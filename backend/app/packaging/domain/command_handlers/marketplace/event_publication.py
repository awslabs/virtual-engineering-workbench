"""Best-effort domain-event publication for the Marketplace write paths.

The three Marketplace procurement commands (create quote, accept quote,
cancel agreement) each perform an AWS write and then publish a domain
event. The AWS write is the authoritative act -- it is what creates or
ends a real, billable agreement -- and it cannot be rolled back.

A publication failure after the write therefore leaves changed AWS state
with no event. Letting the exception propagate would make it worse: the
purchase has *succeeded*, and the user would be shown a 500 telling them it
failed. So publication is best-effort and explicitly so:

* the AWS outcome is returned to the caller, because it really happened
* the failure is logged at ERROR with the identifiers needed to reconcile
* a ``MarketplaceEventPublishFailed`` counter is emitted so the gap is
  visible on the ops dashboard instead of being silent

The commands are safe to retry, which is what recovers a lost event:

* create sends an AWS idempotency token, so a retry returns the same
  agreement request and publishes ``AgreementRequestCreated`` again
* cancel treats AWS's ``ConflictException`` as success when
  ``DescribeAgreement`` reports the agreement ``CANCELLED``, and publishes
  its event again
* accept never treats a conflict as success: AWS offers no way to map an
  agreement request to the agreement it created, so the buyer is refused
  with guidance to check the Agreements page

This is NOT guaranteed delivery: there is no outbox, and an event is only
re-published if the caller retries. A retry after a publication that did
succeed publishes the event a second time. Consumers must therefore
deduplicate on the AWS identifiers (``agreementRequestId`` /
``agreementId``) and reconcile against AWS (``SearchAgreements`` /
``DescribeAgreement``) rather than trust event arrival. Today nothing
consumes these events -- the subscriptions UI reads the AWS Agreements API
live via ``list_active_agreements`` -- so a lost event costs a missed
reaction, not a lost subscription.
"""

import logging
from typing import Any

from app.shared.adapters.message_bus import message_bus
from app.shared.instrumentation import metrics

PUBLISH_FAILED_METRIC = "MarketplaceEventPublishFailed"


def publish_best_effort(
    msg_bus: message_bus.MessageBus,
    event: message_bus.Message,
    logger: logging.Logger,
    metrics_client: metrics.Metrics | None = None,
    **reconciliation_context: Any,
) -> bool:
    """Publish ``event``, absorbing failure. Returns whether it published.

    ``reconciliation_context`` is logged alongside the failure and should
    carry whatever an operator needs to find the AWS-side state that was
    already committed (agreement id, agreement request id, offer id).
    """
    try:
        msg_bus.publish(event)
        return True
    except Exception as e:
        logger.error(
            {
                "Message": (
                    "AWS Marketplace write succeeded but publishing the domain event failed. "
                    "AWS state has changed and no event was emitted; reconcile against the "
                    "AWS Agreements API."
                ),
                "Event": event.event_name,
                "Error": str(e),
                **reconciliation_context,
            }
        )
        if metrics_client is not None:
            try:
                metrics_client.publish_counter(
                    metric_name=PUBLISH_FAILED_METRIC,
                    metric_type=metrics.MetricType.FailedCommand,
                )
            except Exception as metric_error:
                # Never let instrumentation mask the original outcome.
                logger.warning(f"Unable to publish {PUBLISH_FAILED_METRIC} metric: {metric_error}")
        return False
