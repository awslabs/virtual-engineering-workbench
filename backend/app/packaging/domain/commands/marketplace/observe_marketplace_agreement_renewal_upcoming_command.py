from decimal import Decimal
from typing import Optional

from app.packaging.domain.value_objects.marketplace import agreement_id_value_object
from app.shared.adapters.message_bus import command_bus


class ObserveMarketplaceAgreementRenewalUpcomingCommand(command_bus.Command):
    """Record that AWS Marketplace has confirmed an upcoming auto-renewal.

    Triggered by the Marketplace agreement event listener on
    ``Purchase Agreement Renewal Upcoming - Acceptor``. AWS emits at the
    start of the renewal-decision lockout period once auto-renewal is
    confirmed to proceed.
    """

    agreementId: agreement_id_value_object.AgreementIdValueObject
    productId: Optional[str]
    startTime: Optional[str]
    endTime: Optional[str]
    tcv: Optional[Decimal]
    currency: Optional[str]
    lockoutReached: Optional[bool]
    proposerAccountId: str
    acceptorAccountId: str
    requestId: str
    catalog: str
