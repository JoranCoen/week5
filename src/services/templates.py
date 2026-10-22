"""Website templates and safe file installation."""

from pathlib import Path

from src.models import DatabaseCredentials, WebsiteType

STATIC_HTML = """<!doctype html>
<html lang="nl"><head><meta charset="utf-8"><title>{domain}</title></head>
<body><h1>Welkom op {domain}</h1><p>Deze website werd automatisch aangemaakt.</p></body>
</html>
"""

TODO_CSS = "body { max-width: 48rem; margin: 2rem auto; font-family: sans-serif; }\n"
TODO_SCHEMA = """CREATE TABLE todos (
 id INT AUTO_INCREMENT PRIMARY KEY,
 title VARCHAR(255) NOT NULL,
 completed BOOLEAN NOT NULL DEFAULT FALSE,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
TODO_CONFIG_PHP = """<?php
declare(strict_types=1);
$pdo = new PDO('mysql:host=__MYSQL_HOST__;dbname=__MYSQL_DATABASE__;charset=utf8mb4', '__MYSQL_USER__', '__MYSQL_PASSWORD__',
    [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
"""
TODO_PHP = """<?php
declare(strict_types=1);
require __DIR__ . '/config.php';
if ($_SERVER['REQUEST_METHOD'] === 'POST' && trim($_POST['title'] ?? '') !== '') {
    $statement = $pdo->prepare('INSERT INTO todos (title) VALUES (?)');
    $statement->execute([trim($_POST['title'])]);
}
$todos = $pdo->query('SELECT id, title, completed FROM todos ORDER BY id DESC')->fetchAll(PDO::FETCH_ASSOC);
?><!doctype html><html lang="nl"><head><meta charset="utf-8"><title>Todo</title>
<link rel="stylesheet" href="style.css"></head><body><h1>Todo</h1>
<form method="post"><input name="title" required><button>Toevoegen</button></form>
<ul><?php foreach ($todos as $todo): ?><li><?= htmlspecialchars($todo['title'], ENT_QUOTES, 'UTF-8') ?></li>
<?php endforeach; ?></ul></body></html>
"""
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
define('WP_DEBUG', false);
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
        todo_config = (
            TODO_CONFIG_PHP.replace("__MYSQL_HOST__", mysql_host)
            .replace("__MYSQL_DATABASE__", credentials.name)
            .replace("__MYSQL_USER__", credentials.user)
            .replace("__MYSQL_PASSWORD__", credentials.password)
        )
        (root / "config.php").write_text(todo_config, encoding="utf-8")
        (root / "index.php").write_text(TODO_PHP, encoding="utf-8")
        (root / "style.css").write_text(TODO_CSS, encoding="utf-8")
        (root / "schema.sql").write_text(TODO_SCHEMA, encoding="utf-8")
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
