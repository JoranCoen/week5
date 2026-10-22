"""Backup creation using tar as the archive format and 7-Zip compression."""

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from shutil import which
from typing import Iterable

from src.config import SEVEN_ZIP_COMMAND


class BackupError(RuntimeError):
    """Raised when a backup cannot be created."""


def create_backup(
    sources: Iterable[Path],
    destination_root: Path,
    domain: str,
    seven_zip_command: str = SEVEN_ZIP_COMMAND,
) -> Path:
    """Create ``domain-<timestamp>.tar.7z`` from existing source paths.

    The intermediate tar file is removed only after 7-Zip succeeds. Commands
    use argument arrays and therefore never invoke a shell.
    """
    existing_sources = [path for path in sources if path.exists()]
    if not existing_sources:
        raise BackupError("Geen bestaande bestanden gevonden om te back-uppen.")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_domain = domain.replace(".", "_")
    destination_root.mkdir(parents=True, exist_ok=True)
    tar_path = destination_root / f"{safe_domain}-{timestamp}.tar"
    compressed_path = destination_root / f"{tar_path.name}.7z"

    tar_command = ["tar", "-cf", str(tar_path), *map(str, existing_sources)]
    resolved_seven_zip = which(seven_zip_command) or which("7z")
    if resolved_seven_zip is None:
        raise BackupError("7-Zip niet gevonden; installeer het pakket 7zip.")
    compress_command = [
        resolved_seven_zip,
        "a",
        "-t7z",
        "-mx=9",
        str(compressed_path),
        str(tar_path),
    ]

    try:
        subprocess.run(tar_command, check=True, capture_output=True, text=True)
        subprocess.run(
            compress_command,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise BackupError(f"Benodigd commando niet gevonden: {exc.filename}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise BackupError(
            f"Backup mislukt voor {domain}." + (f" Details: {detail}" if detail else "")
        ) from exc
    finally:
        tar_path.unlink(missing_ok=True)

    return compressed_path
