"""Shared by the create and update recipe version handlers: builds a recipe version on an AWS Marketplace AMI.

Two kinds of base image:
- a subscribed Marketplace product (``parentImageProductId``): license data is handed on to built images;
- an AMI that AWS publishes, imported into the project (``parentImageId``, imageSource AWS_PUBLISHED_AMI):
  AWS is the seller of record, so there is no license to hand on.
"""

from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe
from app.packaging.domain.ports.marketplace_base_image_query_service import MarketplaceBaseImageQueryService
from app.packaging.domain.read_models.marketplace_base_image import MarketplaceBaseImage
from app.packaging.domain.value_objects.recipe_version import recipe_version_parent_image_upstream_id_value_object


@dataclass(frozen=True)
class ParentImage:
    """What a recipe version stores about its parent image."""

    upstream_id: str
    product_id: str | None = None
    image_id: str | None = None
    marketplace_metadata: dict | None = None
    supported_instance_types: list[str] | None = None


def _check_fits(image: MarketplaceBaseImage, label: str, recipe_entity: recipe.Recipe, volume_size: str) -> None:
    if image.platform != recipe_entity.recipePlatform or image.architecture != recipe_entity.recipeArchitecture:
        raise domain_exception.DomainException(
            f"{label} is a {image.platform} {image.architecture} image, "
            f"but the recipe is {recipe_entity.recipePlatform} {recipe_entity.recipeArchitecture}."
        )
    if int(volume_size) < image.rootVolumeSize:
        raise domain_exception.DomainException(f"{label} needs a volume size of at least {image.rootVolumeSize} GB.")
    # Same AMI ID format check as for the default parent images.
    recipe_version_parent_image_upstream_id_value_object.from_str(image.amiId)


def _require(marketplace_base_image_qry_srv: MarketplaceBaseImageQueryService | None):
    if marketplace_base_image_qry_srv is None:
        raise domain_exception.DomainException("AWS Marketplace base images are not available.")
    return marketplace_base_image_qry_srv


def resolve(
    marketplace_base_image_qry_srv: MarketplaceBaseImageQueryService | None,
    product_id: str,
    recipe_entity: recipe.Recipe,
    volume_size: str,
) -> MarketplaceBaseImage:
    image = _require(marketplace_base_image_qry_srv).get_base_image(product_id)
    _check_fits(image, f"Product {product_id}", recipe_entity, volume_size)
    return image


def resolve_parent_image(
    marketplace_base_image_qry_srv: MarketplaceBaseImageQueryService | None,
    recipe_entity: recipe.Recipe,
    volume_size: str,
    project_id: str,
    product_id: str | None = None,
    image_id: str | None = None,
) -> ParentImage:
    """The Marketplace parent image of a recipe version, from a product ID or an imported image ID."""
    if product_id and image_id:
        raise domain_exception.DomainException(
            "Choose either an AWS Marketplace product or an imported AWS-published image as base image, not both."
        )
    if product_id:
        image = resolve(marketplace_base_image_qry_srv, product_id, recipe_entity, volume_size)
        return ParentImage(
            upstream_id=image.amiId,
            product_id=product_id,
            marketplace_metadata=image.to_parent_image_marketplace_metadata(),
            supported_instance_types=image.supportedInstanceTypes or None,
        )
    image = _require(marketplace_base_image_qry_srv).get_imported_base_image(project_id, image_id)
    _check_fits(image, f"Image {image_id}", recipe_entity, volume_size)
    # No license data: nothing is granted to spoke accounts for AWS-published AMIs.
    return ParentImage(upstream_id=image.amiId, image_id=image_id)
