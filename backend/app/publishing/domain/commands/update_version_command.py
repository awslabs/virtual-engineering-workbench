from typing import Optional

from app.publishing.domain.value_objects import (
    ami_id_value_object,
    image_digest_value_object,
    image_tag_value_object,
    product_id_value_object,
    project_id_value_object,
    user_id_value_object,
    version_description_value_object,
    version_id_value_object,
    version_template_definition_value_object,
)
from app.shared.adapters.message_bus import command_bus


class UpdateVersionCommand(command_bus.Command):
    amiId: Optional[ami_id_value_object.AmiIdValueObject] = None
    imageTag: Optional[image_tag_value_object.ImageTagValueObject] = None
    imageDigest: Optional[image_digest_value_object.ImageDigestValueObject] = None
    versionDescription: version_description_value_object.VersionDescriptionValueObject
    versionTemplateDefinition: version_template_definition_value_object.VersionTemplateDefinitionValueObject
    projectId: project_id_value_object.ProjectIdValueObject
    productId: product_id_value_object.ProductIdValueObject
    versionId: version_id_value_object.VersionIdValueObject
    lastUpdatedBy: user_id_value_object.UserIdValueObject
