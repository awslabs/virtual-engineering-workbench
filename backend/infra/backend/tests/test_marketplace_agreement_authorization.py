"""Pins the authorization of the account-scoped Marketplace agreement routes.

Accepting a quote commits the hub AWS account to a purchase, and cancelling
ends one, for the whole account rather than a project. The Cedar condition on
those three actions is therefore the only thing deciding who may spend the
account's money, and it cannot be exercised in CI: Amazon Verified Permissions
is mocked everywhere, so no test evaluates the policy. These assertions pin
the statement's shape instead, so a change to who may call them has to be
deliberate.
"""

import assertpy
import pytest

from infra.auth import packaging_auth, packaging_auth_schema, shared_auth_schema

ACCOUNT_SCOPED_ACTIONS = (
    packaging_auth_schema.PackagingBCActions.AcceptMarketplaceQuote,
    packaging_auth_schema.PackagingBCActions.CancelMarketplaceAgreement,
    packaging_auth_schema.PackagingBCActions.ListMarketplaceAgreements,
)

TOTAL_ADMIN_ASSIGNMENTS = shared_auth_schema.SharedAttributes.TotalAdminAssignments


def _policies_mentioning(action) -> list:
    """Policies whose action list names ``action``."""
    quoted = f'VEW::Action::"{action.value}"'
    return [p for p in packaging_auth.packaging_bc_auth_policies if quoted in p.statement]


@pytest.mark.parametrize("action", ACCOUNT_SCOPED_ACTIONS)
def test_exactly_one_policy_permits_each_agreement_action(action):
    """A second permit for the same action would widen it unnoticed, because
    Cedar permits are a union."""
    # ACT
    policies = _policies_mentioning(action)

    # ASSERT
    assertpy.assert_that(policies).described_as(str(action)).is_length(1)


@pytest.mark.parametrize("action", ACCOUNT_SCOPED_ACTIONS)
def test_agreement_actions_require_an_admin_assignment(action):
    """Being an admin of at least one project is the condition. Removing it,
    or replacing it with a weaker attribute, would let any authenticated user
    buy and cancel subscriptions for the account."""
    # ARRANGE
    statement = _policies_mentioning(action)[0].statement

    # ACT / ASSERT
    assertpy.assert_that(statement).contains(f"principal has {TOTAL_ADMIN_ASSIGNMENTS}")
    assertpy.assert_that(statement).contains(f"principal.{TOTAL_ADMIN_ASSIGNMENTS} > 0")


@pytest.mark.parametrize("action", ACCOUNT_SCOPED_ACTIONS)
def test_agreement_actions_are_not_authorized_against_a_project(action):
    """These routes carry no /projects/<id>/ prefix, so the authorizer never
    resolves a VEW::Project resource for them. A resource.admins condition
    would deny every call instead of scoping anything."""
    # ARRANGE
    statement = _policies_mentioning(action)[0].statement

    # ACT / ASSERT
    assertpy.assert_that(statement).does_not_contain("resource.")


def test_project_scoped_marketplace_actions_keep_their_resource_condition():
    """Calibration for the three tests above: the procurement actions that do
    sit under /projects/<id>/ must still be scoped to that project, so an
    account-wide condition cannot quietly spread to them."""
    # ARRANGE
    project_scoped = (
        packaging_auth_schema.PackagingBCActions.ListMarketplacePurchaseOptions,
        packaging_auth_schema.PackagingBCActions.GetMarketplaceOffer,
        packaging_auth_schema.PackagingBCActions.CreateMarketplaceQuote,
    )

    for action in project_scoped:
        # ACT
        policies = _policies_mentioning(action)

        # ASSERT
        assertpy.assert_that(policies).described_as(str(action)).is_length(1)
        assertpy.assert_that(policies[0].statement).described_as(str(action)).contains("resource.admins")


@pytest.mark.parametrize("action", ACCOUNT_SCOPED_ACTIONS)
def test_agreement_action_descriptions_fit_the_avp_limit(action):
    """AVP caps a policy description at 150 characters and rejects a longer
    one when the change set is validated, which no other test reaches."""
    # ARRANGE
    description = _policies_mentioning(action)[0].description

    # ACT / ASSERT
    assertpy.assert_that(len(description)).described_as(description).is_less_than_or_equal_to(150)
