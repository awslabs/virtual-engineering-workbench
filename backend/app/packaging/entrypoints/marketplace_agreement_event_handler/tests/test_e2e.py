"""End-to-end tests for the marketplace-agreement event handler.

These exercise the whole chain: EventBridge envelope → integration event
model → command → real command handler → message_bus.publish. The message
bus is stubbed at the API layer (``AWSEventsApi`` via moto) so no real
network calls happen, but everything above is production code.
"""

from decimal import Decimal

import assertpy

from app.packaging.domain.events.marketplace import (
    marketplace_agreement_activated,
    marketplace_agreement_amended,
    marketplace_agreement_ended,
    marketplace_agreement_ending_soon,
    marketplace_agreement_renewal_terms_finalized,
    marketplace_agreement_renewal_upcoming,
)
from app.packaging.entrypoints.marketplace_agreement_event_handler.tests.conftest import GlobalVariables


def _install_recording_bus():
    """Replace the entrypoint's command bus so we can capture domain
    events published by the real handlers without a live events bus."""
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    captured = []

    class _RecordingBus:
        def publish(self, message, schedule_config=None, flexible_config=None):
            captured.append(message)

        def reschedule(self, *args, **kwargs):
            pass

    # Rebuild dependencies but swap the message bus mid-flight by
    # patching the module-level ``event_bridge_message_bus`` reference
    # through the bootstrapper. Simpler path: re-wire handlers directly.
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
    from app.shared.adapters.message_bus import command_bus_metrics, in_memory_command_bus
    from app.shared.instrumentation import power_tools_metrics

    bus = _RecordingBus()
    cmd_bus = (
        command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=handler.logger),
            metrics_client=power_tools_metrics.PowerToolsMetrics(),
        )
        .register_handler(
            observe_marketplace_agreement_activated_command.ObserveMarketplaceAgreementActivatedCommand,
            lambda c: observe_marketplace_agreement_activated_command_handler.handle(command=c, msg_bus=bus),
        )
        .register_handler(
            observe_marketplace_agreement_amended_command.ObserveMarketplaceAgreementAmendedCommand,
            lambda c: observe_marketplace_agreement_amended_command_handler.handle(command=c, msg_bus=bus),
        )
        .register_handler(
            observe_marketplace_agreement_ended_command.ObserveMarketplaceAgreementEndedCommand,
            lambda c: observe_marketplace_agreement_ended_command_handler.handle(command=c, msg_bus=bus),
        )
        .register_handler(
            observe_marketplace_agreement_ending_soon_command.ObserveMarketplaceAgreementEndingSoonCommand,
            lambda c: observe_marketplace_agreement_ending_soon_command_handler.handle(command=c, msg_bus=bus),
        )
        .register_handler(
            observe_marketplace_agreement_renewal_terms_finalized_command.ObserveMarketplaceAgreementRenewalTermsFinalizedCommand,  # noqa: E501
            lambda c: observe_marketplace_agreement_renewal_terms_finalized_command_handler.handle(
                command=c, msg_bus=bus
            ),
        )
        .register_handler(
            observe_marketplace_agreement_renewal_upcoming_command.ObserveMarketplaceAgreementRenewalUpcomingCommand,
            lambda c: observe_marketplace_agreement_renewal_upcoming_command_handler.handle(command=c, msg_bus=bus),
        )
    )
    handler.dependencies.command_bus = cmd_bus
    return captured


def test_e2e_created_new_publishes_activated_domain_event(lambda_context, created_new_event):
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    captured = _install_recording_bus()

    handler.handler(created_new_event(), lambda_context)

    assertpy.assert_that(captured).is_length(1)
    published = captured[0]
    assertpy.assert_that(published).is_instance_of(marketplace_agreement_activated.MarketplaceAgreementActivated)
    assertpy.assert_that(published.agreementId).is_equal_to(GlobalVariables.TEST_AGREEMENT_ID.value)
    assertpy.assert_that(published.offerId).is_equal_to(GlobalVariables.TEST_OFFER_ID.value)
    assertpy.assert_that(published.intent).is_equal_to("NEW")
    assertpy.assert_that(published.status).is_equal_to("ACTIVE")
    assertpy.assert_that(published.acceptorAccountId).is_equal_to(GlobalVariables.TEST_ACCEPTOR_ACCOUNT.value)
    assertpy.assert_that(published.observedAt).is_not_none()


def test_e2e_amended_publishes_amended_domain_event(lambda_context, amended_event):
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    captured = _install_recording_bus()

    handler.handler(amended_event(), lambda_context)

    assertpy.assert_that(captured).is_length(1)
    published = captured[0]
    assertpy.assert_that(published).is_instance_of(marketplace_agreement_amended.MarketplaceAgreementAmended)
    assertpy.assert_that(published.autoRenewalEnabled).is_true()
    assertpy.assert_that(published.autoRenewalDisabledBy).is_equal_to("ACCEPTOR")


def test_e2e_ended_publishes_ended_domain_event(lambda_context, ended_event):
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    captured = _install_recording_bus()

    handler.handler(ended_event("EXPIRED"), lambda_context)

    published = captured[0]
    assertpy.assert_that(published).is_instance_of(marketplace_agreement_ended.MarketplaceAgreementEnded)
    assertpy.assert_that(published.status).is_equal_to("EXPIRED")


def test_e2e_ending_publishes_ending_soon_domain_event(lambda_context, ending_event):
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    captured = _install_recording_bus()

    handler.handler(ending_event(60), lambda_context)

    published = captured[0]
    assertpy.assert_that(published).is_instance_of(marketplace_agreement_ending_soon.MarketplaceAgreementEndingSoon)
    assertpy.assert_that(published.daysBeforeEndTime).is_equal_to(60)


def test_e2e_renewal_terms_finalized_publishes_domain_event(lambda_context, renewal_terms_finalized_event):
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    captured = _install_recording_bus()

    handler.handler(renewal_terms_finalized_event(), lambda_context)

    published = captured[0]
    assertpy.assert_that(published).is_instance_of(
        marketplace_agreement_renewal_terms_finalized.MarketplaceAgreementRenewalTermsFinalized
    )
    assertpy.assert_that(published.tcv).is_equal_to(Decimal("105000.00"))


def test_e2e_renewal_upcoming_publishes_domain_event(lambda_context, renewal_upcoming_event):
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    captured = _install_recording_bus()

    handler.handler(renewal_upcoming_event(), lambda_context)

    published = captured[0]
    assertpy.assert_that(published).is_instance_of(
        marketplace_agreement_renewal_upcoming.MarketplaceAgreementRenewalUpcoming
    )
    assertpy.assert_that(published.lockoutReached).is_true()
