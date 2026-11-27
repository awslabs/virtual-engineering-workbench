import logging
from datetime import datetime, timezone

from app.packaging.domain.command_handlers.marketplace import event_publication
from app.packaging.domain.commands.marketplace import cancel_agreement_command
from app.packaging.domain.events.marketplace import agreement_cancelled
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.exceptions.marketplace_conflict_exception import MarketplaceConflictException
from app.packaging.domain.ports.marketplace_agreement_service import MarketplaceAgreementService
from app.packaging.domain.ports.marketplace_procurement_service import MarketplaceProcurementService
from app.shared.adapters.message_bus import message_bus
from app.shared.instrumentation import metrics

CANCELLED_STATUS = "CANCELLED"


def _recover_already_cancelled(
    conflict: MarketplaceConflictException,
    agreement_id: str,
    agreement_svc: MarketplaceAgreementService,
    logger: logging.Logger,
) -> None:
    """Treat a conflicting cancel as success if the agreement is already
    ``CANCELLED``; otherwise re-raise ``conflict``.

    ``CancelAgreement`` also conflicts for agreements that are not eligible
    for cancellation, or that ended another way (expired, terminated,
    replaced). Those are real failures, so only a ``CANCELLED`` status read
    back with ``DescribeAgreement`` counts as an earlier, successful
    cancellation. If the status cannot be read, the conflict propagates.
    """
    try:
        status = agreement_svc.get_agreement_status(agreement_id)
    except Exception as describe_error:
        raise conflict from describe_error
    if status != CANCELLED_STATUS:
        raise conflict
    logger.info(
        {"Message": "Agreement was already cancelled; treating the cancel as done.", "AgreementId": agreement_id}
    )


def handle(
    command: cancel_agreement_command.CancelAgreementCommand,
    procurement_svc: MarketplaceProcurementService,
    agreement_svc: MarketplaceAgreementService,
    msg_bus: message_bus.MessageBus,
    logger: logging.Logger,
    metrics_client: metrics.Metrics | None = None,
) -> None:
    """Execute :class:`CancelAgreementCommand` (rollback / manage
    subscription).

    A repeated cancel of an already-cancelled agreement succeeded at AWS in
    a live test, so a retry after a lost response or event normally needs no
    recovery. Should AWS answer with ``ConflictException``, it is reported as
    success when the agreement's status is ``CANCELLED`` (see
    :func:`_recover_already_cancelled`), and the event is published. Once
    AWS has cancelled, a failure to publish the event does not fail the
    command; see ``event_publication``.
    """
    agreement_id = command.agreementId.value
    # The route takes any agreement id in the hub account, and the IAM action covers every
    # product type, so the AMI-only rule is checked here. A failed check raises.
    if not agreement_svc.is_ami_agreement(agreement_id):
        raise domain_exception.DomainException(
            f"Agreement {agreement_id} is not an AMI agreement. VEW cancels AMI agreements only."
        )
    try:
        procurement_svc.cancel_agreement(agreement_id)
    except MarketplaceConflictException as conflict:
        _recover_already_cancelled(conflict, agreement_id, agreement_svc, logger)

    event_publication.publish_best_effort(
        msg_bus,
        agreement_cancelled.AgreementCancelled(
            agreementId=agreement_id,
            cancelledAt=datetime.now(timezone.utc).isoformat(),
        ),
        logger=logger,
        metrics_client=metrics_client,
        agreementId=agreement_id,
    )
