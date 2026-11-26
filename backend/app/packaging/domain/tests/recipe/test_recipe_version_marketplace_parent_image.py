"""Recipe versions that build on a subscribed AWS Marketplace AMI instead of the platform default."""

from unittest import mock

import assertpy
import pytest

from app.packaging.domain.command_handlers.recipe import (
    create_recipe_version_command_handler,
    update_recipe_version_command_handler,
)
from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.ports.marketplace_base_image_query_service import MarketplaceBaseImageQueryService
from app.packaging.domain.read_models.marketplace_base_image import MarketplaceBaseImage
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_parent_image_id_value_object,
    recipe_version_parent_image_product_id_value_object,
    recipe_version_volume_size_value_object,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work

PRODUCT_ID = "prod-ib2w5aw4ynhey"
MARKETPLACE_AMI_ID = "ami-0fedcba9876543210"
LICENSE_ARN = "arn:aws:license-manager::111111111111:license:l-0123456789abcdef0123456789abcdef"


def _base_image(**overrides) -> MarketplaceBaseImage:
    values = dict(
        productId=PRODUCT_ID,
        productName="Ubuntu 24.04 LTS",
        productCode="abc123def456ghi789jkl0mno",
        amiId=MARKETPLACE_AMI_ID,
        platform="Linux",
        architecture="amd64",
        rootVolumeSize=8,
        licenseConfigurationArn=LICENSE_ARN,
        homeRegion="us-east-1",
        subscriptionOwnership="VEW_MANAGED",
    )
    values.update(overrides)
    return MarketplaceBaseImage(**values)


EXPECTED_METADATA = {
    "marketplaceProductId": PRODUCT_ID,
    "productCode": "abc123def456ghi789jkl0mno",
    "licenseConfigurationArn": LICENSE_ARN,
    "homeRegion": "us-east-1",
    "subscriptionOwnership": "VEW_MANAGED",
    "licenseGrantAllowed": False,
    "rootVolumeSize": 8,
}


@pytest.fixture
def base_image_qry_srv_mock():
    srv = mock.create_autospec(spec=MarketplaceBaseImageQueryService, instance=True)
    srv.get_base_image.return_value = _base_image()
    return srv


@pytest.fixture
def released_components(component_version_query_service_mock, get_test_component_version_with_specific_status):
    def _setup(command):
        entities = []
        for entry in command.recipeComponentsVersions.value:
            entity = get_test_component_version_with_specific_status(
                status=component_version.ComponentVersionStatus.Released
            )
            entity.componentId = entry.componentId
            entity.componentVersionId = entry.componentVersionId
            entities.append(entity)
        component_version_query_service_mock.get_component_version.side_effect = entities

    return _setup


@pytest.fixture
def repo_and_uow():
    repo = mock.create_autospec(spec=unit_of_work.GenericRepository)
    uow = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow.get_repository.side_effect = lambda pk, entity: repo
    return repo, uow


def _create(command, uow, base_image_qry_srv, deps):
    return create_recipe_version_command_handler.handle(
        command=command,
        uow=uow,
        message_bus=mock.create_autospec(spec=message_bus.MessageBus),
        component_version_qry_srv=deps["component_version_query_service_mock"],
        recipe_version_qry_srv=deps["recipe_version_query_service_mock"],
        recipe_qry_srv=deps["recipe_query_service_mock"],
        parameter_srv=deps["parameter_service_mock"],
        mandatory_components_list_qry_srv=deps["mandatory_components_list_query_service_mock"],
        system_configuration_mapping=deps["mock_system_configuration_mapping"],
        component_qry_srv=deps["component_query_service_mock"],
        marketplace_base_image_qry_srv=base_image_qry_srv,
    )


@pytest.fixture
def deps(
    component_version_query_service_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
    parameter_service_mock,
    mandatory_components_list_query_service_mock,
    mock_system_configuration_mapping,
    component_query_service_mock,
    mock_recipe_object,
):
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = None
    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = None
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    return dict(
        component_version_query_service_mock=component_version_query_service_mock,
        recipe_version_query_service_mock=recipe_version_query_service_mock,
        recipe_query_service_mock=recipe_query_service_mock,
        parameter_service_mock=parameter_service_mock,
        mandatory_components_list_query_service_mock=mandatory_components_list_query_service_mock,
        mock_system_configuration_mapping=mock_system_configuration_mapping,
        component_query_service_mock=component_query_service_mock,
    )


def test_create_should_build_on_the_marketplace_ami_and_keep_its_license(
    create_recipe_version_command_mock, base_image_qry_srv_mock, released_components, repo_and_uow, deps
):
    # ARRANGE
    repo, uow = repo_and_uow
    create_recipe_version_command_mock.parentImageProductId = (
        recipe_version_parent_image_product_id_value_object.from_str(PRODUCT_ID)
    )
    released_components(create_recipe_version_command_mock)

    # ACT
    _create(create_recipe_version_command_mock, uow, base_image_qry_srv_mock, deps)

    # ASSERT
    base_image_qry_srv_mock.get_base_image.assert_called_once_with(PRODUCT_ID)
    deps["parameter_service_mock"].get_parameter_value.assert_not_called()
    created: recipe_version.RecipeVersion = repo.add.call_args.args[0]
    assertpy.assert_that(created.parentImageUpstreamId).is_equal_to(MARKETPLACE_AMI_ID)
    assertpy.assert_that(created.parentImageProductId).is_equal_to(PRODUCT_ID)
    assertpy.assert_that(created.parentImageMarketplaceMetadata).is_equal_to(EXPECTED_METADATA)


def test_create_without_product_should_keep_the_default_parent_image(
    create_recipe_version_command_mock,
    base_image_qry_srv_mock,
    released_components,
    repo_and_uow,
    deps,
    get_test_ami_id,
):
    # ARRANGE
    repo, uow = repo_and_uow
    deps["parameter_service_mock"].get_parameter_value.return_value = get_test_ami_id
    released_components(create_recipe_version_command_mock)

    # ACT
    _create(create_recipe_version_command_mock, uow, base_image_qry_srv_mock, deps)

    # ASSERT
    base_image_qry_srv_mock.get_base_image.assert_not_called()
    created: recipe_version.RecipeVersion = repo.add.call_args.args[0]
    assertpy.assert_that(created.parentImageUpstreamId).is_equal_to(get_test_ami_id)
    assertpy.assert_that(created.parentImageProductId).is_none()
    assertpy.assert_that(created.parentImageMarketplaceMetadata).is_none()


@pytest.mark.parametrize(
    "image_overrides,volume_size,expected_message",
    (
        ({"platform": "Windows"}, "8", "is a Windows amd64 image, but the recipe is Linux amd64"),
        ({"architecture": "arm64"}, "8", "is a Linux arm64 image, but the recipe is Linux amd64"),
        ({"rootVolumeSize": 30}, "8", "needs a volume size of at least 30 GB"),
    ),
)
def test_create_should_reject_a_marketplace_ami_that_does_not_fit_the_recipe(
    create_recipe_version_command_mock,
    base_image_qry_srv_mock,
    released_components,
    repo_and_uow,
    deps,
    image_overrides,
    volume_size,
    expected_message,
):
    # ARRANGE
    repo, uow = repo_and_uow
    base_image_qry_srv_mock.get_base_image.return_value = _base_image(**image_overrides)
    create_recipe_version_command_mock.parentImageProductId = (
        recipe_version_parent_image_product_id_value_object.from_str(PRODUCT_ID)
    )
    create_recipe_version_command_mock.recipeVersionVolumeSize = recipe_version_volume_size_value_object.from_str(
        volume_size
    )
    released_components(create_recipe_version_command_mock)

    # ACT / ASSERT
    with pytest.raises(DomainException, match=expected_message):
        _create(create_recipe_version_command_mock, uow, base_image_qry_srv_mock, deps)
    repo.add.assert_not_called()


def test_create_should_fail_when_marketplace_base_images_are_not_wired(
    create_recipe_version_command_mock, released_components, repo_and_uow, deps
):
    repo, uow = repo_and_uow
    create_recipe_version_command_mock.parentImageProductId = (
        recipe_version_parent_image_product_id_value_object.from_str(PRODUCT_ID)
    )
    released_components(create_recipe_version_command_mock)

    with pytest.raises(DomainException, match="not available"):
        _create(create_recipe_version_command_mock, uow, None, deps)
    repo.add.assert_not_called()


def test_update_should_switch_to_the_marketplace_ami_and_publish_it(
    update_recipe_version_command_mock,
    base_image_qry_srv_mock,
    released_components,
    repo_and_uow,
    deps,
    get_test_recipe_version_with_specific_version_name,
):
    # ARRANGE
    repo, uow = repo_and_uow
    bus = mock.create_autospec(spec=message_bus.MessageBus)
    deps["recipe_version_query_service_mock"].get_recipe_version.return_value = (
        get_test_recipe_version_with_specific_version_name("1.0.0-rc.1")
    )
    update_recipe_version_command_mock.parentImageProductId = (
        recipe_version_parent_image_product_id_value_object.from_str(PRODUCT_ID)
    )
    released_components(update_recipe_version_command_mock)

    # ACT
    update_recipe_version_command_handler.handle(
        command=update_recipe_version_command_mock,
        uow=uow,
        message_bus=bus,
        component_version_qry_srv=deps["component_version_query_service_mock"],
        recipe_version_query_service=deps["recipe_version_query_service_mock"],
        recipe_qry_service=deps["recipe_query_service_mock"],
        parameter_qry_srv=deps["parameter_service_mock"],
        mandatory_components_list_qry_srv=deps["mandatory_components_list_query_service_mock"],
        system_configuration_mapping=deps["mock_system_configuration_mapping"],
        component_qry_srv=deps["component_query_service_mock"],
        marketplace_base_image_qry_srv=base_image_qry_srv_mock,
    )

    # ASSERT
    update_kwargs = repo.update_attributes.call_args.kwargs
    assertpy.assert_that(update_kwargs["parentImageUpstreamId"]).is_equal_to(MARKETPLACE_AMI_ID)
    assertpy.assert_that(update_kwargs["parentImageProductId"]).is_equal_to(PRODUCT_ID)
    assertpy.assert_that(update_kwargs["parentImageMarketplaceMetadata"]).is_equal_to(EXPECTED_METADATA)
    assertpy.assert_that(bus.publish.call_args.args[0].parent_image_upstream_id).is_equal_to(MARKETPLACE_AMI_ID)


def _update(command, uow, base_image_qry_srv, deps):
    update_recipe_version_command_handler.handle(
        command=command,
        uow=uow,
        message_bus=mock.create_autospec(spec=message_bus.MessageBus),
        component_version_qry_srv=deps["component_version_query_service_mock"],
        recipe_version_query_service=deps["recipe_version_query_service_mock"],
        recipe_qry_service=deps["recipe_query_service_mock"],
        parameter_qry_srv=deps["parameter_service_mock"],
        mandatory_components_list_qry_srv=deps["mandatory_components_list_query_service_mock"],
        system_configuration_mapping=deps["mock_system_configuration_mapping"],
        component_qry_srv=deps["component_query_service_mock"],
        marketplace_base_image_qry_srv=base_image_qry_srv,
    )


@pytest.fixture
def stored_marketplace_version(deps, get_test_recipe_version_with_specific_version_name):
    stored = get_test_recipe_version_with_specific_version_name("1.0.0-rc.1")
    stored.parentImageUpstreamId = "ami-0000000000000old0"
    stored.parentImageProductId = PRODUCT_ID
    stored.parentImageMarketplaceMetadata = EXPECTED_METADATA
    deps["recipe_version_query_service_mock"].get_recipe_version.return_value = stored
    return stored


def test_update_with_reset_should_go_back_to_the_default_parent_image(
    update_recipe_version_command_mock,
    base_image_qry_srv_mock,
    released_components,
    repo_and_uow,
    deps,
    get_test_ami_id,
    stored_marketplace_version,
):
    # ARRANGE
    repo, uow = repo_and_uow
    update_recipe_version_command_mock.resetParentImage = True
    deps["parameter_service_mock"].get_parameter_value.return_value = get_test_ami_id
    released_components(update_recipe_version_command_mock)

    # ACT
    _update(update_recipe_version_command_mock, uow, base_image_qry_srv_mock, deps)

    # ASSERT
    base_image_qry_srv_mock.get_base_image.assert_not_called()
    update_kwargs = repo.update_attributes.call_args.kwargs
    assertpy.assert_that(update_kwargs["parentImageUpstreamId"]).is_equal_to(get_test_ami_id)
    assertpy.assert_that(update_kwargs["parentImageProductId"]).is_none()
    assertpy.assert_that(update_kwargs["parentImageMarketplaceMetadata"]).is_none()


def test_update_without_base_image_choice_should_keep_the_marketplace_parent(
    update_recipe_version_command_mock,
    base_image_qry_srv_mock,
    released_components,
    repo_and_uow,
    deps,
    stored_marketplace_version,
):
    # ARRANGE: a client that does not send the field (CLI, automation) only changes components
    repo, uow = repo_and_uow
    released_components(update_recipe_version_command_mock)

    # ACT
    _update(update_recipe_version_command_mock, uow, base_image_qry_srv_mock, deps)

    # ASSERT: same product, re-resolved to its latest AMI like the default parent image
    base_image_qry_srv_mock.get_base_image.assert_called_once_with(PRODUCT_ID)
    deps["parameter_service_mock"].get_parameter_value.assert_not_called()
    update_kwargs = repo.update_attributes.call_args.kwargs
    assertpy.assert_that(update_kwargs["parentImageUpstreamId"]).is_equal_to(MARKETPLACE_AMI_ID)
    assertpy.assert_that(update_kwargs["parentImageProductId"]).is_equal_to(PRODUCT_ID)
    assertpy.assert_that(update_kwargs["parentImageMarketplaceMetadata"]).is_equal_to(EXPECTED_METADATA)


def test_update_without_marketplace_access_should_keep_the_stored_parent(
    update_recipe_version_command_mock, released_components, repo_and_uow, deps, stored_marketplace_version
):
    # ARRANGE: the s2s API has no Marketplace access
    repo, uow = repo_and_uow
    released_components(update_recipe_version_command_mock)

    # ACT
    _update(update_recipe_version_command_mock, uow, None, deps)

    # ASSERT
    deps["parameter_service_mock"].get_parameter_value.assert_not_called()
    update_kwargs = repo.update_attributes.call_args.kwargs
    assertpy.assert_that(update_kwargs["parentImageUpstreamId"]).is_equal_to("ami-0000000000000old0")
    assertpy.assert_that(update_kwargs["parentImageProductId"]).is_equal_to(PRODUCT_ID)
    assertpy.assert_that(update_kwargs["parentImageMarketplaceMetadata"]).is_equal_to(EXPECTED_METADATA)


def test_update_without_marketplace_access_should_still_check_the_minimum_volume_size(
    update_recipe_version_command_mock, released_components, repo_and_uow, deps, stored_marketplace_version
):
    repo, uow = repo_and_uow
    stored_marketplace_version.parentImageMarketplaceMetadata = {**EXPECTED_METADATA, "rootVolumeSize": 30}
    released_components(update_recipe_version_command_mock)

    with pytest.raises(DomainException, match="needs a volume size of at least 30 GB"):
        _update(update_recipe_version_command_mock, uow, None, deps)
    repo.update_attributes.assert_not_called()


def test_update_choosing_a_product_without_marketplace_access_should_fail(
    update_recipe_version_command_mock, released_components, repo_and_uow, deps, stored_marketplace_version
):
    repo, uow = repo_and_uow
    update_recipe_version_command_mock.parentImageProductId = (
        recipe_version_parent_image_product_id_value_object.from_str("prod-anotherproduct")
    )
    released_components(update_recipe_version_command_mock)

    with pytest.raises(DomainException, match="not available"):
        _update(update_recipe_version_command_mock, uow, None, deps)
    repo.update_attributes.assert_not_called()


@pytest.mark.parametrize("value", ("prod-ib2w5aw4ynhey", "47489723-7305-4e22-8b22-b0d57054f216"))
def test_parent_image_product_id_should_accept_both_marketplace_product_id_formats(value):
    assertpy.assert_that(recipe_version_parent_image_product_id_value_object.from_str(value).value).is_equal_to(value)


@pytest.mark.parametrize(
    "value",
    (
        "",
        "ami-0123",
        "prod-UPPER",
        "prod-" + "a" * 64,
        "47489723-7305-4E22-8B22-B0D57054F216",
        "47489723-7305-4e22-8b22",
    ),
)
def test_parent_image_product_id_should_reject_invalid_values(value):
    with pytest.raises(DomainException):
        recipe_version_parent_image_product_id_value_object.from_str(value)


# ---- imported AWS-published images (Windows Server, RHEL, ...) as base image ----

IMPORTED_IMAGE_ID = "image-rhel9abc"
RHEL_AMI_ID = "ami-0b07d2bc8152a1d84"


def _imported_base_image(**overrides) -> MarketplaceBaseImage:
    values = dict(
        imageId=IMPORTED_IMAGE_ID,
        productName="RHEL 9",
        amiId=RHEL_AMI_ID,
        platform="Linux",
        architecture="amd64",
        rootVolumeSize=8,
        subscriptionOwnership="AWS_MANAGED",
    )
    values.update(overrides)
    return MarketplaceBaseImage(**values)


def test_create_should_build_on_an_imported_aws_published_image_without_license_data(
    create_recipe_version_command_mock, base_image_qry_srv_mock, released_components, repo_and_uow, deps
):
    # ARRANGE
    repo, uow = repo_and_uow
    base_image_qry_srv_mock.get_imported_base_image.return_value = _imported_base_image()
    create_recipe_version_command_mock.parentImageId = recipe_version_parent_image_id_value_object.from_str(
        IMPORTED_IMAGE_ID
    )
    released_components(create_recipe_version_command_mock)

    # ACT
    _create(create_recipe_version_command_mock, uow, base_image_qry_srv_mock, deps)

    # ASSERT: AWS is the seller of record, so nothing is handed on for a grant
    base_image_qry_srv_mock.get_imported_base_image.assert_called_once_with(
        create_recipe_version_command_mock.projectId.value, IMPORTED_IMAGE_ID
    )
    base_image_qry_srv_mock.get_base_image.assert_not_called()
    created: recipe_version.RecipeVersion = repo.add.call_args.args[0]
    assertpy.assert_that(created.parentImageUpstreamId).is_equal_to(RHEL_AMI_ID)
    assertpy.assert_that(created.parentImageId).is_equal_to(IMPORTED_IMAGE_ID)
    assertpy.assert_that(created.parentImageProductId).is_none()
    assertpy.assert_that(created.parentImageMarketplaceMetadata).is_none()
    assertpy.assert_that(created.parentImageSupportedInstanceTypes).is_none()


def test_create_should_reject_both_a_product_and_an_imported_image(
    create_recipe_version_command_mock, base_image_qry_srv_mock, released_components, repo_and_uow, deps
):
    repo, uow = repo_and_uow
    create_recipe_version_command_mock.parentImageProductId = (
        recipe_version_parent_image_product_id_value_object.from_str(PRODUCT_ID)
    )
    create_recipe_version_command_mock.parentImageId = recipe_version_parent_image_id_value_object.from_str(
        IMPORTED_IMAGE_ID
    )
    released_components(create_recipe_version_command_mock)

    with pytest.raises(DomainException, match="not both"):
        _create(create_recipe_version_command_mock, uow, base_image_qry_srv_mock, deps)
    repo.add.assert_not_called()


def test_create_should_reject_an_imported_image_that_does_not_fit_the_recipe(
    create_recipe_version_command_mock, base_image_qry_srv_mock, released_components, repo_and_uow, deps
):
    repo, uow = repo_and_uow
    base_image_qry_srv_mock.get_imported_base_image.return_value = _imported_base_image(platform="Windows")
    create_recipe_version_command_mock.parentImageId = recipe_version_parent_image_id_value_object.from_str(
        IMPORTED_IMAGE_ID
    )
    released_components(create_recipe_version_command_mock)

    with pytest.raises(DomainException, match="Image image-rhel9abc is a Windows amd64 image"):
        _create(create_recipe_version_command_mock, uow, base_image_qry_srv_mock, deps)


def test_update_should_switch_from_a_marketplace_product_to_an_imported_image(
    update_recipe_version_command_mock,
    base_image_qry_srv_mock,
    released_components,
    repo_and_uow,
    deps,
    stored_marketplace_version,
):
    # ARRANGE: the wizard sends "" for the product and the chosen image
    repo, uow = repo_and_uow
    base_image_qry_srv_mock.get_imported_base_image.return_value = _imported_base_image()
    update_recipe_version_command_mock.parentImageId = recipe_version_parent_image_id_value_object.from_str(
        IMPORTED_IMAGE_ID
    )
    update_recipe_version_command_mock.resetParentImage = True
    released_components(update_recipe_version_command_mock)

    # ACT
    _update(update_recipe_version_command_mock, uow, base_image_qry_srv_mock, deps)

    # ASSERT: the old product and its license data are gone
    update_kwargs = repo.update_attributes.call_args.kwargs
    assertpy.assert_that(update_kwargs["parentImageUpstreamId"]).is_equal_to(RHEL_AMI_ID)
    assertpy.assert_that(update_kwargs["parentImageId"]).is_equal_to(IMPORTED_IMAGE_ID)
    assertpy.assert_that(update_kwargs["parentImageProductId"]).is_none()
    assertpy.assert_that(update_kwargs["parentImageMarketplaceMetadata"]).is_none()
    assertpy.assert_that(update_kwargs["parentImageSupportedInstanceTypes"]).is_none()


def test_update_without_base_image_choice_should_keep_the_imported_image(
    update_recipe_version_command_mock,
    base_image_qry_srv_mock,
    released_components,
    repo_and_uow,
    deps,
    get_test_recipe_version_with_specific_version_name,
):
    repo, uow = repo_and_uow
    stored = get_test_recipe_version_with_specific_version_name("1.0.0-rc.1")
    stored.parentImageUpstreamId = RHEL_AMI_ID
    stored.parentImageId = IMPORTED_IMAGE_ID
    deps["recipe_version_query_service_mock"].get_recipe_version.return_value = stored
    base_image_qry_srv_mock.get_imported_base_image.return_value = _imported_base_image()
    released_components(update_recipe_version_command_mock)

    _update(update_recipe_version_command_mock, uow, base_image_qry_srv_mock, deps)

    base_image_qry_srv_mock.get_imported_base_image.assert_called_once()
    update_kwargs = repo.update_attributes.call_args.kwargs
    assertpy.assert_that(update_kwargs["parentImageId"]).is_equal_to(IMPORTED_IMAGE_ID)
    assertpy.assert_that(update_kwargs["parentImageUpstreamId"]).is_equal_to(RHEL_AMI_ID)


def test_update_with_reset_should_drop_the_imported_image(
    update_recipe_version_command_mock,
    base_image_qry_srv_mock,
    released_components,
    repo_and_uow,
    deps,
    get_test_ami_id,
    get_test_recipe_version_with_specific_version_name,
):
    repo, uow = repo_and_uow
    stored = get_test_recipe_version_with_specific_version_name("1.0.0-rc.1")
    stored.parentImageId = IMPORTED_IMAGE_ID
    deps["recipe_version_query_service_mock"].get_recipe_version.return_value = stored
    deps["parameter_service_mock"].get_parameter_value.return_value = get_test_ami_id
    update_recipe_version_command_mock.resetParentImage = True
    released_components(update_recipe_version_command_mock)

    _update(update_recipe_version_command_mock, uow, base_image_qry_srv_mock, deps)

    update_kwargs = repo.update_attributes.call_args.kwargs
    assertpy.assert_that(update_kwargs["parentImageUpstreamId"]).is_equal_to(get_test_ami_id)
    assertpy.assert_that(update_kwargs["parentImageId"]).is_none()


@pytest.mark.parametrize("value", ("", "prod-abc", "image-UPPER", "image-" + "a" * 64))
def test_parent_image_id_should_reject_invalid_values(value):
    with pytest.raises(DomainException):
        recipe_version_parent_image_id_value_object.from_str(value)
