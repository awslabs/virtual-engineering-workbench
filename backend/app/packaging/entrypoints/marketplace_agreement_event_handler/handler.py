from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent, event_source

from app.packaging.domain.commands.marketplace import (
    observe_marketplace_agreement_activated_command,
    observe_marketplace_agreement_amended_command,
    observe_marketplace_agreement_ended_command,
    observe_marketplace_agreement_ending_soon_command,
    observe_marketplace_agreement_renewal_terms_finalized_command,
    observe_marketplace_agreement_renewal_upcoming_command,
)
from app.packaging.domain.value_objects.marketplace import agreement_id_value_object, offer_id_value_object
from app.packaging.entrypoints.marketplace_agreement_event_handler import bootstrapper, config
from app.packaging.entrypoints.marketplace_agreement_event_handler.integration_events import (
    purchase_agreement_amended_acceptor,
    purchase_agreement_created_acceptor,
    purchase_agreement_ended_acceptor,
    purchase_agreement_ending_acceptor,
    purchase_agreement_renewal_terms_finalized_acceptor,
    purchase_agreement_renewal_upcoming_acceptor,
)
from app.shared.middleware import event_handler
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

logger = logging.Logger()
tracer = tracing.Tracer()
metrics_handler = metrics.Metrics()
app_config = config.AppConfig()
app = event_handler.EventBridgeEventResolver(logger=logger)
dependencies = bootstrapper.bootstrap(app_config, logger, app=app)


def _is_ami_agreement(agreement_id: str) -> bool:
    """AMI-only admission gate for the buyer-side agreement event stream.

    The EventBridge rule that feeds this Lambda cannot make this decision.
    It matches on ``source`` and ``detail-type``, and the event body carries
    no product type at all -- ``detail.product`` is ``{id, title}`` only, on
    every one of the six buyer-side shapes (AWS buyer guide, "AWS Marketplace
    Agreement EventBridge Events"; confirmed against the
    ``marketplace-agreement`` botocore model, where the only product-type
    field anywhere is ``DescribeAgreement.proposalSummary.resources[].type``).
    So an account holding SaaS, Container or Data subscriptions delivers
    their agreement events here too, and without this gate they are
    republished onto VEW's domain bus as if they were AMI agreements.

    A ``DescribeAgreement`` failure is re-raised, not swallowed. The product
    type is then *unknown*, which is not the same as "not an AMI" -- dropping
    on an IAM error would silently discard real AMI events for as long as the
    misconfiguration lasted. Raising surfaces it on the Errors metric; Lambda
    retries the asynchronous invocation and then sends the event to the
    function's own dead-letter queue, where it can be replayed once fixed.
    """
    if dependencies.agreement_svc.is_ami_agreement(agreement_id):
        return True

    logger.info(
        {
            "AgreementId": agreement_id,
            "Message": "Dropping non-AMI Marketplace agreement event.",
        }
    )
    return False


def _to_decimal(value: Any, *, agreement_id: Optional[str] = None) -> Optional[Decimal]:
    """Coerce AWS's ``renewalSummary.tcv`` string into ``Decimal``.

    AWS reports ``tcv`` as a numeric string (e.g. ``"105000.00"``). If
    the field is missing or unparseable, we degrade gracefully to
    ``None`` rather than crash the whole event — the domain event
    downstream tolerates a missing TCV. Warnings include the
    ``agreement_id`` so an operator triaging a burst of warnings can map
    each one to the offending event.
    """
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        logger.warning(
            {
                "Message": "Could not parse tcv as Decimal",
                "AgreementId": agreement_id,
                "Value": value,
            }
        )
        return None


@app.handle(
    purchase_agreement_created_acceptor.PurchaseAgreementCreatedAcceptor,
    event_name="Purchase Agreement Created - Acceptor",
)
def handle_purchase_agreement_created(event: purchase_agreement_created_acceptor.PurchaseAgreementCreatedAcceptor):
    if not _is_ami_agreement(event.agreement.id):
        return
    logger.info(
        {
            "AgreementId": event.agreement.id,
            "Intent": event.agreement.intent,
            "Status": event.agreement.status,
            "OfferId": event.offer.id,
            "RequestId": event.requestId,
            "Message": "Marketplace agreement activated.",
        }
    )
    command = observe_marketplace_agreement_activated_command.ObserveMarketplaceAgreementActivatedCommand(
        agreementId=agreement_id_value_object.from_str(event.agreement.id),
        offerId=offer_id_value_object.from_str(event.offer.id),
        productId=event.product.id if event.product else None,
        intent=event.agreement.intent,
        status=event.agreement.status,
        startTime=event.agreement.startTime,
        endTime=event.agreement.endTime,
        acceptanceTime=event.agreement.acceptanceTime,
        previousAgreementId=event.agreement.previousAgreementId,
        proposerAccountId=event.proposer.accountId,
        acceptorAccountId=event.acceptor.accountId,
        requestId=event.requestId,
        catalog=event.catalog,
    )
    dependencies.command_bus.handle(command)


@app.handle(
    purchase_agreement_amended_acceptor.PurchaseAgreementAmendedAcceptor,
    event_name="Purchase Agreement Amended - Acceptor",
)
def handle_purchase_agreement_amended(event: purchase_agreement_amended_acceptor.PurchaseAgreementAmendedAcceptor):
    if not _is_ami_agreement(event.agreement.id):
        return
    logger.info(
        {
            "AgreementId": event.agreement.id,
            "Intent": event.agreement.intent,
            "Status": event.agreement.status,
            "OfferId": event.offer.id,
            "AutoRenewalEnabled": event.agreement.autoRenewalEnabled,
            "RequestId": event.requestId,
            "Message": "Marketplace agreement amended.",
        }
    )
    renewal = event.renewalSummary
    command = observe_marketplace_agreement_amended_command.ObserveMarketplaceAgreementAmendedCommand(
        agreementId=agreement_id_value_object.from_str(event.agreement.id),
        offerId=offer_id_value_object.from_str(event.offer.id),
        productId=event.product.id if event.product else None,
        intent=event.agreement.intent,
        status=event.agreement.status,
        startTime=event.agreement.startTime,
        endTime=event.agreement.endTime,
        autoRenewalEnabled=event.agreement.autoRenewalEnabled,
        autoRenewalDisabledBy=renewal.disabledBy if renewal else None,
        lockoutStartTime=renewal.lockoutStartTime if renewal else None,
        proposerAccountId=event.proposer.accountId,
        acceptorAccountId=event.acceptor.accountId,
        requestId=event.requestId,
        catalog=event.catalog,
    )
    dependencies.command_bus.handle(command)


@app.handle(
    purchase_agreement_ended_acceptor.PurchaseAgreementEndedAcceptor,
    event_name="Purchase Agreement Ended - Acceptor",
)
def handle_purchase_agreement_ended(event: purchase_agreement_ended_acceptor.PurchaseAgreementEndedAcceptor):
    if not _is_ami_agreement(event.agreement.id):
        return
    logger.info(
        {
            "AgreementId": event.agreement.id,
            "Status": event.agreement.status,
            "OfferId": event.offer.id,
            "RequestId": event.requestId,
            "Message": "Marketplace agreement ended.",
        }
    )
    command = observe_marketplace_agreement_ended_command.ObserveMarketplaceAgreementEndedCommand(
        agreementId=agreement_id_value_object.from_str(event.agreement.id),
        offerId=offer_id_value_object.from_str(event.offer.id),
        status=event.agreement.status,
        proposerAccountId=event.proposer.accountId,
        acceptorAccountId=event.acceptor.accountId,
        requestId=event.requestId,
        catalog=event.catalog,
    )
    dependencies.command_bus.handle(command)


@app.handle(
    purchase_agreement_ending_acceptor.PurchaseAgreementEndingAcceptor,
    event_name="Purchase Agreement Ending - Acceptor",
)
def handle_purchase_agreement_ending(event: purchase_agreement_ending_acceptor.PurchaseAgreementEndingAcceptor):
    if not _is_ami_agreement(event.agreement.id):
        return
    if event.agreement.daysBeforeEndTime is None or event.agreement.endTime is None:
        # Schema drift: AWS documents these two fields as always present on
        # Ending events. Log with full context, then raise so the Lambda
        # error surfaces via the invocation Errors metric and, after Lambda's
        # asynchronous retries, the event lands on the function's own
        # dead-letter queue. A silent swallow would hide the drift and let
        # the entire buyer-side expiry-warning stream disappear unnoticed.
        logger.warning(
            {
                "AgreementId": event.agreement.id,
                "Status": event.agreement.status,
                "DaysBeforeEndTime": event.agreement.daysBeforeEndTime,
                "EndTime": event.agreement.endTime,
                "RequestId": event.requestId,
                "Message": "Malformed Ending event (missing daysBeforeEndTime or endTime) - raising.",
            }
        )
        raise event_handler.EventResolverException(
            "Malformed 'Purchase Agreement Ending - Acceptor' event: " "missing 'daysBeforeEndTime' or 'endTime'."
        )
    logger.info(
        {
            "AgreementId": event.agreement.id,
            "Status": event.agreement.status,
            "DaysBeforeEndTime": event.agreement.daysBeforeEndTime,
            "EndTime": event.agreement.endTime,
            "OfferId": event.offer.id,
            "RequestId": event.requestId,
            "Message": "Marketplace agreement ending soon.",
        }
    )
    renewal = event.renewalSummary
    command = observe_marketplace_agreement_ending_soon_command.ObserveMarketplaceAgreementEndingSoonCommand(
        agreementId=agreement_id_value_object.from_str(event.agreement.id),
        offerId=offer_id_value_object.from_str(event.offer.id),
        productId=event.product.id if event.product else None,
        daysBeforeEndTime=event.agreement.daysBeforeEndTime,
        status=event.agreement.status,
        startTime=event.agreement.startTime,
        endTime=event.agreement.endTime,
        autoRenewalEnabled=event.agreement.autoRenewalEnabled,
        autoRenewalDisabledBy=renewal.disabledBy if renewal else None,
        lockoutStartTime=renewal.lockoutStartTime if renewal else None,
        proposerAccountId=event.proposer.accountId,
        acceptorAccountId=event.acceptor.accountId,
        requestId=event.requestId,
        catalog=event.catalog,
    )
    dependencies.command_bus.handle(command)


@app.handle(
    purchase_agreement_renewal_terms_finalized_acceptor.PurchaseAgreementRenewalTermsFinalizedAcceptor,
    event_name="Purchase Agreement Renewal Terms Finalized - Acceptor",
)
def handle_purchase_agreement_renewal_terms_finalized(
    event: purchase_agreement_renewal_terms_finalized_acceptor.PurchaseAgreementRenewalTermsFinalizedAcceptor,
):
    if not _is_ami_agreement(event.agreement.id):
        return
    logger.info(
        {
            "AgreementId": event.agreement.id,
            "TCV": event.renewalSummary.tcv,
            "Currency": event.renewalSummary.currency,
            "RequestId": event.requestId,
            "Message": "Marketplace agreement renewal terms finalized.",
        }
    )
    renewal = event.renewalSummary
    command = observe_marketplace_agreement_renewal_terms_finalized_command.ObserveMarketplaceAgreementRenewalTermsFinalizedCommand(  # noqa: E501
        agreementId=agreement_id_value_object.from_str(event.agreement.id),
        productId=event.product.id if event.product else None,
        startTime=event.agreement.startTime,
        endTime=event.agreement.endTime,
        tcv=_to_decimal(renewal.tcv, agreement_id=event.agreement.id),
        currency=renewal.currency,
        termsFinalizedTime=renewal.termsFinalizedTime,
        lockoutReached=renewal.lockoutReached,
        lockoutStartTime=renewal.lockoutStartTime,
        proposerAccountId=event.proposer.accountId,
        acceptorAccountId=event.acceptor.accountId,
        requestId=event.requestId,
        catalog=event.catalog,
    )
    dependencies.command_bus.handle(command)


@app.handle(
    purchase_agreement_renewal_upcoming_acceptor.PurchaseAgreementRenewalUpcomingAcceptor,
    event_name="Purchase Agreement Renewal Upcoming - Acceptor",
)
def handle_purchase_agreement_renewal_upcoming(
    event: purchase_agreement_renewal_upcoming_acceptor.PurchaseAgreementRenewalUpcomingAcceptor,
):
    if not _is_ami_agreement(event.agreement.id):
        return
    logger.info(
        {
            "AgreementId": event.agreement.id,
            "TCV": event.renewalSummary.tcv,
            "LockoutReached": event.renewalSummary.lockoutReached,
            "RequestId": event.requestId,
            "Message": "Marketplace agreement renewal upcoming.",
        }
    )
    renewal = event.renewalSummary
    command = observe_marketplace_agreement_renewal_upcoming_command.ObserveMarketplaceAgreementRenewalUpcomingCommand(
        agreementId=agreement_id_value_object.from_str(event.agreement.id),
        productId=event.product.id if event.product else None,
        startTime=event.agreement.startTime,
        endTime=event.agreement.endTime,
        tcv=_to_decimal(renewal.tcv, agreement_id=event.agreement.id),
        currency=renewal.currency,
        lockoutReached=renewal.lockoutReached,
        proposerAccountId=event.proposer.accountId,
        acceptorAccountId=event.acceptor.accountId,
        requestId=event.requestId,
        catalog=event.catalog,
    )
    dependencies.command_bus.handle(command)


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context(log_event=True)  # type: ignore
@metrics_handler.log_metrics(capture_cold_start_metric=True)
@metric_handlers.report_invocation_metrics(
    dimensions={MetricDimensionNames.AsyncEventHandler: "MarketplaceAgreementEvents"}
)
@event_source(data_class=EventBridgeEvent)
def handler(
    event: EventBridgeEvent,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
