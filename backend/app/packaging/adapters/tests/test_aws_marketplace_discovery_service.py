import assertpy
import pytest
from botocore.exceptions import ClientError

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.adapters.tests.conftest import GlobalVariables


def test_should_list_active_agreements(mock_moto_calls, get_marketplace_discovery_srv):
    # ARRANGE
    # AWS `SearchAgreements` rejects the previous four-filter combo (Party +
    # AgreementType + Status + ResourceType) with `ValidationException:
    # UNSUPPORTED_FILTERS`. AMI-only enforcement now happens client-side.
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


def test_should_not_send_resource_type_filter_to_search_agreements(mock_moto_calls, get_marketplace_discovery_srv):
    """``SearchAgreements`` does not accept ``ResourceType`` combined with
    ``Status``: the four-filter combo fails with
    ``ValidationException(UNSUPPORTED_FILTERS)``. Only the base three
    filters may be sent."""
    # ACT
    get_marketplace_discovery_srv.list_active_agreements()

    # ASSERT
    _, called_kwargs = mock_moto_calls["SearchAgreements"].call_args
    filter_names = {f["name"] for f in called_kwargs["filters"]}
    assertpy.assert_that(filter_names).is_equal_to({"PartyType", "AgreementType", "Status"})


def test_should_drop_non_ami_agreements_client_side(mock_moto_calls, get_marketplace_discovery_srv):
    """AMI-only enforcement happens in the adapter, after the call. Any
    agreement whose resources include a non-AmiProduct type is filtered
    out before it reaches the caller."""
    # ARRANGE
    from datetime import datetime

    mock_moto_calls["SearchAgreements"].return_value = {
        "agreementViewSummaries": [
            {
                "agreementId": "agmt-ami-only",
                "proposalSummary": {
                    "resources": [{"id": "prod-ami-1", "type": "AmiProduct"}],
                    "offerId": "offer-1",
                },
                "status": "ACTIVE",
                "acceptanceTime": datetime(2024, 1, 1),
            },
            {
                "agreementId": "agmt-container",
                "proposalSummary": {
                    "resources": [{"id": "prod-container-1", "type": "ContainerProduct"}],
                    "offerId": "offer-2",
                },
                "status": "ACTIVE",
                "acceptanceTime": datetime(2024, 1, 1),
            },
            {
                "agreementId": "agmt-mixed-bundle",
                "proposalSummary": {
                    "resources": [
                        {"id": "prod-ami-2", "type": "AmiProduct"},
                        {"id": "prod-saas", "type": "SaaSProduct"},
                    ],
                    "offerId": "offer-3",
                },
                "status": "ACTIVE",
                "acceptanceTime": datetime(2024, 1, 1),
            },
            {
                "agreementId": "agmt-empty-resources",
                "proposalSummary": {"resources": [], "offerId": "offer-4"},
                "status": "ACTIVE",
                "acceptanceTime": datetime(2024, 1, 1),
            },
        ]
    }

    # ACT
    result = get_marketplace_discovery_srv.list_active_agreements()

    # ASSERT
    # Only agmt-ami-only survives: the Container agreement, the mixed
    # AMI+SaaS bundle (every resource must be an AmiProduct), and the
    # malformed empty-resources agreement are all dropped.
    assertpy.assert_that(result).is_length(1)
    assertpy.assert_that(result[0].agreementId).is_equal_to("agmt-ami-only")


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
    assertpy.assert_that(result[0].rootDeviceName).is_equal_to("/dev/sda1")


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


# ---------------------------------------------------------------------
# is_ami_agreement — the admission gate used by the buyer-side agreement
# event listener. DescribeAgreement is the only
# authoritative product-type source; no event payload carries one.
# ---------------------------------------------------------------------


def test_is_ami_agreement_returns_true_for_ami_only_agreement(mock_moto_calls, get_marketplace_discovery_srv):
    # ARRANGE
    mock_moto_calls["DescribeAgreement"].return_value = {
        "proposalSummary": {"resources": [{"id": "prod-ami-1", "type": "AmiProduct"}]},
    }

    # ACT / ASSERT
    assertpy.assert_that(get_marketplace_discovery_srv.is_ami_agreement("agmt-1")).is_true()
    _, called_kwargs = mock_moto_calls["DescribeAgreement"].call_args
    assertpy.assert_that(called_kwargs["agreementId"]).is_equal_to("agmt-1")


def test_is_ami_agreement_returns_false_for_non_ami_agreement(mock_moto_calls, get_marketplace_discovery_srv):
    # ARRANGE
    mock_moto_calls["DescribeAgreement"].return_value = {
        "proposalSummary": {"resources": [{"id": "prod-saas", "type": "SaaSProduct"}]},
    }

    # ACT / ASSERT
    assertpy.assert_that(get_marketplace_discovery_srv.is_ami_agreement("agmt-2")).is_false()


def test_is_ami_agreement_returns_false_for_mixed_bundle(mock_moto_calls, get_marketplace_discovery_srv):
    """Matches the invariant in list_active_agreements: EVERY resource must
    be an AmiProduct, so a bundle carrying one non-AMI resource is out."""
    # ARRANGE
    mock_moto_calls["DescribeAgreement"].return_value = {
        "proposalSummary": {
            "resources": [
                {"id": "prod-ami-2", "type": "AmiProduct"},
                {"id": "prod-container", "type": "ContainerProduct"},
            ]
        },
    }

    # ACT / ASSERT
    assertpy.assert_that(get_marketplace_discovery_srv.is_ami_agreement("agmt-3")).is_false()


def test_is_ami_agreement_returns_false_for_empty_resources(mock_moto_calls, get_marketplace_discovery_srv):
    """A malformed response is not a positive AMI identification."""
    # ARRANGE
    mock_moto_calls["DescribeAgreement"].return_value = {"proposalSummary": {"resources": []}}

    # ACT / ASSERT
    assertpy.assert_that(get_marketplace_discovery_srv.is_ami_agreement("agmt-4")).is_false()


def test_is_ami_agreement_raises_rather_than_degrading_on_access_denied(mock_moto_calls, get_marketplace_discovery_srv):
    """Unlike the discovery reads on this adapter, the gate must NOT
    degrade gracefully. An AccessDenied means the type is unknown; letting
    that read as False would silently drop real AMI events."""
    # ARRANGE
    from botocore.exceptions import ClientError

    mock_moto_calls["DescribeAgreement"].side_effect = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "denied"}}, "DescribeAgreement"
    )

    # ACT / ASSERT
    with pytest.raises(adapter_exception.AdapterException):
        get_marketplace_discovery_srv.is_ami_agreement("agmt-5")


def test_get_agreement_status_returns_the_described_status(mock_moto_calls, get_marketplace_discovery_srv):
    # ARRANGE
    mock_moto_calls["DescribeAgreement"].return_value = {"agreementId": "agmt-6", "status": "CANCELLED"}

    # ACT / ASSERT
    assertpy.assert_that(get_marketplace_discovery_srv.get_agreement_status("agmt-6")).is_equal_to("CANCELLED")
    _, called_kwargs = mock_moto_calls["DescribeAgreement"].call_args
    assertpy.assert_that(called_kwargs["agreementId"]).is_equal_to("agmt-6")


def test_get_agreement_status_raises_when_the_agreement_cannot_be_described(
    mock_moto_calls, get_marketplace_discovery_srv
):
    # ARRANGE
    mock_moto_calls["DescribeAgreement"].side_effect = ClientError(
        {"Error": {"Code": "ResourceNotFoundException", "Message": "no such agreement"}}, "DescribeAgreement"
    )

    # ACT / ASSERT
    with pytest.raises(adapter_exception.AdapterException):
        get_marketplace_discovery_srv.get_agreement_status("agmt-7")


def test_get_agreement_status_raises_when_aws_returns_no_status(mock_moto_calls, get_marketplace_discovery_srv):
    """An unknown status must not be read as any particular state."""
    # ARRANGE
    mock_moto_calls["DescribeAgreement"].return_value = {"agreementId": "agmt-8"}

    # ACT / ASSERT
    with pytest.raises(adapter_exception.AdapterException):
        get_marketplace_discovery_srv.get_agreement_status("agmt-8")


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


def _instance_type_offer_terms(offerId):
    return {
        "offerTerms": [
            {"legalTerm": {"id": "term-legal", "type": "LegalTerm"}},
            {
                "usageBasedPricingTerm": {
                    "id": "term-usage",
                    "rateCards": [
                        {
                            "rateCard": [
                                {"dimensionKey": "m7i.2xlarge", "price": "0"},
                                {"dimensionKey": "t3.medium" if offerId == "offer-private" else "m7i.2xlarge"},
                                {"dimensionKey": "UserHours", "price": "0"},
                            ]
                        }
                    ],
                }
            },
        ]
    }


def test_should_list_supported_instance_types_across_offers(mock_moto_calls, get_marketplace_discovery_srv):
    # ARRANGE: the shared mock map also serves the offer-discovery adapter, so these
    # two operations are set up here rather than in conftest.
    mock_moto_calls["ListPurchaseOptions"].return_value = {
        "purchaseOptions": [
            {"purchaseOptionId": "offer-public", "purchaseOptionType": "OFFER"},
            {"purchaseOptionId": "offer-private", "purchaseOptionType": "OFFER"},
        ]
    }
    mock_moto_calls["GetOfferTerms"].side_effect = _instance_type_offer_terms

    # ACT
    result = get_marketplace_discovery_srv.list_supported_instance_types("prod-ib2w5aw4ynhey")

    # ASSERT: union of all offers' usage dimensions that look like instance types
    mock_moto_calls["ListPurchaseOptions"].assert_called_once_with(
        filters=[{"filterType": "PRODUCT_ID", "filterValues": ["prod-ib2w5aw4ynhey"]}]
    )
    assertpy.assert_that(mock_moto_calls["GetOfferTerms"].call_count).is_equal_to(2)
    assertpy.assert_that(result).is_equal_to(["m7i.2xlarge", "t3.medium"])


def test_should_not_restrict_instance_types_when_offers_cannot_be_read(mock_moto_calls, get_marketplace_discovery_srv):
    # ARRANGE
    mock_moto_calls["ListPurchaseOptions"].side_effect = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "denied"}}, "ListPurchaseOptions"
    )

    # ACT / ASSERT
    assertpy.assert_that(get_marketplace_discovery_srv.list_supported_instance_types("prod-ib2w5aw4ynhey")).is_empty()
