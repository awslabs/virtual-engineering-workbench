from typing import Optional

from app.packaging.domain.value_objects.marketplace import agreement_id_value_object, offer_id_value_object
from app.shared.adapters.message_bus import command_bus


class ObserveMarketplaceAgreementAmendedCommand(command_bus.Command):
    """Record that AWS Marketplace has amended a purchase agreement.

    Triggered by the Marketplace agreement event listener on
    ``Purchase Agreement Amended - Acceptor``. Covers term changes,
    price changes, and buyer/seller auto-renewal opt-in/opt-out.
    """

    agreementId: agreement_id_value_object.AgreementIdValueObject
    offerId: offer_id_value_object.OfferIdValueObject
    productId: Optional[str]
    intent: Optional[str]
    status: str
    startTime: Optional[str]
    endTime: Optional[str]
    autoRenewalEnabled: Optional[bool]
    autoRenewalDisabledBy: Optional[str]
    lockoutStartTime: Optional[str]
    proposerAccountId: str
    acceptorAccountId: str
    requestId: str
    catalog: str
