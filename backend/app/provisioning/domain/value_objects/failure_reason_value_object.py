import typing

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class FailureReason(value_object.ValueObject):
    value: str


def from_str(value: typing.Optional[str]) -> FailureReason:
    if not value:
        raise domain_exception.DomainException("Failure reason cannot be empty.")

    return FailureReason(value=value)
