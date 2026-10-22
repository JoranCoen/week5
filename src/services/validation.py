"""Input validation and domain normalisation."""

import re

from src.config import DEFAULT_DOMAIN

DOMAIN_PATTERN = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9]" r"(?:[a-z0-9-]{0,61}[a-z0-9])?$",
    re.IGNORECASE,
)


def normalise_domain(value: str) -> str:
    """Return a canonical domain below the configured main domain."""
    domain = value.strip().lower().rstrip(".")
    if not domain:
        raise ValueError("Geef een domein op.")
    if "." not in domain:
        domain = f"{domain}.{DEFAULT_DOMAIN}"
    if not DOMAIN_PATTERN.fullmatch(domain):
        raise ValueError("Het domein bevat ongeldige tekens.")
    if not domain.endswith(f".{DEFAULT_DOMAIN}"):
        raise ValueError(f"Het domein moet onder .{DEFAULT_DOMAIN} vallen.")
    return domain
