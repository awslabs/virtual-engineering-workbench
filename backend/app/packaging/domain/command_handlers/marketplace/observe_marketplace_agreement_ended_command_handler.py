from datetime import datetime, timezone

from app.packaging.domain.commands.marketplace import observe_marketplace_agreement_ended_command
from app.packaging.domain.events.marketplace import marketplace_agreement_ended
from app.shared.adapters.message_bus import message_bus


def handle(
    command: observe_marketplace_agreement_ended_command.ObserveMarketplaceAgreementEndedCommand,
    msg_bus: message_bus.MessageBus,
) -> None:
    """Execute :class:`ObserveMarketplaceAgreementEndedCommand`."""
    msg_bus.publish(
        marketplace_agreement_ended.MarketplaceAgreementEnded(
            agreementId=command.agreementId.value,
            offerId=command.offerId.value,
            status=command.status,
            proposerAccountId=command.proposerAccountId,
            acceptorAccountId=command.acceptorAccountId,
            requestId=command.requestId,
            catalog=command.catalog,
            observedAt=datetime.now(timezone.utc).isoformat(),
        )
    )
