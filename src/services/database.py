"""MySQL database and user management."""

import secrets
import string

from src.config import AppConfig
from src.models import DatabaseCredentials


def _identifier(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value)


def credentials_for(
    domain: str,
    config: AppConfig,
    password: str | None = None,
) -> DatabaseCredentials:
    token = _identifier(domain.removesuffix(".sil"))[:24]
    name = f"{config.mysql_database_prefix}{token}".lower()[:64]
    user = token.lower()[:32]
    if not user:
        raise ValueError("Domein levert geen geldige MySQL-gebruikersnaam op.")
    if password is not None and not password:
        raise ValueError("MySQL-wachtwoord mag niet leeg zijn.")
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*_-"
    selected_password = password or "".join(
        secrets.choice(alphabet) for _ in range(24)
    )
    return DatabaseCredentials(name, user, selected_password)


def provision_database(
    domain: str,
    config: AppConfig,
    password: str | None = None,
) -> DatabaseCredentials:
    """Create a database and least-privilege user with parameterized values."""
    import mysql.connector

    credentials = credentials_for(domain, config, password)
    connection = mysql.connector.connect(
        host=config.mysql_host,
        port=config.mysql_port,
        user=config.mysql_admin_user,
        password=config.mysql_admin_password,
    )
    cursor = connection.cursor()
    try:
        cursor.execute(f"CREATE DATABASE `{credentials.name}`")
        cursor.execute(
            "CREATE USER %s@'localhost' IDENTIFIED BY %s",
            (credentials.user, credentials.password),
        )
        cursor.execute(
            f"GRANT ALL PRIVILEGES ON `{credentials.name}`.* TO %s@'localhost'",
            (credentials.user,),
        )
        cursor.execute("FLUSH PRIVILEGES")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    try:
        verify_connection = mysql.connector.connect(
            host=config.mysql_host,
            port=config.mysql_port,
            user=credentials.user,
            password=credentials.password,
            database=credentials.name,
        )
        verify_connection.close()
    except mysql.connector.Error as error:
        raise RuntimeError(
            f"MySQL-gebruiker {credentials.user} kan niet verbinden met "
            f"database {credentials.name}: {error.msg}"
        ) from error
    return credentials


def load_schema(credentials: DatabaseCredentials, schema: str, config: AppConfig) -> None:
    """Execute the bundled schema with the newly-created MySQL user."""
    import mysql.connector

    connection = mysql.connector.connect(
        host=config.mysql_host,
        port=config.mysql_port,
        user=credentials.user,
        password=credentials.password,
        database=credentials.name,
    )
    cursor = connection.cursor()
    try:
        for statement in schema.split(";"):
            if statement.strip():
                cursor.execute(statement)
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def drop_database(credentials: DatabaseCredentials, config: AppConfig) -> None:
    """Remove a database and its application user during rollback."""
    import mysql.connector

    connection = mysql.connector.connect(
        host=config.mysql_host,
        port=config.mysql_port,
        user=config.mysql_admin_user,
        password=config.mysql_admin_password,
    )
    cursor = connection.cursor()
    try:
        cursor.execute(f"DROP DATABASE IF EXISTS `{credentials.name}`")
        cursor.execute("DROP USER IF EXISTS %s@'localhost'", (credentials.user,))
        connection.commit()
    finally:
        cursor.close()
        connection.close()
