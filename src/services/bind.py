"""BIND zone creation and validation."""

import os
import tempfile
from pathlib import Path

from src.config import AppConfig
from src.services.commands import run_command


def zone_filename(domain: str) -> str:
    return f"db.{domain}"


def zone_text(domain: str, config: AppConfig) -> str:
    return f"""$TTL 86400
@ IN SOA {config.nameserver} hostmaster.{domain}. (
        2026102201 ; serial
        3600       ; refresh
        900        ; retry
        604800     ; expire
        86400      ; minimum
)
@ IN NS {config.nameserver}
@ IN A {config.server_ip}
www IN A {config.server_ip}
"""


def create_zone(domain: str, config: AppConfig) -> Path:
    config.zone_root.mkdir(parents=True, exist_ok=True)
    path = config.zone_root / zone_filename(domain)
    if path.exists():
        raise FileExistsError(f"Zone bestaat al: {path}")
    with tempfile.NamedTemporaryFile("w", dir=config.zone_root, delete=False) as handle:
        handle.write(zone_text(domain, config))
        temporary = Path(handle.name)
    declaration = f'\nzone "{domain}" {{\n' f"    type master;\n" f'    file "{path}";\n' "};\n"
    try:
        os.replace(temporary, path)
        run_command(["named-checkzone", domain, str(path)], dry_run=config.dry_run)
        if not config.dry_run:
            with config.named_conf.open("a", encoding="utf-8") as named_conf:
                named_conf.write(declaration)
        run_command(["named-checkconf", str(config.named_conf)], dry_run=config.dry_run)
    except Exception:
        if not config.dry_run and config.named_conf.exists():
            content = config.named_conf.read_text(encoding="utf-8")
            config.named_conf.write_text(content.replace(declaration, "", 1), encoding="utf-8")
        path.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)
        raise
    return path
