from typing import Optional

from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import (
    component_license_dashboard_url_value_object,
    component_software_vendor_value_object,
    component_software_version_notes_value_object,
    component_software_version_value_object,
    component_version_dependencies_value_object,
    component_version_description_value_object,
    component_version_id_value_object,
    component_version_yaml_definition_value_object,
)
from app.packaging.domain.value_objects.shared import user_id_value_object
from app.shared.adapters.message_bus import command_bus


class UpdateComponentVersionCommand(command_bus.Command):
    componentId: component_id_value_object.ComponentIdValueObject
    componentVersionId: component_version_id_value_object.ComponentVersionIdValueObject
    componentVersionDescription: component_version_description_value_object.ComponentVersionDescriptionValueObject
    componentVersionYamlDefinition: (
        component_version_yaml_definition_value_object.ComponentVersionYamlDefinitionValueObject
    )
    componentVersionDependencies: component_version_dependencies_value_object.ComponentVersionDependenciesValueObject
    softwareVendor: component_software_vendor_value_object.ComponentSoftwareVendorValueObject
    softwareVersion: component_software_version_value_object.ComponentSoftwareVersionValueObject
    licenseDashboard: Optional[component_license_dashboard_url_value_object.ComponentLicenseDashboardUrlValueObject]
    notes: Optional[component_software_version_notes_value_object.ComponentSoftwareVersionNotesValueObject]
    lastUpdatedBy: user_id_value_object.UserIdValueObject
