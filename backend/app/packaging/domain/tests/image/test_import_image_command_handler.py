import assertpy
import pytest

from app.packaging.domain.command_handlers.image import import_image_command_handler
from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.value_objects.image import product_code_value_object


def _call_handle(cmd, uow_mock, ami_validation_service_mock, image_query_service_mock, message_bus_mock):
    return import_image_command_handler.handle(
        command=cmd,
        uow=uow_mock,
        ami_validation_svc=ami_validation_service_mock,
        image_qry_srv=image_query_service_mock,
        msg_bus=message_bus_mock,
    )


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
