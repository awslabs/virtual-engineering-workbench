from typing import Optional

from pydantic import Field

from app.packaging.domain.model.image.image_constants import SubscriptionOwnership
from app.packaging.domain.value_objects.image import (
    ami_id_value_object,
    image_name_value_object,
    image_source_value_object,
    os_version_value_object,
    platform_value_object,
    product_code_value_object,
)
from app.packaging.domain.value_objects.shared import project_id_value_object
from app.shared.adapters.message_bus import command_bus


class ImportImageCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    imageSource: image_source_value_object.ImageSourceValueObject
    amiId: ami_id_value_object.AmiIdValueObject
    imageName: image_name_value_object.ImageNameValueObject
    imageDescription: Optional[str] = None
    platform: platform_value_object.PlatformValueObject
    osVersion: os_version_value_object.OsVersionValueObject
    componentVersionDetails: list[dict] = Field(default_factory=list)
    marketplaceProductCode: Optional[product_code_value_object.ProductCodeValueObject] = None
    licenseConfigurationArn: Optional[str] = None
    subscriptionOwnership: Optional[SubscriptionOwnership] = None
    licenseGrantAllowed: bool = False
    regionalAmiIds: Optional[dict] = None
    homeRegion: Optional[str] = None
    imageServiceAccountId: Optional[str] = None
