"""DNS diagnostics for the configured BIND server."""

from src.config import AppConfig
from src.services.commands import run_command


def check_dns(domain: str, config: AppConfig) -> str:
    """Query the local authoritative server for an A record."""
    return run_command(
        ["dig", f"@{config.nameserver_ip}", domain, "A", "+short"],
        dry_run=config.dry_run,
    )
