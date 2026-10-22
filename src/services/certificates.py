"""Self-signed certificate generation."""

import os
from pathlib import Path

from src.config import AppConfig
from src.services.commands import run_command


def create_certificate(domain: str, config: AppConfig) -> tuple[Path, Path]:
    cert_dir = config.certificate_root / "certs"
    key_dir = config.certificate_root / "private"
    cert_dir.mkdir(parents=True, exist_ok=True)
    key_dir.mkdir(parents=True, exist_ok=True)
    certificate = cert_dir / f"{domain}.crt"
    key = key_dir / f"{domain}.key"
    if certificate.exists() or key.exists():
        raise FileExistsError(f"Certificaat bestaat al voor {domain}")
    run_command(
        [
            "openssl",
            "req",
            "-x509",
            "-nodes",
            "-newkey",
            "rsa:2048",
            "-days",
            "365",
            "-subj",
            f"/CN={domain}",
            "-keyout",
            str(key),
            "-out",
            str(certificate),
        ],
        dry_run=config.dry_run,
    )
    if not config.dry_run:
        os.chmod(key, 0o600)
    return certificate, key
