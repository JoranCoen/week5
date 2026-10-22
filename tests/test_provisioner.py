import tempfile
import unittest
import os
from pathlib import Path

from src.config import AppConfig
from src.models import ProvisionRequest, WebsiteType
from src.services.backup import create_backup
from src.services.provisioner import provision
from src.services.provisioner import ExistingSiteError
from src.services.provisioner import check_permissions
from src.services.bind import zone_text
from src.services.validation import normalise_domain
from src.services.templates import install_website
from src.models import DatabaseCredentials


class ProvisionerTests(unittest.TestCase):
    def test_domain_normalisation_and_rejection(self):
        self.assertEqual(normalise_domain("Test5"), "test5.sil")
        self.assertEqual(normalise_domain("www.test5.sil"), "www.test5.sil")
        with self.assertRaises(ValueError):
            normalise_domain("../etc/passwd")
        with self.assertRaises(ValueError):
            normalise_domain("example.org")

    def test_backup_is_tar_7z(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "site"
            source.mkdir()
            (source / "index.html").write_text("hello", encoding="utf-8")
            archive = create_backup([source], root / "backups", "test5.sil")
            self.assertTrue(archive.name.endswith(".tar.7z"))
            self.assertTrue(archive.stat().st_size > 0)
            self.assertFalse(archive.with_suffix("").exists())

    def test_dry_run_provisions_static_site_without_system_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = AppConfig(
                backup_root=root / "backups",
                zone_root=root / "zones",
                document_root=root / "www",
                vhost_root=root / "vhosts",
                certificate_root=root / "certs",
                dry_run=True,
            )
            result = provision(
                ProvisionRequest("static.sil", False, False, WebsiteType.STATIC),
                config,
            )
            self.assertEqual(result.domain, "static.sil")
            self.assertTrue((root / "www/static.sil/index.html").exists())
            self.assertTrue((root / "zones/db.static.sil").exists())
            self.assertTrue((root / "vhosts/static.sil.conf").exists())

    def test_existing_site_is_backed_up_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = AppConfig(
                backup_root=root / "backups",
                zone_root=root / "zones",
                document_root=root / "www",
                vhost_root=root / "vhosts",
                certificate_root=root / "certs",
                dry_run=True,
            )
            existing_root = config.document_root / "old.sil"
            existing_root.mkdir(parents=True)
            (existing_root / "index.html").write_text("original", encoding="utf-8")
            with self.assertRaises(ExistingSiteError):
                provision(
                    ProvisionRequest("old.sil", False, False, WebsiteType.STATIC),
                    config,
                )
            self.assertEqual(
                (existing_root / "index.html").read_text(encoding="utf-8"),
                "original",
            )
            self.assertEqual(len(list(config.backup_root.glob("*.tar.7z"))), 1)

    def test_dry_run_skips_system_permission_check(self):
        config = AppConfig(dry_run=True)
        check_permissions(
            ProvisionRequest("test.sil", False, False, WebsiteType.STATIC),
            config,
        )

    def test_zone_contains_self_contained_nameserver_record(self):
        config = AppConfig(
            server_ip="192.0.2.10",
            nameserver="dns.example.test.",
            nameserver_ip="192.0.2.53",
        )
        zone = zone_text("test5.sil", config)
        self.assertIn("@ IN NS dns.example.test.", zone)
        self.assertIn("dns IN A 192.0.2.53", zone)

    def test_zone_uses_configured_server_ip(self):
        config = AppConfig(server_ip="192.168.1.1", nameserver_ip="192.168.1.1")
        zone = zone_text("test2.sil", config)
        self.assertIn("@ IN A 192.168.1.1", zone)
        self.assertIn("www IN A 192.168.1.1", zone)

    def test_environment_configuration_uses_explicit_server_ip(self):
        original = os.environ.get("PROVISIONER_SERVER_IP")
        os.environ["PROVISIONER_SERVER_IP"] = "192.168.1.1"
        try:
            self.assertEqual(AppConfig.from_environment().server_ip, "192.168.1.1")
        finally:
            if original is None:
                os.environ.pop("PROVISIONER_SERVER_IP", None)
            else:
                os.environ["PROVISIONER_SERVER_IP"] = original

    def test_zone_text_does_not_use_localhost_when_server_ip_is_configured(self):
        config = AppConfig(server_ip="192.168.1.1", nameserver_ip="192.168.1.1")
        zone = zone_text("test3.sil", config)
        self.assertNotIn("127.0.0.1", zone)
        self.assertEqual(zone.count("192.168.1.1"), 3)

    def test_todo_site_has_separate_database_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            install_website(
                "todo.sil",
                root,
                WebsiteType.TODO,
                DatabaseCredentials("site_todo", "site_todo", "safe-password"),
                "localhost",
            )
            config = (root / "config.php").read_text(encoding="utf-8")
            index = (root / "index.php").read_text(encoding="utf-8")
            self.assertIn("dbname=site_todo", config)
            self.assertIn("require __DIR__ . '/config.php';", index)
            self.assertIn(
                "$pdo->prepare('INSERT INTO todos (title) VALUES (?)')",
                index,
            )

    def test_permission_check_creates_missing_backup_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = AppConfig(
                backup_root=root / "missing" / "backups",
                zone_root=root / "zones",
                document_root=root / "www",
                vhost_root=root / "vhosts",
                named_conf=root / "named.conf",
                dry_run=False,
            )
            check_permissions(
                ProvisionRequest("test.sil", False, False, WebsiteType.STATIC),
                config,
            )
            self.assertTrue(config.backup_root.is_dir())


if __name__ == "__main__":
    unittest.main()
