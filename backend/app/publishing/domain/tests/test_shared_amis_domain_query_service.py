from unittest import mock

import assertpy
import pytest

from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import shared_ami, version
from app.publishing.domain.ports import image_service, shared_amis_query_service
from app.publishing.domain.query_services import shared_amis_domain_query_service
from app.publishing.domain.value_objects import (
    ami_id_value_object,
    aws_account_id_value_object,
    product_id_value_object,
    product_type_value_object,
    region_value_object,
    version_id_value_object,
)

TEST_ORIGINAL_AMI_REGION = "us-east-1"


@pytest.fixture()
def image_svc_mock():
    image_svc_mock = mock.create_autospec(spec=image_service.ImageService)
    return image_svc_mock


@pytest.fixture()
def shared_amis_qry_svc_mock():
    shared_amis_qry_svc_mock = mock.create_autospec(spec=shared_amis_query_service.SharedAMIsQueryService)
    shared_amis_qry_svc_mock.get_shared_amis.return_value = []
    return shared_amis_qry_svc_mock


def _version(region: str) -> version.Version:
    return version.Version(
        versionId="vers-11111111",
        projectId="proj-12345",
        productId="prod-11111111",
        scPortfolioId="port-12345",
        versionDescription="Workbench version description",
        versionName="1.0.0",
        versionType=version.VersionType.Released.text,
        technologyId="tech-12345",
        awsAccountId="123456789012",
        stage="DEV",
        region=region,
        originalAmiId="ami-023c04780e65e723c",
        status=version.VersionStatus.Created,
        isRecommendedVersion=True,
        createDate="2023-06-20T00:00:00+00:00",
        lastUpdateDate="2023-06-20T00:00:00+00:00",
        createdBy="T0037SG",
        lastUpdatedBy="T0037SG",
    )


def _shared_ami(region: str, aws_account_id: str = "123456789012", copied_ami_id: str = "ami-copy"):
    return shared_ami.SharedAmi(
        originalAmiId="ami-023c04780e65e723c",
        copiedAmiId=copied_ami_id,
        awsAccountId=aws_account_id,
        region=region,
        createDate="2023-06-20T00:00:00+00:00",
        lastUpdateDate="2023-06-20T00:00:00+00:00",
    )


@pytest.mark.parametrize(
    "is_ami_shared,region,decision",
    (
        (True, "us-east-1", shared_amis_domain_query_service.ShareAmiDecision.Done),
        (True, "us-central-1", shared_amis_domain_query_service.ShareAmiDecision.Done),
        (
            False,
            "us-east-1",
            shared_amis_domain_query_service.ShareAmiDecision.Share,
        ),
        (
            False,
            "us-central-1",
            shared_amis_domain_query_service.ShareAmiDecision.Copy,
        ),
    ),
)
def test_make_share_ami_decision_makes_correct_decision(
    is_ami_shared, region, decision, image_svc_mock, shared_amis_qry_svc_mock, mock_unit_of_work, mock_version_repo
):
    # ARRANGE
    mock_version_repo.get.return_value = _version(region)
    shared_amis_qry_svc_mock.get_shared_amis.return_value = [_shared_ami(region)] if is_ami_shared else []
    domain_service = shared_amis_domain_query_service.SharedAMIsDomainQueryService(
        unit_of_work=mock_unit_of_work,
        image_svc=image_svc_mock,
        shared_amis_qry_svc=shared_amis_qry_svc_mock,
        default_original_ami_region=TEST_ORIGINAL_AMI_REGION,
    )

    # ACT
    result = domain_service.make_share_ami_decision(
        product_id=product_id_value_object.from_str("prod-11111111"),
        version_id=version_id_value_object.from_str("vers-11111111"),
        aws_account_id=aws_account_id_value_object.from_str("123456789012"),
        product_type=product_type_value_object.from_str("WORKBENCH"),
    )
    # ASSERT
    assertpy.assert_that(result.decision).is_equal_to(decision)
    assertpy.assert_that(result.region).is_equal_to(region)
    assertpy.assert_that(result.original_ami_id).is_equal_to("ami-023c04780e65e723c")
    assertpy.assert_that(result.copied_ami_id).is_equal_to("ami-copy" if is_ami_shared else None)


@pytest.mark.parametrize(
    "existing,decision",
    (
        # Shared to this account in another region only: the version's region still needs its own copy.
        ([_shared_ami("us-east-1")], shared_amis_domain_query_service.ShareAmiDecision.Copy),
        # Shared to another account in this region only.
        (
            [_shared_ami("eu-west-1", aws_account_id="210987654321")],
            shared_amis_domain_query_service.ShareAmiDecision.Copy,
        ),
        # Shared to this account in both regions: the version's region is reused.
        (
            [
                _shared_ami("us-east-1", copied_ami_id="ami-useast1"),
                _shared_ami("eu-west-1", copied_ami_id="ami-euwest1"),
            ],
            shared_amis_domain_query_service.ShareAmiDecision.Done,
        ),
    ),
)
def test_make_share_ami_decision_matches_the_version_region(
    existing, decision, image_svc_mock, shared_amis_qry_svc_mock, mock_unit_of_work, mock_version_repo
):
    # ARRANGE
    mock_version_repo.get.return_value = _version("eu-west-1")
    shared_amis_qry_svc_mock.get_shared_amis.return_value = existing
    domain_service = shared_amis_domain_query_service.SharedAMIsDomainQueryService(
        unit_of_work=mock_unit_of_work,
        image_svc=image_svc_mock,
        shared_amis_qry_svc=shared_amis_qry_svc_mock,
        default_original_ami_region=TEST_ORIGINAL_AMI_REGION,
    )

    # ACT
    result = domain_service.make_share_ami_decision(
        product_id=product_id_value_object.from_str("prod-11111111"),
        version_id=version_id_value_object.from_str("vers-11111111"),
        aws_account_id=aws_account_id_value_object.from_str("123456789012"),
        product_type=product_type_value_object.from_str("WORKBENCH"),
    )

    # ASSERT
    assertpy.assert_that(result.decision).is_equal_to(decision)
    assertpy.assert_that(result.copied_ami_id).is_equal_to(
        "ami-euwest1" if decision == shared_amis_domain_query_service.ShareAmiDecision.Done else None
    )


@pytest.mark.parametrize(
    "response,outcome",
    [
        ("pending", False),
        ("available", True),
    ],
)
def test_verify_copy_checks_if_copy_is_ready(response, outcome, image_svc_mock, shared_amis_qry_svc_mock, uow_mock):
    # ARRANGE
    image_svc_mock.get_copied_ami_status.return_value = response
    domain_service = shared_amis_domain_query_service.SharedAMIsDomainQueryService(
        unit_of_work=uow_mock,
        image_svc=image_svc_mock,
        shared_amis_qry_svc=shared_amis_qry_svc_mock,
        default_original_ami_region=TEST_ORIGINAL_AMI_REGION,
    )
    # ACT
    is_copy_ready = domain_service.verify_copy(
        region_value_object.RegionValueObject("eu-west-3"),
        ami_id_value_object.AmiIdValueObject("copy-12345"),
    )
    # ASSERT
    assertpy.assert_that(is_copy_ready).is_equal_to(outcome)


def test_verify_copy_raises_exception_when_status_invalid(image_svc_mock, shared_amis_qry_svc_mock, uow_mock):
    # ARRANGE
    image_svc_mock.get_copied_ami_status.return_value = "invalid"
    domain_service = shared_amis_domain_query_service.SharedAMIsDomainQueryService(
        unit_of_work=uow_mock,
        image_svc=image_svc_mock,
        shared_amis_qry_svc=shared_amis_qry_svc_mock,
        default_original_ami_region=TEST_ORIGINAL_AMI_REGION,
    )
    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException):
        domain_service.verify_copy(
            region_value_object.RegionValueObject("eu-west-3"),
            ami_id_value_object.AmiIdValueObject("copy-12345"),
        )


def _marketplace_version(
    region: str,
    ownership: str,
    regional_ami_ids: dict | None = None,
    license_grant_allowed: bool = True,
):
    """A version imported from a Marketplace subscription, whose product publishes a
    different AMI id per region."""
    from app.publishing.domain.model.marketplace_metadata import MarketplaceMetadata

    entity = _version(region)
    entity.imageSource = "MARKETPLACE_PRODUCT"
    entity.marketplaceMetadata = MarketplaceMetadata(
        productCode="pc-1",
        subscriptionOwnership=ownership,
        licenseGrantAllowed=license_grant_allowed,
        regionalAmiIds=regional_ami_ids if regional_ami_ids is not None else {region: "ami-regional-euwest1"},
        licenseConfigurationArn="arn:aws:license-manager:us-east-1:111111111111:license:l-1",
        homeRegion="us-east-1",
    )
    return entity


@pytest.mark.parametrize(
    "ownership,expected_decision",
    [
        ("VEW_MANAGED", shared_amis_domain_query_service.ShareAmiDecision.LicenseGrant),
        ("EXTERNALLY_MANAGED", shared_amis_domain_query_service.ShareAmiDecision.VerifyExternalGrant),
    ],
)
def test_marketplace_decision_separates_the_registered_and_regional_ami(
    ownership,
    expected_decision,
    image_svc_mock,
    shared_amis_qry_svc_mock,
    mock_unit_of_work,
    mock_version_repo,
):
    """Two different AMI ids with two different jobs.

    original_ami_id must be the REGISTERED image, because that is what the publishing
    AMIs table is keyed by and what create_license_grant authorizes against - passing
    the regional id made that lookup miss and rejected every Marketplace grant.
    image_id must be the REGIONAL image, because that is the one the spoke launches
    and the one the launch-permission check asks about.
    """
    # ARRANGE
    mock_version_repo.get.return_value = _marketplace_version("eu-west-1", ownership)
    domain_service = shared_amis_domain_query_service.SharedAMIsDomainQueryService(
        unit_of_work=mock_unit_of_work,
        image_svc=image_svc_mock,
        shared_amis_qry_svc=shared_amis_qry_svc_mock,
        default_original_ami_region=TEST_ORIGINAL_AMI_REGION,
    )

    # ACT
    result = domain_service.make_share_ami_decision(
        product_id=product_id_value_object.from_str("prod-11111111"),
        version_id=version_id_value_object.from_str("vers-11111111"),
        aws_account_id=aws_account_id_value_object.from_str("123456789012"),
        product_type=product_type_value_object.from_str("WORKBENCH"),
    )

    # ASSERT
    assertpy.assert_that(result.decision).is_equal_to(expected_decision)
    assertpy.assert_that(result.original_ami_id).is_equal_to("ami-023c04780e65e723c")
    assertpy.assert_that(result.image_id).is_equal_to("ami-regional-euwest1")


def test_marketplace_decision_falls_back_to_the_registered_ami_for_an_unlisted_region(
    image_svc_mock,
    shared_amis_qry_svc_mock,
    mock_unit_of_work,
    mock_version_repo,
):
    """When the product lists no AMI for the spoke's region there is nothing regional to
    launch, so both ids are the registered image."""
    # ARRANGE
    mock_version_repo.get.return_value = _marketplace_version(
        "eu-west-1", "VEW_MANAGED", regional_ami_ids={"us-east-1": "ami-regional-useast1"}
    )
    domain_service = shared_amis_domain_query_service.SharedAMIsDomainQueryService(
        unit_of_work=mock_unit_of_work,
        image_svc=image_svc_mock,
        shared_amis_qry_svc=shared_amis_qry_svc_mock,
        default_original_ami_region=TEST_ORIGINAL_AMI_REGION,
    )

    # ACT
    result = domain_service.make_share_ami_decision(
        product_id=product_id_value_object.from_str("prod-11111111"),
        version_id=version_id_value_object.from_str("vers-11111111"),
        aws_account_id=aws_account_id_value_object.from_str("123456789012"),
        product_type=product_type_value_object.from_str("WORKBENCH"),
    )

    # ASSERT
    assertpy.assert_that(result.original_ami_id).is_equal_to("ami-023c04780e65e723c")
    assertpy.assert_that(result.image_id).is_equal_to("ami-023c04780e65e723c")


def _lm_service(has_grant: bool, can_distribute: bool):
    from app.publishing.domain.ports import license_manager_service

    svc = mock.create_autospec(spec=license_manager_service.LicenseManagerService)
    svc.has_active_received_grant.return_value = has_grant
    svc.can_distribute_license.return_value = can_distribute
    return svc


def _external_decision(lm_service, image_svc_mock, shared_amis_qry_svc_mock, mock_unit_of_work, mock_version_repo):
    mock_version_repo.get.return_value = _marketplace_version("eu-west-1", "EXTERNALLY_MANAGED")
    domain_service = shared_amis_domain_query_service.SharedAMIsDomainQueryService(
        unit_of_work=mock_unit_of_work,
        image_svc=image_svc_mock,
        shared_amis_qry_svc=shared_amis_qry_svc_mock,
        default_original_ami_region=TEST_ORIGINAL_AMI_REGION,
        license_manager_svc=lm_service,
    )
    return domain_service.make_share_ami_decision(
        product_id=product_id_value_object.from_str("prod-11111111"),
        version_id=version_id_value_object.from_str("vers-11111111"),
        aws_account_id=aws_account_id_value_object.from_str("123456789012"),
        product_type=product_type_value_object.from_str("WORKBENCH"),
    )


def test_external_subscription_is_upgraded_to_a_grant_when_the_hub_can_distribute(
    image_svc_mock, shared_amis_qry_svc_mock, mock_unit_of_work, mock_version_repo
):
    """The spoke has no grant and License Manager's organization integration is on, so
    the hub can distribute one itself. Without this the decision was always verify-only
    and the launch could never succeed."""
    # ARRANGE
    lm = _lm_service(has_grant=False, can_distribute=True)

    # ACT
    result = _external_decision(lm, image_svc_mock, shared_amis_qry_svc_mock, mock_unit_of_work, mock_version_repo)

    # ASSERT
    assertpy.assert_that(result.decision).is_equal_to(shared_amis_domain_query_service.ShareAmiDecision.LicenseGrant)


def test_external_subscription_stays_verify_only_when_the_spoke_already_has_a_grant(
    image_svc_mock, shared_amis_qry_svc_mock, mock_unit_of_work, mock_version_repo
):
    # ARRANGE
    lm = _lm_service(has_grant=True, can_distribute=True)

    # ACT
    result = _external_decision(lm, image_svc_mock, shared_amis_qry_svc_mock, mock_unit_of_work, mock_version_repo)

    # ASSERT — there is nothing to distribute, only to verify
    assertpy.assert_that(result.decision).is_equal_to(
        shared_amis_domain_query_service.ShareAmiDecision.VerifyExternalGrant
    )
    lm.can_distribute_license.assert_not_called()


def test_external_subscription_stays_verify_only_when_the_hub_cannot_distribute(
    image_svc_mock, shared_amis_qry_svc_mock, mock_unit_of_work, mock_version_repo
):
    # ARRANGE — integration off, so VEW holds nothing it may grant
    lm = _lm_service(has_grant=False, can_distribute=False)

    # ACT
    result = _external_decision(lm, image_svc_mock, shared_amis_qry_svc_mock, mock_unit_of_work, mock_version_repo)

    # ASSERT
    assertpy.assert_that(result.decision).is_equal_to(
        shared_amis_domain_query_service.ShareAmiDecision.VerifyExternalGrant
    )


def test_vew_managed_subscription_is_not_affected_by_the_upgrade(
    image_svc_mock, shared_amis_qry_svc_mock, mock_unit_of_work, mock_version_repo
):
    """A VEW-managed subscription is already a grant decision; the upgrade must not
    consult License Manager for it."""
    # ARRANGE
    lm = _lm_service(has_grant=False, can_distribute=True)
    mock_version_repo.get.return_value = _marketplace_version("eu-west-1", "VEW_MANAGED")
    domain_service = shared_amis_domain_query_service.SharedAMIsDomainQueryService(
        unit_of_work=mock_unit_of_work,
        image_svc=image_svc_mock,
        shared_amis_qry_svc=shared_amis_qry_svc_mock,
        default_original_ami_region=TEST_ORIGINAL_AMI_REGION,
        license_manager_svc=lm,
    )

    # ACT
    result = domain_service.make_share_ami_decision(
        product_id=product_id_value_object.from_str("prod-11111111"),
        version_id=version_id_value_object.from_str("vers-11111111"),
        aws_account_id=aws_account_id_value_object.from_str("123456789012"),
        product_type=product_type_value_object.from_str("WORKBENCH"),
    )

    # ASSERT
    assertpy.assert_that(result.decision).is_equal_to(shared_amis_domain_query_service.ShareAmiDecision.LicenseGrant)
    lm.has_active_received_grant.assert_not_called()


def test_external_subscription_without_create_grant_stays_verify_only_when_account_is_ready(
    image_svc_mock, shared_amis_qry_svc_mock, mock_unit_of_work, mock_version_repo
):
    """Account-level readiness cannot override this license's AllowedOperations."""
    # ARRANGE
    lm = _lm_service(has_grant=False, can_distribute=True)
    mock_version_repo.get.return_value = _marketplace_version(
        "eu-west-1", "EXTERNALLY_MANAGED", license_grant_allowed=False
    )
    domain_service = shared_amis_domain_query_service.SharedAMIsDomainQueryService(
        unit_of_work=mock_unit_of_work,
        image_svc=image_svc_mock,
        shared_amis_qry_svc=shared_amis_qry_svc_mock,
        default_original_ami_region=TEST_ORIGINAL_AMI_REGION,
        license_manager_svc=lm,
    )

    # ACT
    result = domain_service.make_share_ami_decision(
        product_id=product_id_value_object.from_str("prod-11111111"),
        version_id=version_id_value_object.from_str("vers-11111111"),
        aws_account_id=aws_account_id_value_object.from_str("123456789012"),
        product_type=product_type_value_object.from_str("WORKBENCH"),
    )

    # ASSERT
    assertpy.assert_that(result.decision).is_equal_to(
        shared_amis_domain_query_service.ShareAmiDecision.VerifyExternalGrant
    )
    lm.has_active_received_grant.assert_not_called()
    lm.can_distribute_license.assert_not_called()


def test_historical_marketplace_metadata_defaults_to_not_grant_capable():
    from app.publishing.domain.model.marketplace_metadata import MarketplaceMetadata

    metadata = MarketplaceMetadata.model_validate(
        {
            "productCode": "pc-1",
            "subscriptionOwnership": "EXTERNALLY_MANAGED",
        }
    )

    assertpy.assert_that(metadata.licenseGrantAllowed).is_false()
