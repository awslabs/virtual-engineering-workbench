from app.publishing.domain.value_objects import (
    product_id_value_object,
    project_id_value_object,
    version_template_definition_value_object,
)
from app.shared.adapters.message_bus import command_bus


class ValidateVersionCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    productId: product_id_value_object.ProductIdValueObject
    versionTemplateDefinition: version_template_definition_value_object.VersionTemplateDefinitionValueObject
