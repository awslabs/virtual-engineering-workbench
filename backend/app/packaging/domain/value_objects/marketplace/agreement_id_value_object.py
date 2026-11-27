import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class AgreementIdValueObject:
    """Durable AWS Marketplace Agreement identifier.

    The buyer's subscription lives under this ID once
    ``AcceptAgreementRequest`` has succeeded.

    We intentionally do NOT enforce an ``agmt-`` prefix here: AWS's
    ``ResourceId`` regex is ``[A-Za-z0-9_/-]+`` and does not guarantee any
    prefix at the API level. Historically observed IDs use ``agmt-``, but
    binding VEW to that prefix risks silently rejecting a valid agreement
    right after AWS has already created the durable subscription — a
    trap-door bug. The value-object's contract is "distinguish this from
    other IDs at API boundaries", not "enforce an AWS invariant AWS does not
    document".
    """

    value: str


def from_str(value: typing.Optional[str]) -> AgreementIdValueObject:
    if not value:
        raise domain_exception.DomainException("Agreement ID cannot be empty.")
    return AgreementIdValueObject(value=value)
