from datetime import datetime, timezone

from app.packaging.domain.commands.marketplace import observe_marketplace_agreement_ending_soon_command
from app.packaging.domain.events.marketplace import marketplace_agreement_ending_soon
from app.shared.adapters.message_bus import message_bus


def handle(
    command: observe_marketplace_agreement_ending_soon_command.ObserveMarketplaceAgreementEndingSoonCommand,
    msg_bus: message_bus.MessageBus,
) -> None:
    """Execute :class:`ObserveMarketplaceAgreementEndingSoonCommand`."""
    msg_bus.publish(
        marketplace_agreement_ending_soon.MarketplaceAgreementEndingSoon(
            agreementId=command.agreementId.value,
            offerId=command.offerId.value,
            productId=command.productId,
            daysBeforeEndTime=command.daysBeforeEndTime,
            status=command.status,
            startTime=command.startTime,
            endTime=command.endTime,
            autoRenewalEnabled=command.autoRenewalEnabled,
            autoRenewalDisabledBy=command.autoRenewalDisabledBy,
            lockoutStartTime=command.lockoutStartTime,
            proposerAccountId=command.proposerAccountId,
            acceptorAccountId=command.acceptorAccountId,
            requestId=command.requestId,
            catalog=command.catalog,
            observedAt=datetime.now(timezone.utc).isoformat(),
        )
    )
