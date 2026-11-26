from unittest import mock

import assertpy

from app.packaging.domain.commands.marketplace import (
    observe_marketplace_agreement_activated_command,
    observe_marketplace_agreement_amended_command,
    observe_marketplace_agreement_ended_command,
    observe_marketplace_agreement_ending_soon_command,
    observe_marketplace_agreement_renewal_terms_finalized_command,
    observe_marketplace_agreement_renewal_upcoming_command,
)


def _build_activated_command():
    from app.packaging.domain.value_objects.marketplace import agreement_id_value_object, offer_id_value_object

    return observe_marketplace_agreement_activated_command.ObserveMarketplaceAgreementActivatedCommand(
        agreementId=agreement_id_value_object.from_str("agmt-x"),
        offerId=offer_id_value_object.from_str("offer-x"),
        productId=None,
        intent="NEW",
        status="ACTIVE",
        startTime=None,
        endTime=None,
        acceptanceTime=None,
        previousAgreementId=None,
        proposerAccountId="p",
        acceptorAccountId="a",
        requestId="r",
        catalog="AWSMarketplace",
    )


def test_bootstrapper_wires_activated_command_to_a_real_handler():
    """Round-trip a real Command through the bus and assert the handler
    module's ``handle`` is invoked. This avoids reaching into private
    ``_command_handlers`` internals — a refactor of InMemoryCommandBus
    that renames that dict won't break this test with a misleading
    error, and the test still guards the wiring.
    """
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    with mock.patch(
        "app.packaging.domain.command_handlers.marketplace."
        "observe_marketplace_agreement_activated_command_handler.handle"
    ) as mocked_handle:
        handler.dependencies.command_bus.handle(_build_activated_command())

    mocked_handle.assert_called_once()


def test_bootstrapper_registers_all_six_command_types_without_missing_handlers():
    """Second wiring guard: every one of the six Observe* commands
    round-trips without raising 'Command X does not have registered
    handlers'. Patches every downstream handler to a no-op so we test
    only registration, not business logic."""
    from app.packaging.domain.value_objects.marketplace import agreement_id_value_object, offer_id_value_object
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    commands = [
        _build_activated_command(),
        observe_marketplace_agreement_amended_command.ObserveMarketplaceAgreementAmendedCommand(
            agreementId=agreement_id_value_object.from_str("agmt-x"),
            offerId=offer_id_value_object.from_str("offer-x"),
            productId=None,
            intent="AMEND",
            status="ACTIVE",
            startTime=None,
            endTime=None,
            autoRenewalEnabled=None,
            autoRenewalDisabledBy=None,
            lockoutStartTime=None,
            proposerAccountId="p",
            acceptorAccountId="a",
            requestId="r",
            catalog="AWSMarketplace",
        ),
        observe_marketplace_agreement_ended_command.ObserveMarketplaceAgreementEndedCommand(
            agreementId=agreement_id_value_object.from_str("agmt-x"),
            offerId=offer_id_value_object.from_str("offer-x"),
            status="EXPIRED",
            proposerAccountId="p",
            acceptorAccountId="a",
            requestId="r",
            catalog="AWSMarketplace",
        ),
        observe_marketplace_agreement_ending_soon_command.ObserveMarketplaceAgreementEndingSoonCommand(
            agreementId=agreement_id_value_object.from_str("agmt-x"),
            offerId=offer_id_value_object.from_str("offer-x"),
            productId=None,
            daysBeforeEndTime=60,
            status="ACTIVE",
            startTime=None,
            endTime="2025-01-01T00:00:00Z",
            autoRenewalEnabled=None,
            autoRenewalDisabledBy=None,
            lockoutStartTime=None,
            proposerAccountId="p",
            acceptorAccountId="a",
            requestId="r",
            catalog="AWSMarketplace",
        ),
        observe_marketplace_agreement_renewal_terms_finalized_command.ObserveMarketplaceAgreementRenewalTermsFinalizedCommand(  # noqa: E501
            agreementId=agreement_id_value_object.from_str("agmt-x"),
            productId=None,
            startTime=None,
            endTime=None,
            tcv=None,
            currency=None,
            termsFinalizedTime=None,
            lockoutReached=None,
            lockoutStartTime=None,
            proposerAccountId="p",
            acceptorAccountId="a",
            requestId="r",
            catalog="AWSMarketplace",
        ),
        observe_marketplace_agreement_renewal_upcoming_command.ObserveMarketplaceAgreementRenewalUpcomingCommand(
            agreementId=agreement_id_value_object.from_str("agmt-x"),
            productId=None,
            startTime=None,
            endTime=None,
            tcv=None,
            currency=None,
            lockoutReached=None,
            proposerAccountId="p",
            acceptorAccountId="a",
            requestId="r",
            catalog="AWSMarketplace",
        ),
    ]

    patch_targets = [
        "app.packaging.domain.command_handlers.marketplace."
        "observe_marketplace_agreement_activated_command_handler.handle",
        "app.packaging.domain.command_handlers.marketplace."
        "observe_marketplace_agreement_amended_command_handler.handle",
        "app.packaging.domain.command_handlers.marketplace."
        "observe_marketplace_agreement_ended_command_handler.handle",
        "app.packaging.domain.command_handlers.marketplace."
        "observe_marketplace_agreement_ending_soon_command_handler.handle",
        "app.packaging.domain.command_handlers.marketplace."
        "observe_marketplace_agreement_renewal_terms_finalized_command_handler.handle",
        "app.packaging.domain.command_handlers.marketplace."
        "observe_marketplace_agreement_renewal_upcoming_command_handler.handle",
    ]

    with mock.patch(patch_targets[0]) as m0, mock.patch(patch_targets[1]) as m1, mock.patch(
        patch_targets[2]
    ) as m2, mock.patch(patch_targets[3]) as m3, mock.patch(patch_targets[4]) as m4, mock.patch(patch_targets[5]) as m5:
        for c in commands:
            handler.dependencies.command_bus.handle(c)

        for mocked in (m0, m1, m2, m3, m4, m5):
            assertpy.assert_that(mocked.call_count).is_equal_to(1)
