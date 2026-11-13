from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception

VALID_PLATFORMS = ["Linux", "Windows"]


@dataclass(frozen=True)
class PlatformValueObject:
    value: str


def from_str(value: str) -> PlatformValueObject:
    if not value or not value.strip():
        raise domain_exception.DomainException("Platform cannot be empty.")
    if value not in VALID_PLATFORMS:
        raise domain_exception.DomainException(f"Platform should be in {VALID_PLATFORMS}.")
    return PlatformValueObject(value=value)
