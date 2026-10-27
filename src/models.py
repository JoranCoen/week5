"""Domain models used by the UI and provisioning services."""

from dataclasses import dataclass
from enum import Enum


class WebsiteType(str, Enum):
    STATIC = "statische website"
    TODO = "todo website"
    WORDPRESS = "WordPress-website"


@dataclass(frozen=True)
class ProvisionRequest:
    domain: str
    https: bool
    database: bool
    website_type: WebsiteType = WebsiteType.STATIC
    database_password: str | None = None


@dataclass(frozen=True)
class DatabaseCredentials:
    name: str
    user: str
    password: str


@dataclass(frozen=True)
class ProvisionResult:
    domain: str
    document_root: str
    vhost_file: str
    zone_file: str
    database: DatabaseCredentials | None = None
