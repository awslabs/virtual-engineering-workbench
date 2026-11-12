import assertpy
import pytest
from botocore.exceptions import ClientError

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.adapters.tests.conftest import GlobalVariables


def test_should_list_active_agreements(mock_moto_calls, get_marketplace_discovery_srv):
    # ARRANGE
    expected_kwargs = {
        "catalog": "AWSMarketplace",
        "filters": [
            {"name": "PartyType", "values": ["Acceptor"]},
            {"name": "AgreementType", "values": ["PurchaseAgreement"]},
            {"name": "Status", "values": ["ACTIVE"]},
        ],
    }

    # ACT
    result = get_marketplace_discovery_srv.list_active_agreements()

    # ASSERT
    mock_moto_calls["SearchAgreements"].assert_called_once_with(**expected_kwargs)
    assertpy.assert_that(result).is_length(1)
    assertpy.assert_that(result[0].agreementId).is_equal_to(GlobalVariables.TEST_MARKETPLACE_AGREEMENT_ID.value)
    assertpy.assert_that(result[0].productId).is_equal_to(GlobalVariables.TEST_MARKETPLACE_PRODUCT_ID.value)
    assertpy.assert_that(result[0].status).is_equal_to("ACTIVE")


def test_should_list_active_agreements_when_empty(mock_moto_calls, get_marketplace_discovery_srv):
    # ARRANGE
    mock_moto_calls["SearchAgreements"].return_value = {"AgreementViewSummaries": []}

    # ACT
    result = get_marketplace_discovery_srv.list_active_agreements()

    # ASSERT
    assertpy.assert_that(result).is_empty()


def test_should_return_empty_agreements_when_access_denied(mock_moto_calls, get_marketplace_discovery_srv):
    # ARRANGE
    mock_moto_calls["SearchAgreements"].side_effect = ClientError(
        error_response={"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}},
        operation_name="SearchAgreements",
    )

    # ACT
    result = get_marketplace_discovery_srv.list_active_agreements()

    # ASSERT
    assertpy.assert_that(result).is_empty()


def test_should_raise_on_unexpected_agreements_error(mock_moto_calls, get_marketplace_discovery_srv):
    # ARRANGE
    mock_moto_calls["SearchAgreements"].side_effect = ClientError(
        error_response={"Error": {"Code": "InternalServerException", "Message": "Server error"}},
        operation_name="SearchAgreements",
    )

    # ACT / ASSERT
    with pytest.raises(adapter_exception.AdapterException):
        get_marketplace_discovery_srv.list_active_agreements()


def test_should_list_marketplace_amis_by_product_code(mock_moto_calls, get_marketplace_discovery_srv):
    # ARRANGE
    product_code = GlobalVariables.TEST_MARKETPLACE_PRODUCT_CODE.value
    region = "us-east-1"
    expected_kwargs = {
        "Owners": ["aws-marketplace"],
        # Deprecated images must be listed, or a subscription whose AMIs are all
        # past their deprecation date looks like one with no AMI at all.
        "IncludeDeprecated": True,
        "Filters": [
            {"Name": "product-code", "Values": [product_code]},
            {"Name": "state", "Values": ["available"]},
        ],
    }

    # ACT
    result = get_marketplace_discovery_srv.list_marketplace_amis_by_product_code(product_code, region)

    # ASSERT
    mock_moto_calls["DescribeImages"].assert_called_with(**expected_kwargs)
    assertpy.assert_that(result).is_length(1)
    assertpy.assert_that(result[0].amiId).is_equal_to(GlobalVariables.TEST_AMI_ID.value)
    assertpy.assert_that(result[0].region).is_equal_to(region)


def test_should_list_received_licenses(mock_moto_calls, get_marketplace_discovery_srv):
    # ACT
    result = get_marketplace_discovery_srv.list_received_licenses()

    # ASSERT
    mock_moto_calls["ListReceivedLicenses"].assert_called_once()
    assertpy.assert_that(result).is_length(1)
    assertpy.assert_that(result[0].licenseArn).is_equal_to(GlobalVariables.TEST_LICENSE_ARN.value)
    assertpy.assert_that(result[0].status).is_equal_to("AVAILABLE")
    assertpy.assert_that(result[0].issuer).is_equal_to(GlobalVariables.TEST_LICENSE_ISSUER.value)


def test_should_return_empty_licenses_when_access_denied(mock_moto_calls, get_marketplace_discovery_srv):
    # ARRANGE — SLR AWSServiceRoleForMarketplaceLicenseManagement missing
    mock_moto_calls["ListReceivedLicenses"].side_effect = ClientError(
        error_response={"Error": {"Code": "AccessDeniedException", "Message": "Service role not found"}},
        operation_name="ListReceivedLicenses",
    )

    # ACT
    result = get_marketplace_discovery_srv.list_received_licenses()

    # ASSERT
    assertpy.assert_that(result).is_empty()


def test_should_return_empty_licenses_when_authorization_exception(mock_moto_calls, get_marketplace_discovery_srv):
    # ARRANGE
    mock_moto_calls["ListReceivedLicenses"].side_effect = ClientError(
        error_response={"Error": {"Code": "AuthorizationException", "Message": "Not authorized"}},
        operation_name="ListReceivedLicenses",
    )

    # ACT
    result = get_marketplace_discovery_srv.list_received_licenses()

    # ASSERT
    assertpy.assert_that(result).is_empty()


def test_should_raise_on_unexpected_licenses_error(mock_moto_calls, get_marketplace_discovery_srv):
    # ARRANGE
    mock_moto_calls["ListReceivedLicenses"].side_effect = ClientError(
        error_response={"Error": {"Code": "ServerInternalException", "Message": "Server error"}},
        operation_name="ListReceivedLicenses",
    )

    # ACT / ASSERT
    with pytest.raises(adapter_exception.AdapterException):
        get_marketplace_discovery_srv.list_received_licenses()


def test_should_pick_the_newest_ami_when_a_region_publishes_several(mock_moto_calls, get_marketplace_discovery_srv):
    """describe_images has no defined order, so the regional map must not depend on it.

    Returning the AMIs newest-last and then newest-first has to give the same answer;
    taking whichever arrived last would give a different one each way.
    """
    # ARRANGE
    product_code = GlobalVariables.TEST_MARKETPLACE_PRODUCT_CODE.value

    def _ami(ami_id: str, creation_date: str) -> dict:
        return {
            "ImageId": ami_id,
            "State": "available",
            "OwnerId": GlobalVariables.TEST_IMAGE_OWNER_ID.value,
            "Architecture": "x86_64",
            "PlatformDetails": "Linux/UNIX",
            "Name": ami_id,
            "Description": "Test AMI",
            "BlockDeviceMappings": [],
            "CreationDate": creation_date,
            "ProductCodes": [
                {"ProductCodeId": product_code, "ProductCodeType": "marketplace"},
            ],
        }

    older = _ami("ami-older", "2026-01-01T00:00:00.000Z")
    newer = _ami("ami-newer", "2026-06-01T00:00:00.000Z")

    # ACT
    mock_moto_calls["DescribeImages"].return_value = {"Images": [older, newer]}
    newest_last = get_marketplace_discovery_srv.get_regional_ami_ids(product_code, ["us-east-1"])

    mock_moto_calls["DescribeImages"].return_value = {"Images": [newer, older]}
    newest_first = get_marketplace_discovery_srv.get_regional_ami_ids(product_code, ["us-east-1"])

    # ASSERT
    assertpy.assert_that(newest_last).is_equal_to({"us-east-1": "ami-newer"})
    assertpy.assert_that(newest_first).is_equal_to(newest_last)


def test_should_skip_a_region_that_publishes_no_ami(mock_moto_calls, get_marketplace_discovery_srv):
    # ARRANGE
    mock_moto_calls["DescribeImages"].return_value = {"Images": []}

    # ACT
    result = get_marketplace_discovery_srv.get_regional_ami_ids(
        GlobalVariables.TEST_MARKETPLACE_PRODUCT_CODE.value, ["us-east-1"]
    )

    # ASSERT
    assertpy.assert_that(result).is_empty()
