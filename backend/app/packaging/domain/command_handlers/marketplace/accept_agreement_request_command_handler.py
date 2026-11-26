import logging
from datetime import datetime, timezone

from app.packaging.domain.command_handlers.marketplace import event_publication
from app.packaging.domain.commands.marketplace import accept_agreement_request_command
from app.packaging.domain.events.marketplace import agreement_request_accepted
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.exceptions.marketplace_conflict_exception import MarketplaceConflictException
from app.packaging.domain.ports.marketplace_procurement_service import MarketplaceProcurementService
from app.shared.adapters.message_bus import message_bus
from app.shared.instrumentation import metrics

CONFLICT_GUIDANCE = (
    "If this quote was accepted before, the agreement is listed on the Agreements page; "
    "do not accept it again. Otherwise request a new quote."
)


def handle(
    command: accept_agreement_request_command.AcceptAgreementRequestCommand,
    procurement_svc: MarketplaceProcurementService,
    msg_bus: message_bus.MessageBus,
    logger: logging.Logger,
    metrics_client: metrics.Metrics | None = None,
) -> str:
    """Execute :class:`AcceptAgreementRequestCommand` and return the durable
    ``agreementId`` under which the buyer's subscription now lives.

    Accepting is the moment the buyer account becomes liable for the
    agreement. A repeated accept of the same request id may succeed with the
    same agreement (seen for a free offer) or raise ``ConflictException``.
    AWS offers no API that maps an agreement request to the agreement it
    created, so a conflict cannot be proven to be an earlier acceptance of
    this request rather than a different purchase. It is reported to the
    buyer as a refusal with guidance, never as success. Once AWS has accepted, a
    failure to publish the event does not fail the command; see
    ``event_publication``.
    """
    agreement_request_id = command.agreementRequestId.value
    try:
        agreement_id = procurement_svc.accept_agreement_request(agreement_request_id).agreementId
    except MarketplaceConflictException as conflict:
        logger.warning(
            {
                "Message": "AWS Marketplace refused to accept the agreement request (conflict).",
                "AgreementRequestId": agreement_request_id,
                "ConflictResourceType": conflict.resource_type,
                "ConflictResourceId": conflict.resource_id,
            }
        )
        raise domain_exception.DomainException(
            f"AWS Marketplace refused to accept agreement request {agreement_request_id}: {conflict}. "
            f"{CONFLICT_GUIDANCE}"
        ) from conflict

    event_publication.publish_best_effort(
        msg_bus,
        agreement_request_accepted.AgreementRequestAccepted(
            agreementRequestId=agreement_request_id,
            agreementId=agreement_id,
            acceptedAt=datetime.now(timezone.utc).isoformat(),
        ),
        logger=logger,
        metrics_client=metrics_client,
        agreementRequestId=agreement_request_id,
        agreementId=agreement_id,
    )

    return agreement_id
