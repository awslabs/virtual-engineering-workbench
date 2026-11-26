from datetime import datetime, timezone

from app.packaging.domain.commands.marketplace import observe_marketplace_agreement_renewal_upcoming_command
from app.packaging.domain.events.marketplace import marketplace_agreement_renewal_upcoming
from app.shared.adapters.message_bus import message_bus


def handle(
    command: observe_marketplace_agreement_renewal_upcoming_command.ObserveMarketplaceAgreementRenewalUpcomingCommand,
    msg_bus: message_bus.MessageBus,
) -> None:
    """Execute :class:`ObserveMarketplaceAgreementRenewalUpcomingCommand`."""
    msg_bus.publish(
        marketplace_agreement_renewal_upcoming.MarketplaceAgreementRenewalUpcoming(
            agreementId=command.agreementId.value,
            productId=command.productId,
            startTime=command.startTime,
            endTime=command.endTime,
            tcv=command.tcv,
            currency=command.currency,
            lockoutReached=command.lockoutReached,
            proposerAccountId=command.proposerAccountId,
            acceptorAccountId=command.acceptorAccountId,
            requestId=command.requestId,
            catalog=command.catalog,
            observedAt=datetime.now(timezone.utc).isoformat(),
        )
    )
