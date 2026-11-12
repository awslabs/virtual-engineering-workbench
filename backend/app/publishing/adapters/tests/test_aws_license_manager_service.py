from unittest import mock

import assertpy

from app.publishing.adapters.tests.conftest import (
    TEST_GRANT_ARN,
    TEST_LICENSE_ARN,
    TEST_SPOKE_ACCOUNT_ID,
)


def test_should_create_grant(mock_moto_calls, get_license_manager_srv):
    # ARRANGE
    license_arn = TEST_LICENSE_ARN
    principal_arn = f"arn:aws:iam::{TEST_SPOKE_ACCOUNT_ID}:root"
    grant_name = "test-grant"
    home_region = "us-east-1"

    # ACT
    result = get_license_manager_srv.create_grant(
        license_arn=license_arn,
        principal_arn=principal_arn,
        grant_name=grant_name,
        home_region=home_region,
    )

    # ASSERT
    create_grant_call = mock_moto_calls["CreateGrant"].call_args
    assertpy.assert_that(create_grant_call.kwargs["GrantName"]).is_equal_to(grant_name)
    assertpy.assert_that(create_grant_call.kwargs["LicenseArn"]).is_equal_to(license_arn)
    assertpy.assert_that(create_grant_call.kwargs["Principals"]).is_equal_to([principal_arn])
    assertpy.assert_that(create_grant_call.kwargs["HomeRegion"]).is_equal_to(home_region)
    assertpy.assert_that(create_grant_call.kwargs["AllowedOperations"]).is_equal_to(
        ["CheckoutLicense", "ListPurchasedLicenses"]
    )
    assertpy.assert_that(create_grant_call.kwargs["ClientToken"]).is_not_empty()
    assertpy.assert_that(result.grantArn).is_equal_to(TEST_GRANT_ARN)
    assertpy.assert_that(result.status).is_equal_to("PENDING_ACCEPTANCE")


def test_should_accept_grant(mock_moto_calls, get_license_manager_srv):
    # ARRANGE
    grant_arn = TEST_GRANT_ARN
    mock_moto_calls["ListReceivedGrants"] = mock.MagicMock(
        return_value={"Grants": [{"GrantArn": grant_arn, "GrantStatus": "PENDING_ACCEPT"}]}
    )

    # ACT
    get_license_manager_srv.accept_grant(grant_arn, home_region="us-east-1", spoke_account_id=TEST_SPOKE_ACCOUNT_ID)

    # ASSERT
    mock_moto_calls["AcceptGrant"].assert_called_once_with(GrantArn=grant_arn)
    cgv_call = mock_moto_calls["CreateGrantVersion"].call_args
    assertpy.assert_that(cgv_call.kwargs["GrantArn"]).is_equal_to(grant_arn)
    assertpy.assert_that(cgv_call.kwargs["Status"]).is_equal_to("ACTIVE")
    assertpy.assert_that(cgv_call.kwargs["Options"]).is_equal_to(
        {"ActivationOverrideBehavior": "ALL_GRANTS_PERMITTED_BY_ISSUER"}
    )
    mock_moto_calls["ListReceivedGrants"].assert_called_once_with(GrantArns=[grant_arn])


def test_should_get_license(mock_moto_calls, get_license_manager_srv):
    # ARRANGE
    license_arn = TEST_LICENSE_ARN

    # ACT
    result = get_license_manager_srv.get_license(license_arn)

    # ASSERT
    mock_moto_calls["GetLicense"].assert_called_once_with(LicenseArn=license_arn)
    assertpy.assert_that(result.licenseArn).is_equal_to(license_arn)
    assertpy.assert_that(result.homeRegion).is_equal_to("us-east-1")


def test_should_verify_image_accessible_when_found(mock_moto_calls, get_license_manager_srv):
    # ARRANGE
    ami_id = "ami-12345678"
    region = "eu-west-1"
    account_id = TEST_SPOKE_ACCOUNT_ID

    # ACT
    result = get_license_manager_srv.verify_image_accessible(ami_id, region, account_id)

    # ASSERT
    mock_moto_calls["AssumeRole"].assert_called_once()
    assertpy.assert_that(result).is_true()


def test_should_verify_image_accessible_when_not_found(mock_moto_calls, get_license_manager_srv):
    # ARRANGE
    mock_moto_calls["DescribeImages"].return_value = {"Images": []}

    # ACT
    result = get_license_manager_srv.verify_image_accessible("ami-notfound", "eu-west-1", TEST_SPOKE_ACCOUNT_ID)

    # ASSERT
    assertpy.assert_that(result).is_false()


def test_should_recover_existing_grant_when_recipient_already_has_grant(mock_moto_calls, get_license_manager_srv):
    # ARRANGE — CreateGrant fails because grant already exists
    from botocore.exceptions import ClientError

    mock_moto_calls["CreateGrant"].side_effect = ClientError(
        {
            "Error": {
                "Code": "ValidationException",
                "Message": "Grant cannot be created because the Grant recipient account already has a grant for this license or product.",
            }
        },
        "CreateGrant",
    )
    mock_moto_calls["ListDistributedGrants"].return_value = {
        "Grants": [
            {
                "GrantArn": TEST_GRANT_ARN,
                "GranteePrincipalArn": f"arn:aws:iam::{TEST_SPOKE_ACCOUNT_ID}:root",
                "GrantStatus": "PENDING_ACCEPT",
            }
        ]
    }

    # ACT
    result = get_license_manager_srv.create_grant(
        license_arn=TEST_LICENSE_ARN,
        principal_arn=f"arn:aws:iam::{TEST_SPOKE_ACCOUNT_ID}:root",
        grant_name="test-grant",
        home_region="us-east-1",
    )

    # ASSERT
    assertpy.assert_that(result.grantArn).is_equal_to(TEST_GRANT_ARN)
    assertpy.assert_that(result.status).is_equal_to("PENDING_ACCEPT")
    mock_moto_calls["ListDistributedGrants"].assert_called_once()


def test_should_skip_accept_when_grant_already_active(mock_moto_calls, get_license_manager_srv):
    # ARRANGE — grant is already ACTIVE
    grant_arn = TEST_GRANT_ARN
    mock_moto_calls["ListReceivedGrants"] = mock.MagicMock(
        return_value={"Grants": [{"GrantArn": grant_arn, "GrantStatus": "ACTIVE"}]}
    )

    # ACT
    get_license_manager_srv.accept_grant(grant_arn, home_region="us-east-1", spoke_account_id=TEST_SPOKE_ACCOUNT_ID)

    # ASSERT — neither AcceptGrant nor CreateGrantVersion should be called
    mock_moto_calls["AcceptGrant"].assert_not_called()
    mock_moto_calls["CreateGrantVersion"].assert_not_called()
    mock_moto_calls["ListReceivedGrants"].assert_called_once_with(GrantArns=[grant_arn])


def test_can_distribute_license_requires_both_the_flag_and_the_resource_share(mock_moto_calls, get_license_manager_srv):
    """EnableIntegration reads back true the moment the setting is saved, but the RAM
    resource share that actually permits a cross-account grant takes around half an
    hour to propagate. Trusting the flag alone would upgrade an externally-managed
    subscription to a grant inside that window, where CreateGrant still fails."""
    # ARRANGE — integration on, share already propagated (the conftest default)

    # ACT / ASSERT
    assertpy.assert_that(get_license_manager_srv.can_distribute_license()).is_true()

    # ARRANGE — integration on, share not there yet
    mock_moto_calls["GetServiceSettings"].return_value = {"OrganizationConfiguration": {"EnableIntegration": True}}

    # ACT / ASSERT
    assertpy.assert_that(get_license_manager_srv.can_distribute_license()).is_false()


def test_can_distribute_license_is_false_when_the_integration_is_off(mock_moto_calls, get_license_manager_srv):
    # ARRANGE
    mock_moto_calls["GetServiceSettings"].return_value = {
        "OrganizationConfiguration": {"EnableIntegration": False},
        "LicenseManagerResourceShareArn": "arn:aws:ram:us-east-1:111111111111:resource-share/lm-abc123",
    }

    # ACT / ASSERT
    assertpy.assert_that(get_license_manager_srv.can_distribute_license()).is_false()


def test_can_distribute_license_is_false_without_any_organization_configuration(
    mock_moto_calls, get_license_manager_srv
):
    # ARRANGE
    mock_moto_calls["GetServiceSettings"].return_value = {}

    # ACT / ASSERT
    assertpy.assert_that(get_license_manager_srv.can_distribute_license()).is_false()
