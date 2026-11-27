from app.packaging.domain.value_objects.marketplace import agreement_id_value_object, offer_id_value_object
from app.shared.adapters.message_bus import command_bus


class ObserveMarketplaceAgreementEndedCommand(command_bus.Command):
    """Record that AWS Marketplace has ended a purchase agreement.

    Triggered by the Marketplace agreement event listener on
    ``Purchase Agreement Ended - Acceptor``. ``status`` is one of
    ``CANCELLED``, ``EXPIRED``, ``TERMINATED``, ``RENEWED``, ``REPLACED``.
    """

    agreementId: agreement_id_value_object.AgreementIdValueObject
    offerId: offer_id_value_object.OfferIdValueObject
    status: str
    proposerAccountId: str
    acceptorAccountId: str
    requestId: str
    catalog: str
