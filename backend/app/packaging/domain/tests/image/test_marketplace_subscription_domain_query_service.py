import logging

import assertpy

from app.packaging.domain.model.image.image_constants import SubscriptionOwnership
from app.packaging.domain.query_services.marketplace_subscription_domain_query_service import (
    MarketplaceSubscriptionDomainQueryService,
)
from app.packaging.domain.value_objects.shared import project_id_value_object


def _build_service(agreement_svc, ami_svc, license_svc, org_integration_svc, image_qry_svc):
    return MarketplaceSubscriptionDomainQueryService(
        agreement_service=agreement_svc,
        ami_service=ami_svc,
        license_service=license_svc,
        org_integration_service=org_integration_svc,
        image_qry_svc=image_qry_svc,
        available_regions=["us-east-1"],
        logger=logging.getLogger(__name__),
    )


def test_discover_should_return_vew_managed_when_agreement_license_and_org_integration_active(
    get_test_marketplace_ami,
    get_test_marketplace_agreement,
    get_test_received_license,
    mock_marketplace_agreement_service,
    mock_marketplace_ami_service,
    mock_marketplace_license_service,
    mock_org_integration_service,
    mock_image_query_service,
):
    # ARRANGE — hub AMI resolves to product_code "pc-1" for both agreement and license lookups
    mock_marketplace_agreement_service.list_active_agreements.return_value = [get_test_marketplace_agreement()]
    mock_marketplace_license_service.list_received_licenses.return_value = [
        get_test_received_license(allowed_operations=["CreateGrant"])
    ]
    mock_marketplace_ami_service.list_marketplace_amis_by_product_id.return_value = [get_test_marketplace_ami()]
    mock_marketplace_ami_service.get_regional_ami_ids.return_value = {}
    mock_org_integration_service.is_license_manager_org_integration_active.return_value = True
    mock_image_query_service.get_images.return_value = []

    svc = _build_service(
        mock_marketplace_agreement_service,
        mock_marketplace_ami_service,
        mock_marketplace_license_service,
        mock_org_integration_service,
        mock_image_query_service,
    )

    # ACT
    result = svc.discover(project_id=project_id_value_object.from_str("proj-1"))

    # ASSERT
    assertpy.assert_that(result).is_length(1)
    sub = result[0]
    assertpy.assert_that(sub.subscriptionOwnership).is_equal_to(SubscriptionOwnership.VEW_MANAGED.value)
    assertpy.assert_that(sub.licenseConfigurationArn).is_equal_to("arn:aws:license-manager::123:license/lic-1")
    assertpy.assert_that(sub.alreadyImported).is_false()


def test_discover_should_return_externally_managed_when_license_without_agreement(
    get_test_marketplace_ami,
    get_test_received_license,
    mock_marketplace_agreement_service,
    mock_marketplace_ami_service,
    mock_marketplace_license_service,
    mock_org_integration_service,
    mock_image_query_service,
):
    # ARRANGE
    mock_marketplace_agreement_service.list_active_agreements.return_value = []
    mock_marketplace_license_service.list_received_licenses.return_value = [
        get_test_received_license(allowed_operations=["CreateGrant"])
    ]
    mock_marketplace_ami_service.list_marketplace_amis_by_product_id.return_value = [get_test_marketplace_ami()]
    mock_marketplace_ami_service.get_regional_ami_ids.return_value = {}
    mock_org_integration_service.is_license_manager_org_integration_active.return_value = True
    mock_image_query_service.get_images.return_value = []

    svc = _build_service(
        mock_marketplace_agreement_service,
        mock_marketplace_ami_service,
        mock_marketplace_license_service,
        mock_org_integration_service,
        mock_image_query_service,
    )

    # ACT
    result = svc.discover(project_id=project_id_value_object.from_str("proj-1"))

    # ASSERT
    assertpy.assert_that(result).is_length(1)
    assertpy.assert_that(result[0].subscriptionOwnership).is_equal_to(SubscriptionOwnership.EXTERNALLY_MANAGED.value)


def test_discover_should_return_externally_managed_when_license_lacks_create_grant(
    get_test_marketplace_ami,
    get_test_marketplace_agreement,
    get_test_received_license,
    mock_marketplace_agreement_service,
    mock_marketplace_ami_service,
    mock_marketplace_license_service,
    mock_org_integration_service,
    mock_image_query_service,
):
    # ARRANGE — agreement + org integration active, but license lacks CreateGrant
    mock_marketplace_agreement_service.list_active_agreements.return_value = [get_test_marketplace_agreement()]
    mock_marketplace_license_service.list_received_licenses.return_value = [
        get_test_received_license(allowed_operations=["CheckoutLicense"])
    ]
    mock_marketplace_ami_service.list_marketplace_amis_by_product_id.return_value = [get_test_marketplace_ami()]
    mock_marketplace_ami_service.get_regional_ami_ids.return_value = {}
    mock_org_integration_service.is_license_manager_org_integration_active.return_value = True
    mock_image_query_service.get_images.return_value = []

    svc = _build_service(
        mock_marketplace_agreement_service,
        mock_marketplace_ami_service,
        mock_marketplace_license_service,
        mock_org_integration_service,
        mock_image_query_service,
    )

    # ACT
    result = svc.discover(project_id=project_id_value_object.from_str("proj-1"))

    # ASSERT
    assertpy.assert_that(result).is_length(1)
    assertpy.assert_that(result[0].subscriptionOwnership).is_equal_to(SubscriptionOwnership.EXTERNALLY_MANAGED.value)


def test_discover_should_return_externally_managed_when_org_integration_inactive(
    get_test_marketplace_ami,
    get_test_marketplace_agreement,
    get_test_received_license,
    mock_marketplace_agreement_service,
    mock_marketplace_ami_service,
    mock_marketplace_license_service,
    mock_org_integration_service,
    mock_image_query_service,
):
    # ARRANGE — agreement + CreateGrant permitted, but org integration off
    mock_marketplace_agreement_service.list_active_agreements.return_value = [get_test_marketplace_agreement()]
    mock_marketplace_license_service.list_received_licenses.return_value = [
        get_test_received_license(allowed_operations=["CreateGrant"])
    ]
    mock_marketplace_ami_service.list_marketplace_amis_by_product_id.return_value = [get_test_marketplace_ami()]
    mock_marketplace_ami_service.get_regional_ami_ids.return_value = {}
    mock_org_integration_service.is_license_manager_org_integration_active.return_value = False
    mock_image_query_service.get_images.return_value = []

    svc = _build_service(
        mock_marketplace_agreement_service,
        mock_marketplace_ami_service,
        mock_marketplace_license_service,
        mock_org_integration_service,
        mock_image_query_service,
    )

    # ACT
    result = svc.discover(project_id=project_id_value_object.from_str("proj-1"))

    # ASSERT
    assertpy.assert_that(result).is_length(1)
    assertpy.assert_that(result[0].subscriptionOwnership).is_equal_to(SubscriptionOwnership.EXTERNALLY_MANAGED.value)


def test_discover_should_mark_already_imported_when_ami_exists_in_project(
    get_test_marketplace_ami,
    get_test_received_license,
    get_test_existing_marketplace_image,
    mock_marketplace_agreement_service,
    mock_marketplace_ami_service,
    mock_marketplace_license_service,
    mock_org_integration_service,
    mock_image_query_service,
):
    # ARRANGE
    mock_marketplace_agreement_service.list_active_agreements.return_value = []
    mock_marketplace_license_service.list_received_licenses.return_value = [get_test_received_license()]
    mock_marketplace_ami_service.list_marketplace_amis_by_product_id.return_value = [get_test_marketplace_ami()]
    mock_marketplace_ami_service.get_regional_ami_ids.return_value = {}
    mock_image_query_service.get_images.return_value = [get_test_existing_marketplace_image(ami_id="ami-111")]

    svc = _build_service(
        mock_marketplace_agreement_service,
        mock_marketplace_ami_service,
        mock_marketplace_license_service,
        mock_org_integration_service,
        mock_image_query_service,
    )

    # ACT
    result = svc.discover(project_id=project_id_value_object.from_str("proj-1"))

    # ASSERT
    assertpy.assert_that(result).is_length(1)
    assertpy.assert_that(result[0].alreadyImported).is_true()


def test_discover_should_return_empty_list_when_no_agreements_and_no_licenses(
    mock_marketplace_agreement_service,
    mock_marketplace_ami_service,
    mock_marketplace_license_service,
    mock_org_integration_service,
    mock_image_query_service,
):
    # ARRANGE
    mock_marketplace_agreement_service.list_active_agreements.return_value = []
    mock_marketplace_license_service.list_received_licenses.return_value = []

    svc = _build_service(
        mock_marketplace_agreement_service,
        mock_marketplace_ami_service,
        mock_marketplace_license_service,
        mock_org_integration_service,
        mock_image_query_service,
    )

    # ACT
    result = svc.discover(project_id=project_id_value_object.from_str("proj-1"))

    # ASSERT
    assertpy.assert_that(result).is_empty()
    mock_marketplace_ami_service.list_marketplace_amis_by_product_id.assert_not_called()


def test_discover_should_skip_product_when_no_hub_ami_found(
    get_test_received_license,
    mock_marketplace_agreement_service,
    mock_marketplace_ami_service,
    mock_marketplace_license_service,
    mock_org_integration_service,
    mock_image_query_service,
):
    # ARRANGE — license exists but no AMI for this product (e.g. SaaS-only or deregistered)
    mock_marketplace_agreement_service.list_active_agreements.return_value = []
    mock_marketplace_license_service.list_received_licenses.return_value = [get_test_received_license()]
    mock_marketplace_ami_service.list_marketplace_amis_by_product_id.return_value = []
    mock_image_query_service.get_images.return_value = []

    svc = _build_service(
        mock_marketplace_agreement_service,
        mock_marketplace_ami_service,
        mock_marketplace_license_service,
        mock_org_integration_service,
        mock_image_query_service,
    )

    # ACT
    result = svc.discover(project_id=project_id_value_object.from_str("proj-1"))

    # ASSERT
    assertpy.assert_that(result).is_empty()
