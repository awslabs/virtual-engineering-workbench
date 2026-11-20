from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.image import image
from app.packaging.domain.model.image.image_constants import ImageSource
from app.packaging.domain.model.recipe import recipe, recipe_version
from app.packaging.domain.ports import ami_validation_service, image_query_service
from app.packaging.domain.read_models.ami_description import AmiDescription
from app.packaging.domain.value_objects.recipe_version import recipe_version_parent_image_upstream_id_value_object

# Recipes, recipe testing and the product templates all map the root volume to this device.
ROOT_DEVICE_NAME = "/dev/sda1"
AMI_AVAILABLE_STATE = "available"
# The regional AMI IDs are the seller's AMIs of the base image, so images built on it don't carry them.
CARRIED_MARKETPLACE_METADATA_KEYS = [
    "productCode",
    "subscriptionOwnership",
    "licenseGrantAllowed",
    "licenseConfigurationArn",
    "homeRegion",
]


def _get_marketplace_image(
    image_qry_srv: image_query_service.ImageQueryService,
    project_id: str,
    image_id: str,
    is_current_parent_image: bool,
) -> image.Image:
    image_entity = image_qry_srv.get_image(project_id=project_id, image_id=image_id)

    if image_entity is None:
        raise domain_exception.DomainException(f"Image {image_id} can not be found in project {project_id}.")
    if image_entity.imageSource != ImageSource.MARKETPLACE_PRODUCT:
        raise domain_exception.DomainException(
            f"Image {image_id} can't be used as a base image: only images imported from AWS Marketplace are supported."
        )
    # A later import of the same product retires the image, and a recipe version that builds on it keeps doing so.
    accepted_statuses = [image.ImageStatus.Created]
    if is_current_parent_image:
        accepted_statuses.append(image.ImageStatus.Retired)
    if image_entity.status not in accepted_statuses:
        raise domain_exception.DomainException(
            f"Image {image_id} can't be used as a base image while in {image_entity.status} status: "
            f"only {image.ImageStatus.Created} images are accepted."
        )

    return image_entity


def _check_platform_and_architecture(image_entity: image.Image, recipe_entity: recipe.Recipe) -> None:
    if (
        image_entity.platform != recipe_entity.recipePlatform
        or image_entity.architecture != recipe_entity.recipeArchitecture
    ):
        raise domain_exception.DomainException(
            f"Image {image_entity.imageId} is a {image_entity.platform} {image_entity.architecture} image, "
            f"but the recipe is {recipe_entity.recipePlatform} {recipe_entity.recipeArchitecture}."
        )


def _get_regional_ami_id(image_entity: image.Image, region: str) -> str:
    regional_ami_ids = (image_entity.marketplaceMetadata or {}).get("regionalAmiIds") or {}
    ami_id = regional_ami_ids.get(region)

    if not ami_id and image_entity.originalAmiRegion == region:
        ami_id = image_entity.imageUpstreamId
    if not ami_id:
        raise domain_exception.DomainException(
            f"Image {image_entity.imageId} has no AMI in {region}, the region recipes are built in."
        )

    return ami_id


def _describe_ami(
    ami_validation_svc: ami_validation_service.AmiValidationService,
    image_id: str,
    ami_id: str,
) -> AmiDescription:
    try:
        ami_description = ami_validation_svc.describe_marketplace_image(ami_id)
    except Exception as e:
        raise domain_exception.DomainException(f"AMI {ami_id} of image {image_id} can not be described.") from e

    if ami_description.state != AMI_AVAILABLE_STATE:
        raise domain_exception.DomainException(
            f"AMI {ami_id} of image {image_id} is not available (state: {ami_description.state})."
        )

    return ami_description


def _check_root_volume(ami_description: AmiDescription, image_id: str, volume_size: str) -> None:
    if ami_description.rootDeviceName != ROOT_DEVICE_NAME:
        raise domain_exception.DomainException(
            f"Image {image_id} boots from {ami_description.rootDeviceName}: "
            f"only images that boot from {ROOT_DEVICE_NAME} can be used as a base image."
        )

    root_volume_size = next(
        (
            block_device_mapping.ebs.volumeSize
            for block_device_mapping in ami_description.blockDeviceMappings
            if block_device_mapping.deviceName == ROOT_DEVICE_NAME and block_device_mapping.ebs
        ),
        None,
    )
    if root_volume_size is None:
        raise domain_exception.DomainException(
            f"Image {image_id} has no EBS root volume on {ROOT_DEVICE_NAME} and can't be used as a base image."
        )
    if int(volume_size) < root_volume_size:
        raise domain_exception.DomainException(
            f"Image {image_id} needs a volume size of at least {root_volume_size} GB."
        )


def get_parent_image_upstream_id(
    parent_image_id: str,
    project_id: str,
    recipe_entity: recipe.Recipe,
    volume_size: str,
    region: str,
    image_qry_srv: image_query_service.ImageQueryService,
    ami_validation_svc: ami_validation_service.AmiValidationService,
    is_current_parent_image: bool = False,
) -> str:
    """Returns the AMI a recipe version builds on when it uses an imported AWS Marketplace image as its base.

    The AMI is the image's AMI in the region recipes are built in. The recipe version stores it, so the version
    keeps building on that AMI even after a later import of the same product retires the image. A retired image is
    accepted only when it is the recipe version's current parent image.
    """

    image_entity = _get_marketplace_image(image_qry_srv, project_id, parent_image_id, is_current_parent_image)
    _check_platform_and_architecture(image_entity, recipe_entity)

    ami_id = _get_regional_ami_id(image_entity, region)
    ami_description = _describe_ami(ami_validation_svc, parent_image_id, ami_id)
    _check_root_volume(ami_description, parent_image_id, volume_size)

    return recipe_version_parent_image_upstream_id_value_object.from_str(ami_id).value


def get_parent_image_marketplace_metadata(
    image_qry_srv: image_query_service.ImageQueryService,
    project_id: str,
    recipe_version_entity: recipe_version.RecipeVersion,
) -> dict | None:
    """Returns the AWS Marketplace license details an image built from the recipe version inherits from its base."""

    if not recipe_version_entity.parentImageId:
        return None

    parent_image_entity = image_qry_srv.get_image(project_id=project_id, image_id=recipe_version_entity.parentImageId)
    if not parent_image_entity or not parent_image_entity.marketplaceMetadata:
        return None

    return {
        key: parent_image_entity.marketplaceMetadata[key]
        for key in CARRIED_MARKETPLACE_METADATA_KEYS
        if parent_image_entity.marketplaceMetadata.get(key) is not None
    }
