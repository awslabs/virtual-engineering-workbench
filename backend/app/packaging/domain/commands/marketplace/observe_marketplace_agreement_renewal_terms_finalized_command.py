from decimal import Decimal
from typing import Optional

from app.packaging.domain.value_objects.marketplace import agreement_id_value_object
from app.shared.adapters.message_bus import command_bus


class ObserveMarketplaceAgreementRenewalTermsFinalizedCommand(command_bus.Command):
    """Record that AWS Marketplace has finalized renewal terms for a
    percentage-range renewal offer.

    Triggered by the Marketplace agreement event listener on
    ``Purchase Agreement Renewal Terms Finalized - Acceptor``. The
    renewal price uplift is now locked in.
    """

    agreementId: agreement_id_value_object.AgreementIdValueObject
    productId: Optional[str]
    startTime: Optional[str]
    endTime: Optional[str]
    tcv: Optional[Decimal]
    currency: Optional[str]
    termsFinalizedTime: Optional[str]
    lockoutReached: Optional[bool]
    lockoutStartTime: Optional[str]
    proposerAccountId: str
    acceptorAccountId: str
    requestId: str
    catalog: str
