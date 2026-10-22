"""Orchestration of backup and new-site provisioning."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from src.config import AppConfig
from src.models import DatabaseCredentials, ProvisionRequest, ProvisionResult
from src.services.apache import create_vhost
from src.services.backup import create_backup
from src.services.bind import create_zone, zone_filename
from src.services.certificates import create_certificate
from src.services.commands import run_command
from src.services.database import credentials_for, provision_database, drop_database, load_schema
from src.services.dns_check import check_dns
from src.services.templates import TODO_SCHEMA, install_website
from src.services.wordpress import download_wordpress

BACKUP_MESSAGE = "Deze website bestaat al; de backup staat klaar."


class ExistingSiteError(RuntimeError):
    """Raised after an existing site was backed up."""


def _require_write_access(path: Path, label: str) -> None:
    if not path.exists() and path.suffix == "":
        path.mkdir(parents=True, exist_ok=True)
    parent = path if path.is_dir() else path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", prefix=".provisioner-write-test-", dir=parent
        ) as test_file:
            test_file.write("write-test")
            test_file.flush()
    except (OSError, PermissionError) as error:
        raise PermissionError(
            f"Geen schrijfrechten voor {label}: {parent}. "
            "Controleer de eigenaar/permissies en start de provisioning-app "
            "met sudo."
        ) from error


def check_permissions(request: ProvisionRequest, config: AppConfig) -> None:
    """Fail before changing anything when the server paths are not writable."""
    if config.dry_run:
        return
    _require_write_access(config.zone_root, "BIND-zonefolder")
    _require_write_access(config.document_root, "website-root")
    _require_write_access(config.vhost_root, "Apache-vhostfolder")
    _require_write_access(config.backup_root, "backupfolder")
    if not config.named_conf.exists():
        _require_write_access(config.named_conf, "named.conf")
    elif not os.access(config.named_conf, os.W_OK):
        raise PermissionError(
            f"Geen schrijfrechten voor named.conf: {config.named_conf}. "
            "Start de provisioning-app met sudo."
        )
    if request.https:
        _require_write_access(config.certificate_root, "certificaatfolder")


def _database_dump(credentials: DatabaseCredentials, destination: Path, config: AppConfig) -> Path:
    command = [
        "mysqldump",
        "--single-transaction",
        "--routines",
        "--events",
        "--host",
        config.mysql_host,
        "--port",
        str(config.mysql_port),
        "--user",
        credentials.user,
        f"--password={credentials.password}",
        credentials.name,
    ]
    if config.dry_run:
        destination.write_text("-- dry-run SQL dump\n", encoding="utf-8")
    else:
        with destination.open("w", encoding="utf-8") as output:
            try:
                subprocess.run(command, check=True, stdout=output, text=True)
            except (FileNotFoundError, subprocess.CalledProcessError) as exc:
                destination.unlink(missing_ok=True)
                raise RuntimeError("MySQL-database kon niet worden gedumpt.") from exc
    return destination


def site_paths(domain: str, config: AppConfig) -> tuple[Path, Path]:
    return config.document_root / domain, config.vhost_root / f"{domain}.conf"


def site_exists(domain: str, config: AppConfig) -> bool:
    root, vhost = site_paths(domain, config)
    return root.exists() or vhost.exists() or (config.zone_root / zone_filename(domain)).exists()


def backup_existing_site(domain: str, config: AppConfig) -> Path:
    root, _ = site_paths(domain, config)
    zone = config.zone_root / zone_filename(domain)
    sources = [path for path in (zone, root) if path.exists()]
    database_dump = config.backup_root / f".{domain}.sql"
    if config.mysql_admin_password:
        candidate = DatabaseCredentials(
            credentials_for(domain, config).name,
            config.mysql_admin_user,
            config.mysql_admin_password,
        )
        try:
            _database_dump(candidate, database_dump, config)
        except RuntimeError:
            database_dump.unlink(missing_ok=True)
        else:
            sources.append(database_dump)
    if not sources:
        raise FileNotFoundError(f"Geen backup-bronnen gevonden voor {domain}")
    try:
        return create_backup(sources, config.backup_root, domain)
    finally:
        database_dump.unlink(missing_ok=True)


def provision(request: ProvisionRequest, config: AppConfig) -> ProvisionResult:
    """Provision one site; existing sites are backed up and never overwritten."""
    check_permissions(request, config)
    if site_exists(request.domain, config):
        archive = backup_existing_site(request.domain, config)
        raise ExistingSiteError(f"{BACKUP_MESSAGE} Backup: {archive}")

    root = config.document_root / request.domain
    created: list[Path] = []
    credentials: DatabaseCredentials | None = None
    wordpress_temporary: tempfile.TemporaryDirectory[str] | None = None
    try:
        root.mkdir(parents=True, exist_ok=False)
        created.append(root)
        if request.database:
            credentials = (
                credentials_for(request.domain, config)
                if config.dry_run
                else provision_database(request.domain, config)
            )
        wordpress_source = None
        if request.website_type.value == "WordPress-website" and not config.dry_run:
            wordpress_temporary = tempfile.TemporaryDirectory(prefix="wordpress-")
            wordpress_source = download_wordpress(Path(wordpress_temporary.name))
        install_website(
            request.domain,
            root,
            request.website_type,
            credentials,
            config.mysql_host,
            wordpress_source,
        )
        if request.database and request.website_type.value == "todo" and credentials:
            if not config.dry_run:
                load_schema(credentials, TODO_SCHEMA, config)
        zone = create_zone(request.domain, config)
        created.append(zone)
        if request.https:
            create_certificate(request.domain, config)
        vhost = create_vhost(request.domain, root, request.https, config)
        created.append(vhost)
        run_command(["systemctl", "reload", "named"], dry_run=config.dry_run)
        run_command(["systemctl", "reload", "httpd"], dry_run=config.dry_run)
        if not config.dry_run:
            check_dns(request.domain, config)
    except Exception:
        rollback_error: Exception | None = None
        if credentials is not None and not config.dry_run:
            try:
                drop_database(credentials, config)
            except Exception as error:
                rollback_error = error
        for path in reversed(created):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
        if wordpress_temporary is not None:
            wordpress_temporary.cleanup()
        if rollback_error is not None:
            raise RuntimeError(
                "Provisioning mislukt en database rollback mislukte ook."
            ) from rollback_error
        raise
    if wordpress_temporary is not None:
        wordpress_temporary.cleanup()
    return ProvisionResult(request.domain, str(root), str(vhost), str(zone), credentials)
