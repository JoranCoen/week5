import tempfile
import unittest
from pathlib import Path

from src.config import AppConfig
from src.models import ProvisionRequest, WebsiteType
from src.services.backup import create_backup
from src.services.provisioner import provision
from src.services.provisioner import ExistingSiteError
from src.services.provisioner import check_permissions
from src.services.validation import normalise_domain


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


if __name__ == "__main__":
    unittest.main()
