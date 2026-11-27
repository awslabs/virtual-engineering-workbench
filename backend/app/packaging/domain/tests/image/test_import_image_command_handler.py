import assertpy
import pytest

from app.packaging.domain.command_handlers.image import import_image_command_handler
from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.value_objects.image import product_code_value_object


def _call_handle(
    cmd, uow_mock, ami_validation_service_mock, image_query_service_mock, message_bus_mock, aws_published_qry_svc=None
):
    return import_image_command_handler.handle(
        command=cmd,
        uow=uow_mock,
        ami_validation_svc=ami_validation_service_mock,
        image_qry_srv=image_query_service_mock,
        msg_bus=message_bus_mock,
        aws_published_qry_svc=aws_published_qry_svc,
    )


def _resolution_offering(ami_id: str, listing_id: str = "listing-1"):
    """A listing resolution that offers ``ami_id`` and nothing else."""
    from unittest import mock

    from app.packaging.domain.query_services.aws_published_ami_domain_query_service import (
        AwsPublishedAmiDomainQueryService,
        AwsPublishedAmiResolutionResult,
    )
    from app.packaging.domain.read_models.aws_published_ami import AwsPublishedAmiCandidate

    svc = mock.create_autospec(spec=AwsPublishedAmiDomainQueryService, instance=True)
    svc.resolve_listing.return_value = AwsPublishedAmiResolutionResult(
        listingId=listing_id,
        productId="prod-1",
        productName="Red Hat Enterprise Linux 9",
        region="us-east-1",
        unambiguous=True,
        resolved=AwsPublishedAmiCandidate(
            amiId=ami_id, amiName="RHEL-9.6.0_HVM", ownerId="309956199498", region="us-east-1"
        ),
    )
    return svc


def test_handle_should_import_image_when_existing_ami_valid(
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_ami_description,
    get_test_import_image_command,
):
    # ARRANGE
    ami_validation_service_mock.describe_image.return_value = get_test_ami_description()
    image_query_service_mock.get_images_by_image_upstream_id.return_value = []
    cmd = get_test_import_image_command()

    # ACT
    result = _call_handle(cmd, uow_mock, ami_validation_service_mock, image_query_service_mock, message_bus_mock)

    # ASSERT
    assertpy.assert_that(result).starts_with("image-")
    uow_mock.get_repository.return_value.add.assert_called_once()
    message_bus_mock.publish.assert_called_once()


def test_handle_should_raise_when_ami_not_available(
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_ami_description,
    get_test_import_image_command,
):
    # ARRANGE
    ami_validation_service_mock.describe_image.return_value = get_test_ami_description(state="pending")
    image_query_service_mock.get_images_by_image_upstream_id.return_value = []
    cmd = get_test_import_image_command()

    # ACT
    with pytest.raises(DomainException, match="not available"):
        _call_handle(cmd, uow_mock, ami_validation_service_mock, image_query_service_mock, message_bus_mock)


def test_handle_should_raise_when_ami_wrong_owner(
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_ami_description,
    get_test_import_image_command,
):
    # ARRANGE
    ami_validation_service_mock.describe_image.return_value = get_test_ami_description(owner_id="999999999999")
    image_query_service_mock.get_images_by_image_upstream_id.return_value = []
    cmd = get_test_import_image_command(imageServiceAccountId="123456789012")

    # ACT
    with pytest.raises(DomainException, match="not owned by the Image Service account"):
        _call_handle(cmd, uow_mock, ami_validation_service_mock, image_query_service_mock, message_bus_mock)


def test_handle_should_raise_when_marketplace_product_code_mismatch(
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_ami_description,
    get_test_import_image_command,
):
    # ARRANGE
    ami_validation_service_mock.describe_marketplace_image.return_value = get_test_ami_description()
    ami_validation_service_mock.validate_marketplace_product_code.return_value = False
    image_query_service_mock.get_images_by_image_upstream_id.return_value = []
    cmd = get_test_import_image_command(
        image_source="MARKETPLACE_PRODUCT",
        marketplaceProductCode=product_code_value_object.from_str("abc123def456ghi"),
        subscriptionOwnership="VEW_MANAGED",
        regionalAmiIds={"eu-west-1": "ami-12345678"},
    )

    # ACT
    with pytest.raises(DomainException, match="Product code mismatch"):
        _call_handle(cmd, uow_mock, ami_validation_service_mock, image_query_service_mock, message_bus_mock)


def test_handle_should_raise_when_missing_component_version_details(
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_import_image_command,
):
    # ARRANGE
    cmd = get_test_import_image_command(componentVersionDetails=[])

    # ACT
    with pytest.raises(DomainException, match="component version detail"):
        _call_handle(cmd, uow_mock, ami_validation_service_mock, image_query_service_mock, message_bus_mock)


def test_handle_should_import_image_when_marketplace_ami_valid(
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_ami_description,
    get_test_import_image_command,
):
    # ARRANGE
    ami_validation_service_mock.describe_marketplace_image.return_value = get_test_ami_description()
    ami_validation_service_mock.validate_marketplace_product_code.return_value = True
    image_query_service_mock.get_images_by_image_upstream_id.return_value = []
    cmd = get_test_import_image_command(
        image_source="MARKETPLACE_PRODUCT",
        marketplaceProductCode=product_code_value_object.from_str("abc123def456ghi"),
        subscriptionOwnership="VEW_MANAGED",
        licenseGrantAllowed=True,
        regionalAmiIds={"eu-west-1": "ami-12345678"},
    )

    # ACT
    result = _call_handle(cmd, uow_mock, ami_validation_service_mock, image_query_service_mock, message_bus_mock)

    # ASSERT
    assertpy.assert_that(result).starts_with("image-")
    saved_entity = uow_mock.get_repository.return_value.add.call_args.args[0]
    assertpy.assert_that(saved_entity.marketplaceMetadata["licenseGrantAllowed"]).is_true()
    event = message_bus_mock.publish.call_args.args[0]
    assertpy.assert_that(event.marketplaceMetadata["licenseGrantAllowed"]).is_true()
    message_bus_mock.publish.assert_called_once()


def test_handle_should_map_ec2_architecture_to_vew_convention(
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_ami_description,
    get_test_import_image_command,
):
    # ARRANGE
    ami_validation_service_mock.describe_image.return_value = get_test_ami_description(architecture="x86_64")
    image_query_service_mock.get_images_by_image_upstream_id.return_value = []
    cmd = get_test_import_image_command()

    # ACT
    _call_handle(cmd, uow_mock, ami_validation_service_mock, image_query_service_mock, message_bus_mock)

    # ASSERT
    saved_entity = uow_mock.get_repository.return_value.add.call_args[0][0]
    assertpy.assert_that(saved_entity.architecture).is_equal_to("amd64")


def test_handle_should_raise_when_unsupported_architecture(
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_ami_description,
    get_test_import_image_command,
):
    # ARRANGE
    ami_validation_service_mock.describe_image.return_value = get_test_ami_description(architecture="mips64")
    image_query_service_mock.get_images_by_image_upstream_id.return_value = []
    cmd = get_test_import_image_command()

    # ACT
    with pytest.raises(DomainException, match="Unsupported architecture"):
        _call_handle(cmd, uow_mock, ami_validation_service_mock, image_query_service_mock, message_bus_mock)


def _existing_import(project_id: str, status: str):
    from app.packaging.domain.model.image import image

    return image.Image.model_construct(
        projectId=project_id, imageId="image-existing", status=image.ImageStatus(status), imageUpstreamId="ami-12345678"
    )


def test_handle_should_raise_when_ami_already_imported_in_this_project(
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_import_image_command,
):
    image_query_service_mock.get_images_by_image_upstream_id.return_value = [_existing_import("proj-123", "CREATED")]

    with pytest.raises(DomainException, match="already imported in this project"):
        _call_handle(
            get_test_import_image_command(),
            uow_mock,
            ami_validation_service_mock,
            image_query_service_mock,
            message_bus_mock,
        )
    uow_mock.get_repository.return_value.add.assert_not_called()


@pytest.mark.parametrize("status", ["CREATED", "CREATING", "RETIRED"])
def test_handle_should_raise_when_ami_held_by_another_project(
    status,
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_import_image_command,
):
    # Publishing keys its AMI read model by AMI id alone; a second project's import
    # would take the row over and break the first project's licence grants.
    image_query_service_mock.get_images_by_image_upstream_id.return_value = [_existing_import("proj-other", status)]

    with pytest.raises(DomainException, match="already imported in another project") as exc_info:
        _call_handle(
            get_test_import_image_command(image_source="MARKETPLACE_PRODUCT"),
            uow_mock,
            ami_validation_service_mock,
            image_query_service_mock,
            message_bus_mock,
        )
    assertpy.assert_that(str(exc_info.value)).does_not_contain("proj-other")
    uow_mock.get_repository.return_value.add.assert_not_called()
    message_bus_mock.publish.assert_not_called()


def test_handle_should_raise_when_any_other_project_still_holds_the_ami(
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_import_image_command,
):
    # The first match is a released import; a later one still holds the AMI.
    image_query_service_mock.get_images_by_image_upstream_id.return_value = [
        _existing_import("proj-a", "DELETED"),
        _existing_import("proj-b", "CREATED"),
    ]

    with pytest.raises(DomainException, match="already imported in another project"):
        _call_handle(
            get_test_import_image_command(),
            uow_mock,
            ami_validation_service_mock,
            image_query_service_mock,
            message_bus_mock,
        )


@pytest.mark.parametrize("status", ["DELETED", "FAILED"])
def test_handle_should_import_when_another_project_released_the_ami(
    status,
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_ami_description,
    get_test_import_image_command,
):
    ami_validation_service_mock.describe_image.return_value = get_test_ami_description()
    image_query_service_mock.get_images_by_image_upstream_id.return_value = [_existing_import("proj-other", status)]

    result = _call_handle(
        get_test_import_image_command(),
        uow_mock,
        ami_validation_service_mock,
        image_query_service_mock,
        message_bus_mock,
    )

    assertpy.assert_that(result).starts_with("image-")
    image_query_service_mock.get_images_by_image_upstream_id.assert_called_once_with("ami-12345678")


def test_handle_should_import_aws_published_ami_from_a_known_vendor(
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_ami_description,
    get_test_import_image_command,
):
    # Red Hat owns the image; no product code, no Image Service ownership.
    ami_validation_service_mock.describe_marketplace_image.return_value = get_test_ami_description(
        owner_id="309956199498"
    )
    image_query_service_mock.get_images_by_image_upstream_id.return_value = []
    cmd = get_test_import_image_command(image_source="AWS_PUBLISHED_AMI", marketplaceListingId="listing-1")
    resolver = _resolution_offering("ami-12345678")

    result = _call_handle(
        cmd, uow_mock, ami_validation_service_mock, image_query_service_mock, message_bus_mock, resolver
    )

    assertpy.assert_that(result).starts_with("image-")
    ami_validation_service_mock.validate_marketplace_product_code.assert_not_called()
    added = uow_mock.get_repository.return_value.add.call_args.args[0]
    assertpy.assert_that(added.marketplaceMetadata["subscriptionOwnership"]).is_equal_to("AWS_MANAGED")
    assertpy.assert_that(added.marketplaceMetadata["productCode"]).is_none()


def test_handle_should_refuse_aws_published_import_of_an_arbitrary_public_ami(
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_ami_description,
    get_test_import_image_command,
):
    """AWS_PUBLISHED_AMI has no Image Service ownership to check, so the
    vendor allowlist is the last guard behind the listing resolution."""
    ami_validation_service_mock.describe_marketplace_image.return_value = get_test_ami_description(
        owner_id="111122223333"
    )
    image_query_service_mock.get_images_by_image_upstream_id.return_value = []
    cmd = get_test_import_image_command(image_source="AWS_PUBLISHED_AMI", marketplaceListingId="listing-1")
    resolver = _resolution_offering("ami-12345678")

    with pytest.raises(DomainException, match="recognised AWS Marketplace vendor"):
        _call_handle(cmd, uow_mock, ami_validation_service_mock, image_query_service_mock, message_bus_mock, resolver)
    uow_mock.get_repository.return_value.add.assert_not_called()


def test_handle_should_refuse_an_ami_the_listing_does_not_offer(
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_ami_description,
    get_test_import_image_command,
):
    """The AMI id comes from the caller, so it is only trusted when the
    server's own resolution of the listing offers it. Otherwise any
    product-coded AMI, including another seller's, would be importable."""
    # ARRANGE
    ami_validation_service_mock.describe_marketplace_image.return_value = get_test_ami_description(
        owner_id="309956199498"
    )
    image_query_service_mock.get_images_by_image_upstream_id.return_value = []
    cmd = get_test_import_image_command(image_source="AWS_PUBLISHED_AMI", marketplaceListingId="listing-1")
    resolver = _resolution_offering("ami-87654321")

    # ACT / ASSERT
    with pytest.raises(DomainException, match="not offered by Marketplace listing"):
        _call_handle(cmd, uow_mock, ami_validation_service_mock, image_query_service_mock, message_bus_mock, resolver)
    uow_mock.get_repository.return_value.add.assert_not_called()
    ami_validation_service_mock.describe_marketplace_image.assert_not_called()


def test_handle_should_require_a_listing_for_an_aws_published_import(
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_import_image_command,
):
    # ARRANGE
    cmd = get_test_import_image_command(image_source="AWS_PUBLISHED_AMI")

    # ACT / ASSERT
    with pytest.raises(DomainException, match="listingId is required"):
        _call_handle(
            cmd,
            uow_mock,
            ami_validation_service_mock,
            image_query_service_mock,
            message_bus_mock,
            _resolution_offering("ami-12345678"),
        )
    uow_mock.get_repository.return_value.add.assert_not_called()


def test_handle_should_ignore_caller_supplied_regional_ami_ids(
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_ami_description,
    get_test_import_image_command,
):
    """Those ids reach the published product template, and nothing has
    checked them, so only the resolved AMI's own region is recorded."""
    # ARRANGE
    ami_validation_service_mock.describe_marketplace_image.return_value = get_test_ami_description(
        owner_id="309956199498"
    )
    image_query_service_mock.get_images_by_image_upstream_id.return_value = []
    cmd = get_test_import_image_command(
        image_source="AWS_PUBLISHED_AMI",
        marketplaceListingId="listing-1",
        regionalAmiIds={"ap-south-1": "ami-deadbeef"},
    )

    # ACT
    _call_handle(
        cmd,
        uow_mock,
        ami_validation_service_mock,
        image_query_service_mock,
        message_bus_mock,
        _resolution_offering("ami-12345678"),
    )

    # ASSERT
    added = uow_mock.get_repository.return_value.add.call_args.args[0]
    regional = added.marketplaceMetadata["regionalAmiIds"]
    assertpy.assert_that(list(regional.values())).is_equal_to(["ami-12345678"])
    assertpy.assert_that(regional).does_not_contain_key("ap-south-1")


def test_handle_should_refuse_an_aws_published_ami_held_by_another_project(
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_import_image_command,
):
    """The one-project-per-AMI rule also covers AMIs that AWS publishes, and it
    runs before the listing is resolved, so no AWS call is made."""
    image_query_service_mock.get_images_by_image_upstream_id.return_value = [_existing_import("proj-other", "CREATED")]
    resolver = _resolution_offering("ami-12345678")
    cmd = get_test_import_image_command(image_source="AWS_PUBLISHED_AMI", marketplaceListingId="listing-1")

    with pytest.raises(DomainException, match="already imported in another project"):
        _call_handle(cmd, uow_mock, ami_validation_service_mock, image_query_service_mock, message_bus_mock, resolver)
    resolver.resolve_listing.assert_not_called()
    uow_mock.get_repository.return_value.add.assert_not_called()


def test_handle_should_record_the_agreement_of_a_product_coded_aws_published_ami(
    ami_validation_service_mock,
    uow_mock,
    message_bus_mock,
    image_query_service_mock,
    get_test_ami_description,
    get_test_import_image_command,
):
    """An agreement names its Marketplace product, not the EC2 product code, so the
    lookup must match the product id of the resolved listing."""
    from unittest import mock

    from app.packaging.domain.read_models.ami_description import ProductCode
    from app.packaging.domain.read_models.marketplace_agreement import MarketplaceAgreement

    ami_validation_service_mock.describe_marketplace_image.return_value = get_test_ami_description(
        owner_id="309956199498", product_codes=[ProductCode(ProductCodeId="pc-rhel", ProductCodeType="marketplace")]
    )
    image_query_service_mock.get_images_by_image_upstream_id.return_value = []
    agreement_svc = mock.MagicMock()
    agreement_svc.list_active_agreements.return_value = [
        MarketplaceAgreement(agreementId="agmt-other", productId="prod-other", offerId="pc-rhel", status="ACTIVE"),
        MarketplaceAgreement(agreementId="agmt-rhel", productId="prod-1", offerId="offer-rhel", status="ACTIVE"),
    ]
    cmd = get_test_import_image_command(image_source="AWS_PUBLISHED_AMI", marketplaceListingId="listing-1")

    import_image_command_handler.handle(
        command=cmd,
        uow=uow_mock,
        ami_validation_svc=ami_validation_service_mock,
        image_qry_srv=image_query_service_mock,
        msg_bus=message_bus_mock,
        agreement_svc=agreement_svc,
        aws_published_qry_svc=_resolution_offering("ami-12345678"),
    )

    added = uow_mock.get_repository.return_value.add.call_args.args[0]
    assertpy.assert_that(added.marketplaceMetadata["productCode"]).is_equal_to("pc-rhel")
    assertpy.assert_that(added.marketplaceMetadata["agreementId"]).is_equal_to("agmt-rhel")
