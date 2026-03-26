import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.read_models import version_release_type


@dataclass(frozen=True)
class VersionReleaseTypeValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> VersionReleaseTypeValueObject:
    if not value or not value.strip():
        raise domain_exception.DomainException("Version release type cannot be empty.")

    value = value.strip().upper()

    if value not in version_release_type.VersionReleaseType.list():
        raise domain_exception.DomainException(
            f"Version release type should be in {version_release_type.VersionReleaseType.list()}."
        )

    return VersionReleaseTypeValueObject(value=value)
