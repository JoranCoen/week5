"""Apache virtual-host generation."""

import os
import tempfile
from pathlib import Path

from src.config import AppConfig
from src.services.commands import run_command


def vhost_text(domain: str, root: Path, https: bool, config: AppConfig) -> str:
    log_root = Path("/var/log/httpd")
    lines = [
        f"<VirtualHost *:{443 if https else config.http_port}>",
        f"    ServerName {domain}",
        f"    ServerAlias www.{domain}",
        f"    DocumentRoot {root}",
        f"    ErrorLog {log_root}/{domain}-error.log",
        f"    CustomLog {log_root}/{domain}-access.log combined",
        "    <Directory " + str(root) + ">",
        "        AllowOverride All",
        "        Require all granted",
        "    </Directory>",
    ]
    if https:
        cert_root = config.certificate_root
        lines.extend(
            [
                f"    SSLEngine on",
                f"    SSLCertificateFile {cert_root}/certs/{domain}.crt",
                f"    SSLCertificateKeyFile {cert_root}/private/{domain}.key",
            ]
        )
    lines.append("</VirtualHost>")
    return "\n".join(lines) + "\n"


def create_vhost(domain: str, root: Path, https: bool, config: AppConfig) -> Path:
    config.vhost_root.mkdir(parents=True, exist_ok=True)
    path = config.vhost_root / f"{domain}.conf"
    if path.exists():
        raise FileExistsError(f"Vhost bestaat al: {path}")
    with tempfile.NamedTemporaryFile("w", dir=config.vhost_root, delete=False) as handle:
        handle.write(vhost_text(domain, root, https, config))
        temporary = Path(handle.name)
    try:
        os.replace(temporary, path)
        run_command(["apachectl", "configtest"], dry_run=config.dry_run)
    except Exception:
        path.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)
        raise
    return path
