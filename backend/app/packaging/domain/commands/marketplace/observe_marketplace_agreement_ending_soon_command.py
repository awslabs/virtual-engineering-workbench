from typing import Optional

from app.packaging.domain.value_objects.marketplace import agreement_id_value_object, offer_id_value_object
from app.shared.adapters.message_bus import command_bus


class ObserveMarketplaceAgreementEndingSoonCommand(command_bus.Command):
    """Record that AWS Marketplace has issued an expiry-warning event.

    Triggered by the Marketplace agreement event listener on
    ``Purchase Agreement Ending - Acceptor``. AWS emits at 180, 120, 90,
    60, and 30 days before ``endTime``.
    """

    agreementId: agreement_id_value_object.AgreementIdValueObject
    offerId: offer_id_value_object.OfferIdValueObject
    productId: Optional[str]
    daysBeforeEndTime: int
    status: str
    startTime: Optional[str]
    endTime: str
    autoRenewalEnabled: Optional[bool]
    autoRenewalDisabledBy: Optional[str]
    lockoutStartTime: Optional[str]
    proposerAccountId: str
    acceptorAccountId: str
    requestId: str
    catalog: str
