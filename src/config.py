"""Central configuration for the provisioning tool."""

from dataclasses import dataclass
import os
from pathlib import Path

DEFAULT_DOMAIN = "sil"
DEFAULT_BACKUP_ROOT = Path("/var/backups/website-provisioner")
SEVEN_ZIP_COMMAND = "7zz"


def _load_local_environment() -> None:
    """Load simple KEY=VALUE entries from the project .env file."""
    project_root = Path(__file__).resolve().parents[1]
    dotenv = project_root / ".env"
    if not dotenv.is_file():
        raise RuntimeError(
            f"Configuratiebestand ontbreekt: {dotenv}. "
            "Maak .env aan op basis van .env.example."
        )
    for raw_line in dotenv.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.removeprefix("export ").strip()
        value = value.strip().strip("\"'")
        if key:
            os.environ[key] = value


def _required(name: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(f"Ontbrekende instelling in .env: {name}")
    return value


@dataclass(frozen=True)
class AppConfig:
    """Filesystem and service settings supplied by the server administrator."""

    backup_root: Path = DEFAULT_BACKUP_ROOT
    zone_root: Path = Path("/var/named")
    named_conf: Path = Path("/etc/named.conf")
    document_root: Path = Path("/var/www/html")
    vhost_root: Path = Path("/etc/httpd/conf.d")
    certificate_root: Path = Path("/etc/pki/tls")
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_admin_user: str = "root"
    mysql_admin_password: str | None = None
    mysql_database_prefix: str = "site_"
    mysql_user_prefix: str = "site_"
    server_ip: str = "127.0.0.1"
    nameserver: str = "ns1.sil."
    nameserver_ip: str = "127.0.0.1"
    bind_user: str = "named"
    bind_group: str = "named"
    apache_user: str = "apache"
    apache_group: str = "apache"
    dry_run: bool = False

    @classmethod
    def from_environment(cls) -> "AppConfig":
        """Load every runtime setting from the project .env file."""
        _load_local_environment()
        return cls(
            backup_root=Path(_required("PROVISIONER_BACKUP_ROOT")),
            zone_root=Path(_required("PROVISIONER_ZONE_ROOT")),
            named_conf=Path(_required("PROVISIONER_NAMED_CONF")),
            document_root=Path(_required("PROVISIONER_DOCUMENT_ROOT")),
            vhost_root=Path(_required("PROVISIONER_VHOST_ROOT")),
            certificate_root=Path(_required("PROVISIONER_CERTIFICATE_ROOT")),
            mysql_host=_required("MYSQL_HOST"),
            mysql_port=int(_required("MYSQL_PORT")),
            mysql_admin_user=_required("MYSQL_ADMIN_USER"),
            mysql_admin_password=os.getenv("MYSQL_ADMIN_PASSWORD") or None,
            mysql_database_prefix=_required("MYSQL_DATABASE_PREFIX"),
            mysql_user_prefix=_required("MYSQL_USER_PREFIX"),
            server_ip=_required("PROVISIONER_SERVER_IP"),
            nameserver=_required("PROVISIONER_NAMESERVER"),
            nameserver_ip=_required("PROVISIONER_NAMESERVER_IP"),
            bind_user=_required("PROVISIONER_BIND_USER"),
            bind_group=_required("PROVISIONER_BIND_GROUP"),
            apache_user=_required("PROVISIONER_APACHE_USER"),
            apache_group=_required("PROVISIONER_APACHE_GROUP"),
            dry_run=_required("PROVISIONER_DRY_RUN").lower() in {"1", "true", "yes"},
        )
