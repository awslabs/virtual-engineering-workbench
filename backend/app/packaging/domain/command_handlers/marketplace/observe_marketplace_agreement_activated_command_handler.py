from datetime import datetime, timezone

from app.packaging.domain.commands.marketplace import observe_marketplace_agreement_activated_command
from app.packaging.domain.events.marketplace import marketplace_agreement_activated
from app.shared.adapters.message_bus import message_bus


def handle(
    command: observe_marketplace_agreement_activated_command.ObserveMarketplaceAgreementActivatedCommand,
    msg_bus: message_bus.MessageBus,
) -> None:
    """Execute :class:`ObserveMarketplaceAgreementActivatedCommand`.

    The listener has already parsed the AWS EventBridge envelope; the
    handler simply re-publishes it as a first-class VEW domain event.
    ``observedAt`` is the moment this handler ran, distinct from the
    AWS-reported event ``time`` (preserved by the entrypoint on the
    logger context).
    """
    msg_bus.publish(
        marketplace_agreement_activated.MarketplaceAgreementActivated(
            agreementId=command.agreementId.value,
            offerId=command.offerId.value,
            productId=command.productId,
            intent=command.intent,
            status=command.status,
            startTime=command.startTime,
            endTime=command.endTime,
            acceptanceTime=command.acceptanceTime,
            previousAgreementId=command.previousAgreementId,
            proposerAccountId=command.proposerAccountId,
            acceptorAccountId=command.acceptorAccountId,
            requestId=command.requestId,
            catalog=command.catalog,
            observedAt=datetime.now(timezone.utc).isoformat(),
        )
    )
