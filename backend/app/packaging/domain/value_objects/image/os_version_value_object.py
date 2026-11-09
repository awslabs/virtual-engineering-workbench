from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class OsVersionValueObject:
    value: str


def from_str(value: str) -> OsVersionValueObject:
    if not value or not value.strip():
        raise domain_exception.DomainException("OS version cannot be empty.")
    return OsVersionValueObject(value=value.strip())
