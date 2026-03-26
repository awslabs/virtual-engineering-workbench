import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import version


@dataclass(frozen=True)
class VersionReleaseTypeValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> VersionReleaseTypeValueObject:
    if not value:
        raise domain_exception.DomainException("Version release type cannot be empty.")

    value = value.upper()

    if value not in version.VersionReleaseType.list():
        raise domain_exception.DomainException(
            f"Version release type should be in {version.VersionReleaseType.list()}."
        )

    return VersionReleaseTypeValueObject(value=value)
