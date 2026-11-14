import assertpy
import pytest

from app.packaging.domain.command_handlers.recipe import recipe_version_parent_image
from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.image import image
from app.packaging.domain.model.image.image_constants import ImageSource
from app.packaging.domain.tests.conftest import (
    TEST_MARKETPLACE_AMI_ID,
    TEST_MARKETPLACE_IMAGE_ID,
    TEST_MARKETPLACE_LICENSE_ARN,
    TEST_MARKETPLACE_PRODUCT_CODE,
    TEST_PROJECT_ID,
    TEST_REGION,
)

TEST_OTHER_REGION = "eu-west-1"
TEST_OTHER_REGION_AMI_ID = "ami-0fedcba9876543210"


def _get_parent_image_upstream_id(
    image_query_service_mock,
    ami_validation_service_mock,
    mock_recipe_object,
    volume_size="8",
    region=TEST_REGION,
):
    return recipe_version_parent_image.get_parent_image_upstream_id(
        parent_image_id=TEST_MARKETPLACE_IMAGE_ID,
        project_id=TEST_PROJECT_ID,
        recipe_entity=mock_recipe_object,
        volume_size=volume_size,
        region=region,
        image_qry_srv=image_query_service_mock,
        ami_validation_svc=ami_validation_service_mock,
    )


def test_get_parent_image_upstream_id_should_return_the_regional_ami_of_the_image(
    image_query_service_mock,
    ami_validation_service_mock,
    mock_recipe_object,
    get_test_marketplace_base_image,
    get_test_marketplace_base_ami_description,
):
    # ARRANGE
    image_query_service_mock.get_image.return_value = get_test_marketplace_base_image(
        regional_ami_ids={TEST_REGION: TEST_MARKETPLACE_AMI_ID, TEST_OTHER_REGION: TEST_OTHER_REGION_AMI_ID},
        original_ami_region=TEST_OTHER_REGION,
    )
    ami_validation_service_mock.describe_marketplace_image.return_value = get_test_marketplace_base_ami_description()

    # ACT
    parent_image_upstream_id = _get_parent_image_upstream_id(
        image_query_service_mock, ami_validation_service_mock, mock_recipe_object
    )

    # ASSERT
    assertpy.assert_that(parent_image_upstream_id).is_equal_to(TEST_MARKETPLACE_AMI_ID)
    image_query_service_mock.get_image.assert_called_once_with(
        project_id=TEST_PROJECT_ID, image_id=TEST_MARKETPLACE_IMAGE_ID
    )
    ami_validation_service_mock.describe_marketplace_image.assert_called_once_with(TEST_MARKETPLACE_AMI_ID)


def test_get_parent_image_upstream_id_should_fall_back_to_the_imported_ami_in_its_original_region(
    image_query_service_mock,
    ami_validation_service_mock,
    mock_recipe_object,
    get_test_marketplace_base_image,
    get_test_marketplace_base_ami_description,
):
    # ARRANGE
    image_query_service_mock.get_image.return_value = get_test_marketplace_base_image(
        regional_ami_ids={TEST_OTHER_REGION: TEST_OTHER_REGION_AMI_ID},
        original_ami_region=TEST_REGION,
    )
    ami_validation_service_mock.describe_marketplace_image.return_value = get_test_marketplace_base_ami_description()

    # ACT
    parent_image_upstream_id = _get_parent_image_upstream_id(
        image_query_service_mock, ami_validation_service_mock, mock_recipe_object
    )

    # ASSERT
    assertpy.assert_that(parent_image_upstream_id).is_equal_to(TEST_MARKETPLACE_AMI_ID)


def test_get_parent_image_upstream_id_should_raise_if_image_has_no_ami_in_the_region(
    image_query_service_mock,
    ami_validation_service_mock,
    mock_recipe_object,
    get_test_marketplace_base_image,
):
    # ARRANGE
    image_query_service_mock.get_image.return_value = get_test_marketplace_base_image(
        regional_ami_ids={TEST_OTHER_REGION: TEST_OTHER_REGION_AMI_ID},
        original_ami_region=TEST_OTHER_REGION,
    )

    # ACT
    with pytest.raises(DomainException) as exc_info:
        _get_parent_image_upstream_id(image_query_service_mock, ami_validation_service_mock, mock_recipe_object)

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Image {TEST_MARKETPLACE_IMAGE_ID} has no AMI in {TEST_REGION}, the region recipes are built in."
    )
    ami_validation_service_mock.describe_marketplace_image.assert_not_called()


@pytest.mark.parametrize(
    "image_kwargs,expected_message",
    (
        (None, f"Image {TEST_MARKETPLACE_IMAGE_ID} can not be found in project {TEST_PROJECT_ID}."),
        (
            {"image_source": ImageSource.EXISTING_AMI},
            "only images imported from AWS Marketplace are supported",
        ),
        (
            {"image_source": ImageSource.PIPELINE},
            "only images imported from AWS Marketplace are supported",
        ),
        (
            {"status": image.ImageStatus.Retired},
            f"while in {image.ImageStatus.Retired} status",
        ),
        (
            {"platform": "Windows"},
            f"Image {TEST_MARKETPLACE_IMAGE_ID} is a Windows amd64 image, but the recipe is Linux amd64.",
        ),
        (
            {"architecture": "arm64"},
            f"Image {TEST_MARKETPLACE_IMAGE_ID} is a Linux arm64 image, but the recipe is Linux amd64.",
        ),
    ),
)
def test_get_parent_image_upstream_id_should_raise_if_image_can_not_be_used(
    image_kwargs,
    expected_message,
    image_query_service_mock,
    ami_validation_service_mock,
    mock_recipe_object,
    get_test_marketplace_base_image,
):
    # ARRANGE
    image_query_service_mock.get_image.return_value = (
        get_test_marketplace_base_image(**image_kwargs) if image_kwargs is not None else None
    )

    # ACT
    with pytest.raises(DomainException) as exc_info:
        _get_parent_image_upstream_id(image_query_service_mock, ami_validation_service_mock, mock_recipe_object)

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).contains(expected_message)
    ami_validation_service_mock.describe_marketplace_image.assert_not_called()


@pytest.mark.parametrize(
    "ami_description_kwargs,volume_size,expected_message",
    (
        (
            {"state": "deregistered"},
            "8",
            f"AMI {TEST_MARKETPLACE_AMI_ID} of image {TEST_MARKETPLACE_IMAGE_ID} is not available (state: deregistered).",
        ),
        (
            {"root_device_name": "/dev/xvda"},
            "8",
            f"Image {TEST_MARKETPLACE_IMAGE_ID} boots from /dev/xvda: only images that boot from /dev/sda1 can be used",
        ),
        (
            {"root_volume_size": None},
            "8",
            f"Image {TEST_MARKETPLACE_IMAGE_ID} has no EBS root volume on /dev/sda1",
        ),
        (
            {"root_volume_size": 30},
            "20",
            f"Image {TEST_MARKETPLACE_IMAGE_ID} needs a volume size of at least 30 GB.",
        ),
    ),
)
def test_get_parent_image_upstream_id_should_raise_if_ami_can_not_be_used(
    ami_description_kwargs,
    volume_size,
    expected_message,
    image_query_service_mock,
    ami_validation_service_mock,
    mock_recipe_object,
    get_test_marketplace_base_image,
    get_test_marketplace_base_ami_description,
):
    # ARRANGE
    image_query_service_mock.get_image.return_value = get_test_marketplace_base_image()
    ami_validation_service_mock.describe_marketplace_image.return_value = get_test_marketplace_base_ami_description(
        **ami_description_kwargs
    )

    # ACT
    with pytest.raises(DomainException) as exc_info:
        _get_parent_image_upstream_id(
            image_query_service_mock, ami_validation_service_mock, mock_recipe_object, volume_size=volume_size
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).contains(expected_message)


def test_get_parent_image_upstream_id_should_accept_a_volume_size_equal_to_the_ami_root_volume(
    image_query_service_mock,
    ami_validation_service_mock,
    mock_recipe_object,
    get_test_marketplace_base_image,
    get_test_marketplace_base_ami_description,
):
    # ARRANGE
    image_query_service_mock.get_image.return_value = get_test_marketplace_base_image()
    ami_validation_service_mock.describe_marketplace_image.return_value = get_test_marketplace_base_ami_description(
        root_volume_size=30
    )

    # ACT
    parent_image_upstream_id = _get_parent_image_upstream_id(
        image_query_service_mock, ami_validation_service_mock, mock_recipe_object, volume_size="30"
    )

    # ASSERT
    assertpy.assert_that(parent_image_upstream_id).is_equal_to(TEST_MARKETPLACE_AMI_ID)


def test_get_parent_image_upstream_id_should_raise_if_ami_can_not_be_described(
    image_query_service_mock,
    ami_validation_service_mock,
    mock_recipe_object,
    get_test_marketplace_base_image,
):
    # ARRANGE
    image_query_service_mock.get_image.return_value = get_test_marketplace_base_image()
    ami_validation_service_mock.describe_marketplace_image.side_effect = Exception("not found")

    # ACT
    with pytest.raises(DomainException) as exc_info:
        _get_parent_image_upstream_id(image_query_service_mock, ami_validation_service_mock, mock_recipe_object)

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"AMI {TEST_MARKETPLACE_AMI_ID} of image {TEST_MARKETPLACE_IMAGE_ID} can not be described."
    )


def test_get_parent_image_marketplace_metadata_should_return_license_details_without_regional_amis(
    image_query_service_mock,
    mock_recipe_version_object,
    get_test_marketplace_base_image,
):
    # ARRANGE
    mock_recipe_version_object.parentImageId = TEST_MARKETPLACE_IMAGE_ID
    image_query_service_mock.get_image.return_value = get_test_marketplace_base_image(status=image.ImageStatus.Retired)

    # ACT
    marketplace_metadata = recipe_version_parent_image.get_parent_image_marketplace_metadata(
        image_qry_srv=image_query_service_mock,
        project_id=TEST_PROJECT_ID,
        recipe_version_entity=mock_recipe_version_object,
    )

    # ASSERT
    image_query_service_mock.get_image.assert_called_once_with(
        project_id=TEST_PROJECT_ID, image_id=TEST_MARKETPLACE_IMAGE_ID
    )
    assertpy.assert_that(marketplace_metadata).is_equal_to(
        {
            "productCode": TEST_MARKETPLACE_PRODUCT_CODE,
            "subscriptionOwnership": "VEW_MANAGED",
            "licenseGrantAllowed": True,
            "licenseConfigurationArn": TEST_MARKETPLACE_LICENSE_ARN,
            "homeRegion": TEST_REGION,
        }
    )


def test_get_parent_image_marketplace_metadata_should_leave_out_missing_license_details(
    image_query_service_mock,
    mock_recipe_version_object,
    get_test_marketplace_base_image,
):
    # ARRANGE
    mock_recipe_version_object.parentImageId = TEST_MARKETPLACE_IMAGE_ID
    parent_image = get_test_marketplace_base_image()
    parent_image.marketplaceMetadata = {
        "productCode": TEST_MARKETPLACE_PRODUCT_CODE,
        "subscriptionOwnership": "EXTERNALLY_MANAGED",
        "regionalAmiIds": {TEST_REGION: TEST_MARKETPLACE_AMI_ID},
        "licenseConfigurationArn": None,
        "homeRegion": None,
    }
    image_query_service_mock.get_image.return_value = parent_image

    # ACT
    marketplace_metadata = recipe_version_parent_image.get_parent_image_marketplace_metadata(
        image_qry_srv=image_query_service_mock,
        project_id=TEST_PROJECT_ID,
        recipe_version_entity=mock_recipe_version_object,
    )

    # ASSERT
    assertpy.assert_that(marketplace_metadata).is_equal_to(
        {"productCode": TEST_MARKETPLACE_PRODUCT_CODE, "subscriptionOwnership": "EXTERNALLY_MANAGED"}
    )


def test_get_parent_image_marketplace_metadata_should_return_none_without_parent_image(
    image_query_service_mock,
    mock_recipe_version_object,
):
    # ACT
    marketplace_metadata = recipe_version_parent_image.get_parent_image_marketplace_metadata(
        image_qry_srv=image_query_service_mock,
        project_id=TEST_PROJECT_ID,
        recipe_version_entity=mock_recipe_version_object,
    )

    # ASSERT
    assertpy.assert_that(marketplace_metadata).is_none()
    image_query_service_mock.get_image.assert_not_called()


@pytest.mark.parametrize("parent_image_found", (False, True))
def test_get_parent_image_marketplace_metadata_should_return_none_if_parent_image_has_no_marketplace_metadata(
    parent_image_found,
    image_query_service_mock,
    mock_recipe_version_object,
    get_test_marketplace_base_image,
):
    # ARRANGE
    mock_recipe_version_object.parentImageId = TEST_MARKETPLACE_IMAGE_ID
    parent_image = get_test_marketplace_base_image()
    parent_image.marketplaceMetadata = None
    image_query_service_mock.get_image.return_value = parent_image if parent_image_found else None

    # ACT
    marketplace_metadata = recipe_version_parent_image.get_parent_image_marketplace_metadata(
        image_qry_srv=image_query_service_mock,
        project_id=TEST_PROJECT_ID,
        recipe_version_entity=mock_recipe_version_object,
    )

    # ASSERT
    assertpy.assert_that(marketplace_metadata).is_none()


def test_get_parent_image_upstream_id_should_accept_a_retired_image_when_it_is_the_current_parent_image(
    image_query_service_mock,
    ami_validation_service_mock,
    mock_recipe_object,
    get_test_marketplace_base_image,
    get_test_marketplace_base_ami_description,
):
    # ARRANGE
    image_query_service_mock.get_image.return_value = get_test_marketplace_base_image(status=image.ImageStatus.Retired)
    ami_validation_service_mock.describe_marketplace_image.return_value = get_test_marketplace_base_ami_description()

    # ACT
    parent_image_upstream_id = recipe_version_parent_image.get_parent_image_upstream_id(
        parent_image_id=TEST_MARKETPLACE_IMAGE_ID,
        project_id=TEST_PROJECT_ID,
        recipe_entity=mock_recipe_object,
        volume_size="8",
        region=TEST_REGION,
        image_qry_srv=image_query_service_mock,
        ami_validation_svc=ami_validation_service_mock,
        is_current_parent_image=True,
    )

    # ASSERT
    assertpy.assert_that(parent_image_upstream_id).is_equal_to(TEST_MARKETPLACE_AMI_ID)
