from unittest import mock

import assertpy
import pytest

from app.publishing.adapters.exceptions import adapter_exception
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


def _client_error(code, operation):
    from botocore.exceptions import ClientError

    return ClientError({"Error": {"Code": code, "Message": code}}, operation)


def _create(get_license_manager_srv):
    return get_license_manager_srv.create_grant(
        license_arn=TEST_LICENSE_ARN,
        principal_arn=f"arn:aws:iam::{TEST_SPOKE_ACCOUNT_ID}:root",
        grant_name="test-grant",
        home_region="us-east-1",
    )


def test_a_refused_create_grant_raises_license_grant_rejected(mock_moto_calls, get_license_manager_srv):
    # The state machine catches this error name and falls back to the external-grant check.
    mock_moto_calls["CreateGrant"].side_effect = _client_error("AccessDeniedException", "CreateGrant")

    with pytest.raises(adapter_exception.LicenseGrantRejectedException):
        _create(get_license_manager_srv)


@pytest.mark.parametrize(
    "code",
    [
        "ThrottlingException",
        "RateLimitExceededException",
        "TooManyRequestsException",
        "ServerInternalException",
        "InternalServerException",
        "ServiceUnavailableException",
    ],
)
def test_a_transient_create_grant_error_is_not_reported_as_rejected(mock_moto_calls, get_license_manager_srv, code):
    # Retrying later can succeed, so it must not trigger the fallback.
    mock_moto_calls["CreateGrant"].side_effect = _client_error(code, "CreateGrant")

    with pytest.raises(adapter_exception.AdapterException) as error:
        _create(get_license_manager_srv)
    assertpy.assert_that(isinstance(error.value, adapter_exception.LicenseGrantRejectedException)).is_false()


def test_a_grant_the_spoke_never_received_raises_license_grant_rejected(mock_moto_calls, get_license_manager_srv):
    mock_moto_calls["ListReceivedGrants"] = mock.MagicMock(return_value={"Grants": []})

    with pytest.raises(adapter_exception.LicenseGrantRejectedException):
        get_license_manager_srv.accept_grant(
            TEST_GRANT_ARN, home_region="us-east-1", spoke_account_id=TEST_SPOKE_ACCOUNT_ID
        )
    mock_moto_calls["AcceptGrant"].assert_not_called()


def test_a_refused_accept_grant_raises_license_grant_rejected(mock_moto_calls, get_license_manager_srv):
    mock_moto_calls["ListReceivedGrants"] = mock.MagicMock(
        return_value={"Grants": [{"GrantArn": TEST_GRANT_ARN, "GrantStatus": "PENDING_ACCEPT"}]}
    )
    mock_moto_calls["AcceptGrant"].side_effect = _client_error("AccessDeniedException", "AcceptGrant")

    with pytest.raises(adapter_exception.LicenseGrantRejectedException):
        get_license_manager_srv.accept_grant(
            TEST_GRANT_ARN, home_region="us-east-1", spoke_account_id=TEST_SPOKE_ACCOUNT_ID
        )


def test_a_refused_grant_activation_raises_license_grant_rejected(mock_moto_calls, get_license_manager_srv):
    mock_moto_calls["ListReceivedGrants"] = mock.MagicMock(
        return_value={"Grants": [{"GrantArn": TEST_GRANT_ARN, "GrantStatus": "PENDING_ACCEPT"}]}
    )
    mock_moto_calls["CreateGrantVersion"].side_effect = _client_error("ValidationException", "CreateGrantVersion")

    with pytest.raises(adapter_exception.LicenseGrantRejectedException):
        get_license_manager_srv.accept_grant(
            TEST_GRANT_ARN, home_region="us-east-1", spoke_account_id=TEST_SPOKE_ACCOUNT_ID
        )


def test_a_throttled_accept_grant_is_not_reported_as_rejected(mock_moto_calls, get_license_manager_srv):
    mock_moto_calls["ListReceivedGrants"] = mock.MagicMock(
        return_value={"Grants": [{"GrantArn": TEST_GRANT_ARN, "GrantStatus": "PENDING_ACCEPT"}]}
    )
    mock_moto_calls["AcceptGrant"].side_effect = _client_error("ThrottlingException", "AcceptGrant")

    with pytest.raises(adapter_exception.AdapterException) as error:
        get_license_manager_srv.accept_grant(
            TEST_GRANT_ARN, home_region="us-east-1", spoke_account_id=TEST_SPOKE_ACCOUNT_ID
        )
    assertpy.assert_that(isinstance(error.value, adapter_exception.LicenseGrantRejectedException)).is_false()


# --- can_distribute_license ---------------------------------------------------------------
# The only condition is the licence's AllowedOperations. AWS accepted and activated grants
# from a plain member hub, without a delegated administrator and with the Organizations
# integration off (live test, Nov 2026), so no organization, RAM or settings call is made.


def test_can_distribute_license_is_true_when_the_license_allows_create_grant(mock_moto_calls, get_license_manager_srv):
    # ACT / ASSERT
    assertpy.assert_that(get_license_manager_srv.can_distribute_license(TEST_LICENSE_ARN, "us-east-1")).is_true()
    mock_moto_calls["ListReceivedLicenses"].assert_called_once_with(LicenseArns=[TEST_LICENSE_ARN])


def test_can_distribute_license_is_false_when_the_license_forbids_create_grant(
    mock_moto_calls, get_license_manager_srv, mock_list_received_licenses_response
):
    # ARRANGE
    mock_list_received_licenses_response["Licenses"][0]["ReceivedMetadata"]["AllowedOperations"] = ["CheckoutLicense"]

    # ACT / ASSERT
    assertpy.assert_that(get_license_manager_srv.can_distribute_license(TEST_LICENSE_ARN, "us-east-1")).is_false()


def test_can_distribute_license_is_false_when_the_hub_has_not_received_the_license(
    mock_moto_calls, get_license_manager_srv
):
    # ARRANGE
    mock_moto_calls["ListReceivedLicenses"].return_value = {"Licenses": []}

    # ACT / ASSERT
    assertpy.assert_that(get_license_manager_srv.can_distribute_license(TEST_LICENSE_ARN, "us-east-1")).is_false()


def test_can_distribute_license_is_false_instead_of_raising_on_access_denied(mock_moto_calls, get_license_manager_srv):
    # ARRANGE
    mock_moto_calls["ListReceivedLicenses"].side_effect = _client_error("AccessDeniedException", "ListReceivedLicenses")

    # ACT / ASSERT
    assertpy.assert_that(get_license_manager_srv.can_distribute_license(TEST_LICENSE_ARN, "us-east-1")).is_false()
