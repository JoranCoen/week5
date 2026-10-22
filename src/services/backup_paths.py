"""Helpers for selecting backup inputs without including configuration files."""

from pathlib import Path


def website_backup_sources(
    zone_file: Path,
    document_root: Path,
    sql_dump: Path | None = None,
) -> list[Path]:
    """Return only the zone, website files, and optional SQL dump."""
    sources = [zone_file, document_root]
    if sql_dump is not None:
        sources.append(sql_dump)
    return sources
