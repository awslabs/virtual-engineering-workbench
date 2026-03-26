import typing

from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.read_models import version
from app.shared.ddd import value_object


class VersionStageValueObject(value_object.ValueObject):
    value: version.VersionStage


def from_str(value: typing.Optional[str]) -> VersionStageValueObject:
    if not value:
        raise domain_exception.DomainException("Stage cannot be empty.")

    enum_value = next((v for v in version.VersionStage if v.lower().strip() == value.lower().strip()), None)

    if not enum_value:
        raise domain_exception.DomainException(f"Stage must be one of {version.VersionStage}")

    return VersionStageValueObject(value=enum_value)
