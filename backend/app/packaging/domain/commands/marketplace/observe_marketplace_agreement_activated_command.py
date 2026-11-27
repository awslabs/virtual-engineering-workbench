from typing import Optional

from app.packaging.domain.value_objects.marketplace import agreement_id_value_object, offer_id_value_object
from app.shared.adapters.message_bus import command_bus


class ObserveMarketplaceAgreementActivatedCommand(command_bus.Command):
    """Record that AWS Marketplace has activated a purchase agreement.

    Triggered by the Marketplace agreement event listener on
    ``Purchase Agreement Created - Acceptor``. The listener has already
    parsed the AWS event envelope; this command carries the flat,
    VEW-facing view of it. The handler's sole job is to emit
    :class:`MarketplaceAgreementActivated` on the domain event bus so
    other bounded contexts (Publishing cache invalidation, UI
    subscribers) can react.

    Kept as a command (rather than a direct event publish from the
    entrypoint) to preserve the repo invariant that mutations flow
    through the command bus for metrics, tracing, and future retry
    semantics.
    """

    agreementId: agreement_id_value_object.AgreementIdValueObject
    offerId: offer_id_value_object.OfferIdValueObject
    productId: Optional[str]
    intent: Optional[str]
    status: str
    startTime: Optional[str]
    endTime: Optional[str]
    acceptanceTime: Optional[str]
    previousAgreementId: Optional[str]
    proposerAccountId: str
    acceptorAccountId: str
    requestId: str
    catalog: str
