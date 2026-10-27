"""Website templates and safe file installation."""

from pathlib import Path
from zipfile import ZipFile

from src.models import DatabaseCredentials, WebsiteType

TODO_ARCHIVE = Path(__file__).resolve().parents[2] / "assets" / "todo-site.zip"

STATIC_HTML = """<!doctype html>
<html lang="nl"><head><meta charset="utf-8"><title>{domain}</title></head>
<body><h1>Welkom op {domain}</h1><p>Deze website werd automatisch aangemaakt.</p></body>
</html>
"""

TODO_CSS = "body { max-width: 48rem; margin: 2rem auto; font-family: sans-serif; }\n"
WORDPRESS_README = """WordPress-bestanden moeten hier geplaatst worden.
Installeer de voorgeschreven WordPress-versie op de server en voltooi daarna
de installatie via de website.
"""
WORDPRESS_CONFIG = """<?php
define('DB_NAME', '{database}');
define('DB_USER', '{user}');
define('DB_PASSWORD', '{password}');
define('DB_HOST', '{host}');
define('DB_CHARSET', 'utf8mb4');
define('DB_COLLATE', '');

$table_prefix = 'wp_';

define('WP_DEBUG', false);

if (!defined('ABSPATH')) {{
    define('ABSPATH', __DIR__ . '/');
}}
require_once ABSPATH . 'wp-settings.php';
"""


def install_website(
    domain: str,
    root: Path,
    website_type: WebsiteType,
    credentials: DatabaseCredentials | None = None,
    mysql_host: str = "localhost",
    wordpress_source: Path | None = None,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    if website_type is WebsiteType.STATIC:
        (root / "index.html").write_text(STATIC_HTML.format(domain=domain), encoding="utf-8")
    elif website_type is WebsiteType.TODO:
        if credentials is None:
            raise ValueError("Todo-site vereist databasegegevens.")
        if not TODO_ARCHIVE.is_file():
            raise FileNotFoundError(f"Todo-template ontbreekt: {TODO_ARCHIVE}")
        with ZipFile(TODO_ARCHIVE) as archive:
            for member in archive.infolist():
                if not member.filename.startswith("www/"):
                    continue
                relative = Path(member.filename.removeprefix("www/"))
                target = (root / relative).resolve()
                if target != root.resolve() and root.resolve() not in target.parents:
                    raise ValueError("Ongeldige todo-template: pad buiten website-root.")
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(member))
        config_path = root / "includes" / "config.php"
        config_text = config_path.read_text(encoding="utf-8")
        config_text = (
            config_text.replace("xxxxxxxxxxxxxxxxxxxxxxx", credentials.user, 1)
            .replace("xxxxxxxxxxxxxxxxxxxxxxx", credentials.password, 1)
            .replace("xxxxxxxxxxxxxxxxxxxxxxx", credentials.name, 1)
            .replace("define ('DB_NAME', 'todo');", f"define ('DB_NAME', '{credentials.name}');")
            .replace("define ('DB_HOST', 'localhost');", f"define ('DB_HOST', '{mysql_host}');")
        )
        config_path.write_text(config_text, encoding="utf-8")
    elif website_type is WebsiteType.WORDPRESS:
        if wordpress_source is not None and wordpress_source.is_dir():
            for item in wordpress_source.iterdir():
                target = root / item.name
                if item.is_dir():
                    import shutil

                    shutil.copytree(item, target)
                else:
                    import shutil

                    shutil.copy2(item, target)
        else:
            (root / "INSTALL-WORDPRESS.txt").write_text(WORDPRESS_README, encoding="utf-8")
        if credentials is not None:
            (root / "wp-config.php").write_text(
                WORDPRESS_CONFIG.format(
                    database=credentials.name,
                    user=credentials.user,
                    password=credentials.password,
                    host=mysql_host,
                ),
                encoding="utf-8",
            )
    else:
        raise ValueError(f"Onbekend websitetype: {website_type}")


def todo_schema() -> str:
    """Return the SQL schema shipped with the supplied todo application."""
    with ZipFile(TODO_ARCHIVE) as archive:
        schema = archive.read("todo.sql").decode("utf-8")
    return "\n".join(
        line for line in schema.splitlines() if not line.strip().upper().startswith("USE ")
    )
