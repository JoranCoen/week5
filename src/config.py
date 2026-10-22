"""Central configuration for the provisioning tool."""

from dataclasses import dataclass
import os
from pathlib import Path

DEFAULT_DOMAIN = "sil"
DEFAULT_BACKUP_ROOT = Path("/var/backups/website-provisioner")
SEVEN_ZIP_COMMAND = "7zz"


@dataclass(frozen=True)
class AppConfig:
    """Filesystem and service settings supplied by the server administrator."""

    backup_root: Path = DEFAULT_BACKUP_ROOT
    zone_root: Path = Path("/var/named")
    named_conf: Path = Path("/etc/named.conf")
    document_root: Path = Path("/var/www")
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
    apache_user: str = "apache"
    apache_group: str = "apache"
    dry_run: bool = False
    wordpress_source: Path | None = None

    @classmethod
    def from_environment(cls) -> "AppConfig":
        """Load optional local settings without requiring an extra dotenv package."""
        return cls(
            backup_root=Path(os.getenv("PROVISIONER_BACKUP_ROOT", str(DEFAULT_BACKUP_ROOT))),
            zone_root=Path(os.getenv("PROVISIONER_ZONE_ROOT", "/var/named")),
            named_conf=Path(os.getenv("PROVISIONER_NAMED_CONF", "/etc/named.conf")),
            document_root=Path(os.getenv("PROVISIONER_DOCUMENT_ROOT", "/var/www")),
            vhost_root=Path(os.getenv("PROVISIONER_VHOST_ROOT", "/etc/httpd/conf.d")),
            certificate_root=Path(os.getenv("PROVISIONER_CERTIFICATE_ROOT", "/etc/pki/tls")),
            mysql_host=os.getenv("MYSQL_HOST", "localhost"),
            mysql_port=int(os.getenv("MYSQL_PORT", "3306")),
            mysql_admin_user=os.getenv("MYSQL_ADMIN_USER", "root"),
            mysql_admin_password=os.getenv("MYSQL_ADMIN_PASSWORD") or None,
            server_ip=os.getenv("PROVISIONER_SERVER_IP", "127.0.0.1"),
            nameserver=os.getenv("PROVISIONER_NAMESERVER", "ns1.sil."),
            nameserver_ip=os.getenv("PROVISIONER_NAMESERVER_IP", "127.0.0.1"),
            dry_run=os.getenv("PROVISIONER_DRY_RUN", "").lower() in {"1", "true", "yes"},
            wordpress_source=(
                Path(os.environ["WORDPRESS_SOURCE"]) if os.getenv("WORDPRESS_SOURCE") else None
            ),
        )
