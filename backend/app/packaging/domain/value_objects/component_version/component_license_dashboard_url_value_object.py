from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ComponentLicenseDashboardUrlValueObject:
    value: str


def from_str(value: Optional[str]) -> ComponentLicenseDashboardUrlValueObject:
    if not value:
        raise domain_exception.DomainException("License dashboard link cannot be empty.")
    parsed_url = urlparse(value)
    if parsed_url.scheme not in ["http", "https"]:
        raise domain_exception.DomainException(
            f"License dashboard link is not valid: {value}. The URL scheme must be 'http' or 'https'."
        )
    if not parsed_url.netloc:
        raise domain_exception.DomainException(
            f"License dashboard link is not valid: {value}. The URL must contain a hostname."
        )
    return ComponentLicenseDashboardUrlValueObject(value=value)
