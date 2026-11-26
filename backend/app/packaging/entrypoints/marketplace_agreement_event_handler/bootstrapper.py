import boto3
from aws_lambda_powertools import logging
from pydantic import BaseModel, ConfigDict

from app.packaging.adapters.services.aws_marketplace_discovery_service import AwsMarketplaceDiscoveryService
from app.packaging.domain.command_handlers.marketplace import (
    observe_marketplace_agreement_activated_command_handler,
    observe_marketplace_agreement_amended_command_handler,
    observe_marketplace_agreement_ended_command_handler,
    observe_marketplace_agreement_ending_soon_command_handler,
    observe_marketplace_agreement_renewal_terms_finalized_command_handler,
    observe_marketplace_agreement_renewal_upcoming_command_handler,
)
from app.packaging.domain.commands.marketplace import (
    observe_marketplace_agreement_activated_command,
    observe_marketplace_agreement_amended_command,
    observe_marketplace_agreement_ended_command,
    observe_marketplace_agreement_ending_soon_command,
    observe_marketplace_agreement_renewal_terms_finalized_command,
    observe_marketplace_agreement_renewal_upcoming_command,
)
from app.packaging.domain.ports import marketplace_agreement_service
from app.packaging.entrypoints.marketplace_agreement_event_handler import config
from app.shared.adapters.message_bus import (
    command_bus,
    command_bus_metrics,
    event_bridge_message_bus,
    in_memory_command_bus,
    message_bus_metrics,
)
from app.shared.api import aws_events_api
from app.shared.instrumentation import power_tools_metrics
from app.shared.logging import boto_logger
from app.shared.middleware import event_handler


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus
    agreement_svc: marketplace_agreement_service.MarketplaceAgreementService
    model_config = ConfigDict(arbitrary_types_allowed=True)


# DI wiring for 6 event handlers + command bus + adapters. Long by nature;
# splitting hurts readability more than it helps.
def bootstrap(  # noqa: C901
    app_config: config.AppConfig,
    logger: logging.Logger,
    app: event_handler.EventBridgeEventResolver,
) -> Dependencies:
    """Wire the marketplace-agreement event listener.

    The listener is a pure observer — no aggregates, no repositories, no
    unit-of-work. External AWS EventBridge events are parsed into typed
    integration events, mapped to commands, and the command handlers
    fan them out onto the VEW domain event bus for downstream
    bounded-context reactions.
    """
    session = boto_logger.loggable_session(boto3.session.Session(), logger)

    events_client = session.client("events", region_name=app_config.get_default_region())
    events_api = aws_events_api.AWSEventsApi(client=events_client)

    metrics_client = power_tools_metrics.PowerToolsMetrics()

    message_bus = message_bus_metrics.MessageBusMetrics(
        inner=event_bridge_message_bus.EventBridgeMessageBus(
            events_api=events_api,
            event_bus_name=app_config.get_domain_event_bus_name(),
            bounded_context_name=app_config.get_bounded_context_name(),
            logger=logger,
        ),
        metrics_client=metrics_client,
        logger=logger,
    )

    def _activated_factory():
        def _handle(command):
            observe_marketplace_agreement_activated_command_handler.handle(
                command=command,
                msg_bus=message_bus,
            )

        return _handle

    def _amended_factory():
        def _handle(command):
            observe_marketplace_agreement_amended_command_handler.handle(
                command=command,
                msg_bus=message_bus,
            )

        return _handle

    def _ended_factory():
        def _handle(command):
            observe_marketplace_agreement_ended_command_handler.handle(
                command=command,
                msg_bus=message_bus,
            )

        return _handle

    def _ending_soon_factory():
        def _handle(command):
            observe_marketplace_agreement_ending_soon_command_handler.handle(
                command=command,
                msg_bus=message_bus,
            )

        return _handle

    def _renewal_terms_finalized_factory():
        def _handle(command):
            observe_marketplace_agreement_renewal_terms_finalized_command_handler.handle(
                command=command,
                msg_bus=message_bus,
            )

        return _handle

    def _renewal_upcoming_factory():
        def _handle(command):
            observe_marketplace_agreement_renewal_upcoming_command_handler.handle(
                command=command,
                msg_bus=message_bus,
            )

        return _handle

    cmd_bus = (
        command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=logger), metrics_client=metrics_client
        )
        .register_handler(
            observe_marketplace_agreement_activated_command.ObserveMarketplaceAgreementActivatedCommand,
            _activated_factory(),
        )
        .register_handler(
            observe_marketplace_agreement_amended_command.ObserveMarketplaceAgreementAmendedCommand,
            _amended_factory(),
        )
        .register_handler(
            observe_marketplace_agreement_ended_command.ObserveMarketplaceAgreementEndedCommand,
            _ended_factory(),
        )
        .register_handler(
            observe_marketplace_agreement_ending_soon_command.ObserveMarketplaceAgreementEndingSoonCommand,
            _ending_soon_factory(),
        )
        .register_handler(
            observe_marketplace_agreement_renewal_terms_finalized_command.ObserveMarketplaceAgreementRenewalTermsFinalizedCommand,  # noqa: E501
            _renewal_terms_finalized_factory(),
        )
        .register_handler(
            observe_marketplace_agreement_renewal_upcoming_command.ObserveMarketplaceAgreementRenewalUpcomingCommand,
            _renewal_upcoming_factory(),
        )
    )

    return Dependencies(
        command_bus=cmd_bus,
        # Used by the handler's AMI-only admission gate. The event payload
        # carries no product type, so the gate calls DescribeAgreement.
        agreement_svc=AwsMarketplaceDiscoveryService(
            region=app_config.get_default_region(),
            boto_session=session,
        ),
    )
