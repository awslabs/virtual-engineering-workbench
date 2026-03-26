from typing import Optional

from pydantic import Field

from app.publishing.domain.value_objects import (
    ami_id_value_object,
    image_digest_value_object,
    image_tag_value_object,
    major_version_name_value_object,
    product_id_value_object,
    project_id_value_object,
    user_id_value_object,
    version_description_value_object,
    version_release_type_value_object,
    version_template_definition_value_object,
)
from app.shared.adapters.message_bus import command_bus


class CreateVersionCommand(command_bus.Command):
    amiId: Optional[ami_id_value_object.AmiIdValueObject]
    imageTag: Optional[image_tag_value_object.ImageTagValueObject]
    imageDigest: Optional[image_digest_value_object.ImageDigestValueObject]
    majorVersionName: Optional[major_version_name_value_object.MajorVersionNameValueObject] = Field(None)
    versionReleaseType: version_release_type_value_object.VersionReleaseTypeValueObject
    versionDescription: version_description_value_object.VersionDescriptionValueObject
    versionTemplateDefinition: version_template_definition_value_object.VersionTemplateDefinitionValueObject
    projectId: project_id_value_object.ProjectIdValueObject
    productId: product_id_value_object.ProductIdValueObject
    createdBy: user_id_value_object.UserIdValueObject
