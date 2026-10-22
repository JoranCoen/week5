"""Safe execution of fixed system commands."""

import subprocess
from collections.abc import Sequence


class CommandError(RuntimeError):
    """Raised for a failed or unavailable system command."""


def run_command(command: Sequence[str], *, dry_run: bool = False) -> str:
    if dry_run:
        return " ".join(command)
    try:
        result = subprocess.run(list(command), check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise CommandError(f"Commando niet gevonden: {exc.filename}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise CommandError(f"Commando mislukt: {' '.join(command)}. {detail}") from exc
    return result.stdout.strip()
