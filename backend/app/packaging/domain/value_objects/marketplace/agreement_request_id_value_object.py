import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception

_PREFIX = "ar-"


@dataclass(frozen=True)
class AgreementRequestIdValueObject:
    """Short-lived handle returned by ``CreateAgreementRequest``
    (pattern ``ar-[A-Za-z0-9]+``, e.g. ``ar-abc123``). Confirmed by
    ``AcceptAgreementRequest`` to yield a durable
    :class:`AgreementIdValueObject`.
    """

    value: str


def from_str(value: typing.Optional[str]) -> AgreementRequestIdValueObject:
    if not value:
        raise domain_exception.DomainException("Agreement request ID cannot be empty.")
    if not value.startswith(_PREFIX):
        raise domain_exception.DomainException(f"Invalid agreement request ID '{value}': expected prefix '{_PREFIX}'.")
    return AgreementRequestIdValueObject(value=value)
