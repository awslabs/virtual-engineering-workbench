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
    assertpy.assert_that(sub.licenseGrantAllowed).is_true()
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
    assertpy.assert_that(result[0].licenseGrantAllowed).is_true()


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
    assertpy.assert_that(result[0].licenseGrantAllowed).is_false()


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
    assertpy.assert_that(result[0].licenseGrantAllowed).is_true()


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
    mock_marketplace_ami_service.list_marketplace_amis_by_product_code.return_value = [get_test_marketplace_ami()]
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


def test_discover_should_detect_newer_version_available_when_latest_ami_differs_from_imported(
    get_test_marketplace_ami,
    get_test_received_license,
    get_test_existing_marketplace_image,
    mock_marketplace_agreement_service,
    mock_marketplace_ami_service,
    mock_marketplace_license_service,
    mock_org_integration_service,
    mock_image_query_service,
):
    # ARRANGE — imported AMI is ami-111, but EC2 now has a newer ami-222
    mock_marketplace_agreement_service.list_active_agreements.return_value = []
    mock_marketplace_license_service.list_received_licenses.return_value = [get_test_received_license()]
    mock_marketplace_ami_service.list_marketplace_amis_by_product_id.return_value = [get_test_marketplace_ami()]
    mock_marketplace_ami_service.get_regional_ami_ids.return_value = {}
    mock_marketplace_ami_service.list_marketplace_amis_by_product_code.return_value = [
        get_test_marketplace_ami(ami_id="ami-111", creation_date="2026-01-01T00:00:00.000Z"),
        get_test_marketplace_ami(ami_id="ami-222", creation_date="2026-05-01T00:00:00.000Z"),
    ]
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
    assertpy.assert_that(result[0].newerVersionAvailable).is_true()
    assertpy.assert_that(result[0].latestAmiId).is_equal_to("ami-222")
    assertpy.assert_that(result[0].latestAmiCreationDate).is_equal_to("2026-05-01T00:00:00.000Z")


def test_discover_should_not_flag_newer_version_when_latest_ami_is_already_imported(
    get_test_marketplace_ami,
    get_test_received_license,
    get_test_existing_marketplace_image,
    mock_marketplace_agreement_service,
    mock_marketplace_ami_service,
    mock_marketplace_license_service,
    mock_org_integration_service,
    mock_image_query_service,
):
    # ARRANGE — imported AMI is ami-111, EC2 latest is also ami-111
    mock_marketplace_agreement_service.list_active_agreements.return_value = []
    mock_marketplace_license_service.list_received_licenses.return_value = [get_test_received_license()]
    mock_marketplace_ami_service.list_marketplace_amis_by_product_id.return_value = [get_test_marketplace_ami()]
    mock_marketplace_ami_service.get_regional_ami_ids.return_value = {}
    mock_marketplace_ami_service.list_marketplace_amis_by_product_code.return_value = [
        get_test_marketplace_ami(ami_id="ami-111", creation_date="2026-01-01T00:00:00.000Z"),
    ]
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
    assertpy.assert_that(result[0].newerVersionAvailable).is_false()
    assertpy.assert_that(result[0].latestAmiId).is_none()


def test_discover_should_not_check_updates_for_non_imported_subscriptions(
    get_test_marketplace_ami,
    get_test_received_license,
    mock_marketplace_agreement_service,
    mock_marketplace_ami_service,
    mock_marketplace_license_service,
    mock_org_integration_service,
    mock_image_query_service,
):
    # ARRANGE — no images imported, so no update check needed
    mock_marketplace_agreement_service.list_active_agreements.return_value = []
    mock_marketplace_license_service.list_received_licenses.return_value = [get_test_received_license()]
    mock_marketplace_ami_service.list_marketplace_amis_by_product_id.return_value = [get_test_marketplace_ami()]
    mock_marketplace_ami_service.get_regional_ami_ids.return_value = {}
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
    assertpy.assert_that(result[0].newerVersionAvailable).is_false()
    # list_marketplace_amis_by_product_code should NOT be called when product is not imported
    mock_marketplace_ami_service.list_marketplace_amis_by_product_code.assert_not_called()


def test_hub_ami_lookup_prefers_a_supported_ami_over_a_newer_deprecated_one(
    get_test_marketplace_ami,
    mock_marketplace_agreement_service,
    mock_marketplace_ami_service,
    mock_marketplace_license_service,
    mock_org_integration_service,
    mock_image_query_service,
):
    """describe_images now returns deprecated images too, so picking amis[0] - or even
    the newest - could hand back a deprecated AMI while a supported one existed."""
    # ARRANGE
    service = _build_service(
        mock_marketplace_agreement_service,
        mock_marketplace_ami_service,
        mock_marketplace_license_service,
        mock_org_integration_service,
        mock_image_query_service,
    )
    mock_marketplace_ami_service.list_marketplace_amis_by_product_id.return_value = [
        get_test_marketplace_ami(
            ami_id="ami-deprecated-newer",
            creation_date="2026-06-01T00:00:00.000Z",
            deprecation_time="2020-07-01T00:00:00.000Z",
        ),
        get_test_marketplace_ami(ami_id="ami-supported-older", creation_date="2026-01-01T00:00:00.000Z"),
    ]

    # ACT
    result = service._lookup_hub_ami_by_product_id("prod-1", "us-east-1")

    # ASSERT
    assertpy.assert_that(result.amiId).is_equal_to("ami-supported-older")


def test_hub_ami_lookup_takes_the_newest_supported_ami(
    get_test_marketplace_ami,
    mock_marketplace_agreement_service,
    mock_marketplace_ami_service,
    mock_marketplace_license_service,
    mock_org_integration_service,
    mock_image_query_service,
):
    # ARRANGE
    service = _build_service(
        mock_marketplace_agreement_service,
        mock_marketplace_ami_service,
        mock_marketplace_license_service,
        mock_org_integration_service,
        mock_image_query_service,
    )
    mock_marketplace_ami_service.list_marketplace_amis_by_product_id.return_value = [
        get_test_marketplace_ami(ami_id="ami-old", creation_date="2026-01-01T00:00:00.000Z"),
        get_test_marketplace_ami(ami_id="ami-new", creation_date="2026-05-01T00:00:00.000Z"),
    ]

    # ACT
    result = service._lookup_hub_ami_by_product_id("prod-1", "us-east-1")

    # ASSERT
    assertpy.assert_that(result.amiId).is_equal_to("ami-new")


def test_hub_ami_lookup_falls_back_to_the_newest_deprecated_ami(
    get_test_marketplace_ami,
    mock_marketplace_agreement_service,
    mock_marketplace_ami_service,
    mock_marketplace_license_service,
    mock_org_integration_service,
    mock_image_query_service,
):
    """When every image is deprecated, an older subscription must still resolve to
    something rather than reporting no AMI."""
    # ARRANGE
    service = _build_service(
        mock_marketplace_agreement_service,
        mock_marketplace_ami_service,
        mock_marketplace_license_service,
        mock_org_integration_service,
        mock_image_query_service,
    )
    mock_marketplace_ami_service.list_marketplace_amis_by_product_id.return_value = [
        get_test_marketplace_ami(
            ami_id="ami-dep-old",
            creation_date="2026-01-01T00:00:00.000Z",
            deprecation_time="2020-02-01T00:00:00.000Z",
        ),
        get_test_marketplace_ami(
            ami_id="ami-dep-new",
            creation_date="2026-04-01T00:00:00.000Z",
            deprecation_time="2020-05-01T00:00:00.000Z",
        ),
    ]

    # ACT
    result = service._lookup_hub_ami_by_product_id("prod-1", "us-east-1")

    # ASSERT
    assertpy.assert_that(result.amiId).is_equal_to("ami-dep-new")
    assertpy.assert_that(result.deprecated).is_true()


def test_hub_ami_lookup_returns_none_without_any_ami(
    mock_marketplace_agreement_service,
    mock_marketplace_ami_service,
    mock_marketplace_license_service,
    mock_org_integration_service,
    mock_image_query_service,
):
    # ARRANGE
    service = _build_service(
        mock_marketplace_agreement_service,
        mock_marketplace_ami_service,
        mock_marketplace_license_service,
        mock_org_integration_service,
        mock_image_query_service,
    )
    mock_marketplace_ami_service.list_marketplace_amis_by_product_id.return_value = []

    # ACT / ASSERT
    assertpy.assert_that(service._lookup_hub_ami_by_product_id("prod-1", "us-east-1")).is_none()


def test_newer_version_detection_prefers_supported_amis_over_newer_deprecated_amis(
    get_test_marketplace_ami,
    mock_marketplace_agreement_service,
    mock_marketplace_ami_service,
    mock_marketplace_license_service,
    mock_org_integration_service,
    mock_image_query_service,
):
    # ARRANGE — the imported supported AMI remains the preferred version even
    # though a deprecated AMI has a later creation date.
    service = _build_service(
        mock_marketplace_agreement_service,
        mock_marketplace_ami_service,
        mock_marketplace_license_service,
        mock_org_integration_service,
        mock_image_query_service,
    )
    mock_marketplace_ami_service.list_marketplace_amis_by_product_code.return_value = [
        get_test_marketplace_ami(ami_id="ami-supported", creation_date="2026-01-01T00:00:00.000Z"),
        get_test_marketplace_ami(
            ami_id="ami-deprecated",
            creation_date="2026-05-01T00:00:00.000Z",
            deprecation_time="2020-06-01T00:00:00.000Z",
        ),
    ]

    # ACT
    result = service._check_for_newer_version(
        "pc-1",
        "us-east-1",
        imported_product_codes={"pc-1"},
        imported_ami_ids={"ami-supported"},
    )

    # ASSERT
    assertpy.assert_that(result).is_equal_to((False, None, None))


def test_newer_version_detection_falls_back_to_deprecated_when_all_amis_are_deprecated(
    get_test_marketplace_ami,
    mock_marketplace_agreement_service,
    mock_marketplace_ami_service,
    mock_marketplace_license_service,
    mock_org_integration_service,
    mock_image_query_service,
):
    # ARRANGE
    service = _build_service(
        mock_marketplace_agreement_service,
        mock_marketplace_ami_service,
        mock_marketplace_license_service,
        mock_org_integration_service,
        mock_image_query_service,
    )
    mock_marketplace_ami_service.list_marketplace_amis_by_product_code.return_value = [
        get_test_marketplace_ami(
            ami_id="ami-deprecated-old",
            creation_date="2026-01-01T00:00:00.000Z",
            deprecation_time="2020-02-01T00:00:00.000Z",
        ),
        get_test_marketplace_ami(
            ami_id="ami-deprecated-new",
            creation_date="2026-05-01T00:00:00.000Z",
            deprecation_time="2020-06-01T00:00:00.000Z",
        ),
    ]

    # ACT
    result = service._check_for_newer_version(
        "pc-1",
        "us-east-1",
        imported_product_codes={"pc-1"},
        imported_ami_ids={"ami-deprecated-old"},
    )

    # ASSERT
    assertpy.assert_that(result).is_equal_to((True, "ami-deprecated-new", "2026-05-01T00:00:00.000Z"))
