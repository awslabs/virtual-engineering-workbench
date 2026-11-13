import re
from dataclasses import dataclass
from typing import Optional

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.value_objects.image.product_code_value_object import PRODUCT_CODE_PATTERN

LICENSE_ARN_PATTERN = re.compile(r"^arn:aws:license-manager:[a-z0-9-]*:\d{12}:license:[a-z0-9-]+$")


@dataclass(frozen=True)
class MarketplaceMetadataValueObject:
    """Bundles multiple marketplace-related fields into a single value object.

    This is an intentional exception to the one-VO-per-field pattern because
    these fields are always validated, persisted, and transferred together as
    an atomic marketplace subscription descriptor.
    """

    productCode: str
    subscriptionOwnership: str
    regionalAmiIds: dict[str, str]
    # False is intentionally backward compatible for records/import callers that
    # predate the per-license CreateGrant capability.
    licenseGrantAllowed: bool = False
    licenseConfigurationArn: Optional[str] = None
    homeRegion: Optional[str] = None


def _validate_required_fields(value: dict) -> str:
    product_code = value.get("productCode")
    if not product_code:
        raise domain_exception.DomainException("Marketplace product code is required.")
    if not PRODUCT_CODE_PATTERN.match(product_code):
        raise domain_exception.DomainException(
            f"Invalid product code format: {product_code}. Must be 13-25 lowercase alphanumeric characters."
        )
    if value.get("subscriptionOwnership") not in ("VEW_MANAGED", "EXTERNALLY_MANAGED"):
        raise domain_exception.DomainException("Subscription ownership must be VEW_MANAGED or EXTERNALLY_MANAGED.")
    if not value.get("regionalAmiIds"):
        raise domain_exception.DomainException("At least one regional AMI ID is required.")
    return product_code


def _validate_optional_fields(value: dict) -> Optional[str]:
    license_arn = value.get("licenseConfigurationArn")
    if license_arn and not LICENSE_ARN_PATTERN.match(license_arn):
        raise domain_exception.DomainException(f"Invalid license configuration ARN format: {license_arn}.")
    return license_arn


def from_dict(value: dict) -> MarketplaceMetadataValueObject:
    product_code = _validate_required_fields(value)
    license_arn = _validate_optional_fields(value)
    return MarketplaceMetadataValueObject(
        productCode=product_code,
        subscriptionOwnership=value["subscriptionOwnership"],
        regionalAmiIds=value["regionalAmiIds"],
        licenseConfigurationArn=license_arn,
        homeRegion=value.get("homeRegion"),
        licenseGrantAllowed=value.get("licenseGrantAllowed", False),
    )
