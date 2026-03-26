from unittest import mock

import assertpy
import pytest

from app.packaging.domain.commands.component import (
    create_component_command,
    create_component_version_command,
    release_component_version_command,
    update_component_command,
    update_component_version_command,
)
from app.packaging.domain.commands.image import create_image_command
from app.packaging.domain.commands.pipeline import (
    create_pipeline_command,
    update_pipeline_command,
)
from app.packaging.domain.commands.recipe import (
    create_recipe_command,
    create_recipe_version_command,
    update_recipe_version_command,
)
from app.packaging.domain.model.component import component, component_version
from app.packaging.domain.model.image import image
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.model.recipe.recipe import RecipeArchitecture
from app.packaging.domain.model.shared import component_version_entry
from app.packaging.domain.value_objects.component import (
    component_description_value_object,
    component_id_value_object,
    component_name_value_object,
    component_system_configuration_value_object,
)
from app.packaging.domain.value_objects.component_version import (
    component_license_dashboard_url_value_object,
    component_software_vendor_value_object,
    component_software_version_notes_value_object,
    component_software_version_value_object,
    component_version_dependencies_value_object,
    component_version_description_value_object,
    component_version_id_value_object,
    component_version_release_type_value_object,
    component_version_yaml_definition_value_object,
)
from app.packaging.domain.value_objects.pipeline import (
    pipeline_build_instance_types_value_object,
    pipeline_description_value_object,
    pipeline_id_value_object,
    pipeline_name_value_object,
    pipeline_schedule_value_object,
)
from app.packaging.domain.value_objects.recipe import (
    recipe_description_value_object,
    recipe_id_value_object,
    recipe_name_value_object,
    recipe_system_configuration_value_object,
)
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_components_versions_value_object,
    recipe_version_description_value_object,
    recipe_version_id_value_object,
    recipe_version_integration_value_object,
    recipe_version_release_type_value_object,
    recipe_version_volume_size_value_object,
)
from app.packaging.domain.value_objects.shared import (
    project_id_value_object,
    user_id_value_object,
    user_role_value_object,
)
from app.packaging.entrypoints.api.model import api_model
from app.packaging.entrypoints.api.model.api_model import ComponentVersionEntry
from app.packaging.entrypoints.api.tests.conftest import GlobalVariables
from app.shared.middleware.authorization import VirtualWorkbenchRoles


def test_get_components_should_return_all_components(
    lambda_context, authenticated_event, mocked_dependencies, list_components
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = list_components()

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    response = api_model.GetComponentsResponse.parse_obj(body)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.components).is_not_none()
    assertpy.assert_that(len(response.components)).is_equal_to(2)


@pytest.mark.parametrize("global_param", ("true", "false", None))
def test_get_components_versions_should_return_all_components_versions(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    global_param,
    get_released_component_versions,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    parameters = {
        "arch": GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value[0],
        "os": GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value[0],
        "platform": GlobalVariables.TEST_COMPONENT_PLATFORM.value,
        "status": "CREATED",
    }
    if global_param is not None:
        parameters["global"] = global_param
    status_code, body = get_released_component_versions(parameters)

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    response = api_model.GetComponentsVersionsResponse.parse_obj(body)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.components_versions_summary).is_not_none()
    assertpy.assert_that(len(response.components_versions_summary)).is_equal_to(6)


@mock.patch(
    "app.packaging.domain.value_objects.component.component_id_value_object.random.choice",
    lambda chars: "1",
)
def test_create_component_command_should_succeed(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_create_component_cmd_handler,
    create_component,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    status_code, body = create_component()

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    mocked_create_component_cmd_handler.assert_called_once_with(
        create_component_command.CreateComponentCommand(
            projectId=project_id_value_object.from_str(GlobalVariables.TEST_PROJECT_ID.value),
            componentId=component_id_value_object.from_str("comp-11111111"),
            componentName=component_name_value_object.from_str(GlobalVariables.TEST_COMPONENT_NAME.value),
            componentDescription=component_description_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_DESCRIPTION.value
            ),
            componentSystemConfiguration=component_system_configuration_value_object.from_attrs(
                platform=GlobalVariables.TEST_COMPONENT_PLATFORM.value,
                supported_architectures=list(GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value),
                supported_os_versions=list(GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value),
            ),
            createdBy=user_id_value_object.from_str(GlobalVariables.TEST_CREATED_BY.value),
        )
    )


def test_archive_component_command_should_succeed(
    archive_component,
    create_component,
    mocked_dependencies,
    list_components,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    create_status_code, _ = create_component()
    list_status_code, list_body = list_components()
    component_id = list_body["components"][0]["componentId"]

    # ACT
    archive_status_code, _ = archive_component(
        component_id=component_id, project_id=GlobalVariables.TEST_PROJECT_ID.value
    )

    # ASSERT
    assertpy.assert_that(create_status_code).is_equal_to(200)
    assertpy.assert_that(list_status_code).is_equal_to(200)
    assertpy.assert_that(archive_status_code).is_equal_to(200)


def test_share_component_command_should_succeed(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_share_component_cmd_handler,
    create_component,
    list_components,
    share_component,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    create_status_code, create_body = create_component()
    list_status_code, list_body = list_components()
    component_id = list_body["components"][0]["componentId"]
    # ACT
    share_status_code, share_body = share_component(
        component_id=component_id,
        project_ids=["proj-2345", GlobalVariables.TEST_PROJECT_ID.value],
    )

    # ASSERT
    assertpy.assert_that(create_status_code).is_equal_to(200)
    assertpy.assert_that(list_status_code).is_equal_to(200)
    assertpy.assert_that(share_status_code).is_equal_to(200)


def test_get_component_should_return_a_specific_component(
    lambda_context, authenticated_event, mocked_dependencies, get_component
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    status_code, body = get_component(component_id=GlobalVariables.TEST_COMPONENT_ID.value)

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    response = api_model.GetComponentResponse.parse_obj(body)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.component).is_not_none()
    assertpy.assert_that(response.component).is_equal_to(
        api_model.Component(
            componentId=GlobalVariables.TEST_COMPONENT_ID.value,
            componentDescription=GlobalVariables.TEST_COMPONENT_DESCRIPTION.value,
            componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
            componentPlatform=GlobalVariables.TEST_COMPONENT_PLATFORM.value,
            componentSupportedArchitectures=list(GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value),
            componentSupportedOsVersions=list(GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value),
            status=component.ComponentStatus.Created,
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            createdBy=GlobalVariables.TEST_CREATED_BY.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
            lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        )
    )
    assertpy.assert_that(response.metadata).is_not_none()
    assertpy.assert_that(response.metadata).is_equal_to(
        api_model.ComponentMetadata(
            associatedProjects=[
                api_model.AssociatedProject(projectId="comp-0"),
                api_model.AssociatedProject(projectId="comp-1"),
            ]
        )
    )


def test_update_component_should_succeed(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_update_component_cmd_handler,
    update_component,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    # ACT
    status_code, body = update_component(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value,
        component_description="Updated Component Description",
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    mocked_update_component_cmd_handler.assert_called_once_with(
        update_component_command.UpdateComponentCommand(
            componentId=component_id_value_object.from_str(GlobalVariables.TEST_COMPONENT_ID.value),
            componentDescription=component_description_value_object.from_str("Updated Component Description"),
            lastUpdatedBy=user_id_value_object.from_str(GlobalVariables.TEST_CREATED_BY.value),
        )
    )


def test_create_component_version_should_succeed_if_dependencies_is_none_or_empty(
    lambda_context,
    authenticated_event,
    get_test_component_yaml_definition,
    mocked_dependencies,
    mocked_create_component_version_cmd_handler,
    create_component_version,
):
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = create_component_version(component_id=GlobalVariables.TEST_COMPONENT_ID.value)
    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    mocked_create_component_version_cmd_handler.assert_called_once_with(
        create_component_version_command.CreateComponentVersionCommand(
            componentId=component_id_value_object.from_str(GlobalVariables.TEST_COMPONENT_ID.value),
            componentVersionDescription=component_version_description_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_DESCRIPTION.value
            ),
            componentVersionDependencies=component_version_dependencies_value_object.from_list([]),
            componentVersionReleaseType=component_version_release_type_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_RELEASE_TYPE.value
            ),
            componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_YAML_DEFINITION.value
            ),
            softwareVendor=component_software_vendor_value_object.from_str(GlobalVariables.TEST_SOFTWARE_VENDOR.value),
            softwareVersion=component_software_version_value_object.from_str(
                GlobalVariables.TEST_SOFTWARE_VERSION.value
            ),
            createdBy=user_id_value_object.from_str(GlobalVariables.TEST_CREATED_BY.value),
        )
    )


def test_create_component_version_should_succeed(
    lambda_context,
    authenticated_event,
    get_test_component_yaml_definition,
    mocked_dependencies,
    mocked_create_component_version_cmd_handler,
    create_component_version,
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = create_component_version(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value,
        component_version_dependencies=[
            ComponentVersionEntry(
                componentId="comp-8675abc",
                componentName="component-8675abc",
                componentVersionId="vers-1234abcd",
                componentVersionName="2.0.0-rc1",
                order=2,
            ),
            ComponentVersionEntry(
                componentId="comp2-1234abc",
                componentName="component2-1234abc",
                componentVersionId="vers-1234abcd",
                componentVersionName="1.0.0",
                order=1,
            ),
        ],
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    mocked_create_component_version_cmd_handler.assert_called_once_with(
        create_component_version_command.CreateComponentVersionCommand(
            componentId=component_id_value_object.from_str(GlobalVariables.TEST_COMPONENT_ID.value),
            componentVersionDescription=component_version_description_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_DESCRIPTION.value
            ),
            componentVersionDependencies=component_version_dependencies_value_object.from_list(
                [
                    ComponentVersionEntry(
                        componentId="comp-8675abc",
                        componentName="component-8675abc",
                        componentVersionId="vers-1234abcd",
                        componentVersionName="2.0.0-rc1",
                        order=2,
                    ),
                    ComponentVersionEntry(
                        componentId="comp2-1234abc",
                        componentName="component2-1234abc",
                        componentVersionId="vers-1234abcd",
                        componentVersionName="1.0.0",
                        order=1,
                    ),
                ]
            ),
            componentVersionReleaseType=component_version_release_type_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_RELEASE_TYPE.value
            ),
            componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_YAML_DEFINITION.value
            ),
            softwareVendor=component_software_vendor_value_object.from_str(GlobalVariables.TEST_SOFTWARE_VENDOR.value),
            softwareVersion=component_software_version_value_object.from_str(
                GlobalVariables.TEST_SOFTWARE_VERSION.value
            ),
            createdBy=user_id_value_object.from_str(GlobalVariables.TEST_CREATED_BY.value),
        )
    )


def test_create_component_version_should_return_bad_request_if_invalid_component_version_definition(
    lambda_context, authenticated_event, mocked_dependencies, create_component_version
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = create_component_version(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value,
        component_version_yaml_definition="Invalid YAML",
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(400)
    assertpy.assert_that(body.get("message")).is_equal_to("Component version YAML definition is invalid.")


def test_get_component_versions_should_return_all_component_versions(
    lambda_context, authenticated_event, mocked_dependencies, get_component_versions
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = get_component_versions(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value,
    )

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    response = api_model.GetComponentVersionsResponse.parse_obj(body)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.component_versions).is_not_none()
    assertpy.assert_that(len(response.component_versions)).is_equal_to(2)


def test_get_component_version_should_return_a_specific_component_version(
    lambda_context, authenticated_event, mocked_dependencies, get_component_version
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = get_component_version(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value,
        version_id=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
    )

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    response = api_model.GetComponentVersionResponse.parse_obj(body)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.component_version).is_not_none()
    assertpy.assert_that(response.component_version).is_equal_to(
        api_model.ComponentVersion(
            componentId=GlobalVariables.TEST_COMPONENT_ID.value,
            componentVersionId=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
            componentVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
            componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
            componentVersionDescription=GlobalVariables.TEST_COMPONENT_VERSION_DESCRIPTION.value,
            componentPlatform=GlobalVariables.TEST_COMPONENT_PLATFORM.value,
            componentSupportedArchitectures=list(GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value),
            componentSupportedOsVersions=list(GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value),
            softwareVendor=GlobalVariables.TEST_SOFTWARE_VENDOR.value,
            softwareVersion=GlobalVariables.TEST_SOFTWARE_VERSION.value,
            licenseDashboard=GlobalVariables.TEST_COMPONENT_LICENSE_DASHBOARD.value,
            notes=GlobalVariables.TEST_COMPONENT_SOFTWARE_VERSION_NOTES.value,
            status=component_version.ComponentVersionStatus.Creating,
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            createdBy=GlobalVariables.TEST_CREATED_BY.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
            lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        )
    )
    assertpy.assert_that(response.yaml_definition).is_not_none()
    assertpy.assert_that(response.yaml_definition).is_equal_to({"example_key": "example_value"})
    assertpy.assert_that(response.yaml_definition_b64).is_equal_to("ZXhhbXBsZV9rZXk6IGV4YW1wbGVfdmFsdWU=")


def test_release_component_version_should_succeed(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_release_component_version_cmd_handler,
    release_component_version,
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = release_component_version(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value,
        version_id=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    mocked_release_component_version_cmd_handler.assert_called_once_with(
        release_component_version_command.ReleaseComponentVersionCommand(
            projectId=project_id_value_object.from_str(GlobalVariables.TEST_PROJECT_ID.value),
            componentId=component_id_value_object.from_str(GlobalVariables.TEST_COMPONENT_ID.value),
            componentVersionId=component_version_id_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_ID.value
            ),
            userRoles=[user_role_value_object.from_str(VirtualWorkbenchRoles.Admin)],
            lastUpdatedBy=user_id_value_object.from_str(GlobalVariables.TEST_CREATED_BY.value),
        )
    )


def test_update_component_version_should_succeed_without_dependencies(
    lambda_context,
    authenticated_event,
    get_test_component_yaml_definition,
    mocked_dependencies,
    mocked_update_component_version_cmd_handler,
    update_component_version,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = update_component_version(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value,
        version_id=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    mocked_update_component_version_cmd_handler.assert_called_once_with(
        update_component_version_command.UpdateComponentVersionCommand(
            componentId=component_id_value_object.from_str(GlobalVariables.TEST_COMPONENT_ID.value),
            componentVersionId=component_version_id_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_ID.value
            ),
            componentVersionDescription=component_version_description_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_DESCRIPTION.value
            ),
            componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_YAML_DEFINITION.value
            ),
            componentVersionDependencies=component_version_dependencies_value_object.from_list([]),
            softwareVendor=component_software_vendor_value_object.from_str(GlobalVariables.TEST_SOFTWARE_VENDOR.value),
            softwareVersion=component_software_version_value_object.from_str(
                GlobalVariables.TEST_SOFTWARE_VERSION.value
            ),
            licenseDashboard=component_license_dashboard_url_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_LICENSE_DASHBOARD.value
            ),
            notes=component_software_version_notes_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_SOFTWARE_VERSION_NOTES.value
            ),
            lastUpdatedBy=user_id_value_object.from_str(GlobalVariables.TEST_CREATED_BY.value),
        )
    )


def test_update_component_version_should_succeed(
    lambda_context,
    authenticated_event,
    get_test_component_yaml_definition,
    mocked_dependencies,
    mocked_update_component_version_cmd_handler,
    update_component_version,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = update_component_version(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value,
        version_id=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
        component_version_dependencies=[
            component_version_entry.ComponentVersionEntry(
                componentId="comp-8675abc",
                componentName="component-8675abc",
                componentVersionId="vers-1234abcd",
                componentVersionName="2.0.0-rc1",
                componentVersionType="HELPER",
                order=2,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp2-1234abc",
                componentName="component2-1234abc",
                componentVersionId="vers-1234abcd",
                componentVersionName="1.0.0",
                componentVersionType="HELPER",
                order=1,
            ),
        ],
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    mocked_update_component_version_cmd_handler.assert_called_once_with(
        update_component_version_command.UpdateComponentVersionCommand(
            componentId=component_id_value_object.from_str(GlobalVariables.TEST_COMPONENT_ID.value),
            componentVersionId=component_version_id_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_ID.value
            ),
            componentVersionDescription=component_version_description_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_DESCRIPTION.value
            ),
            componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_YAML_DEFINITION.value
            ),
            componentVersionDependencies=component_version_dependencies_value_object.from_list(
                [
                    ComponentVersionEntry(
                        componentId="comp-8675abc",
                        componentName="component-8675abc",
                        componentVersionId="vers-1234abcd",
                        componentVersionName="2.0.0-rc1",
                        componentVersionType="HELPER",
                        order=2,
                    ),
                    ComponentVersionEntry(
                        componentId="comp2-1234abc",
                        componentName="component2-1234abc",
                        componentVersionId="vers-1234abcd",
                        componentVersionName="1.0.0",
                        componentVersionType="HELPER",
                        order=1,
                    ),
                ]
            ),
            softwareVendor=component_software_vendor_value_object.from_str(GlobalVariables.TEST_SOFTWARE_VENDOR.value),
            softwareVersion=component_software_version_value_object.from_str(
                GlobalVariables.TEST_SOFTWARE_VERSION.value
            ),
            licenseDashboard=component_license_dashboard_url_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_LICENSE_DASHBOARD.value
            ),
            notes=component_software_version_notes_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_SOFTWARE_VERSION_NOTES.value
            ),
            lastUpdatedBy=user_id_value_object.from_str(GlobalVariables.TEST_CREATED_BY.value),
        )
    )


def test_update_component_version_should_should_return_bad_request_if_invalid_component_version_definition(
    lambda_context, authenticated_event, mocked_dependencies, update_component_version
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = update_component_version(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value,
        version_id=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
        component_version_yaml_definition="Invalid YAML",
    )
    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(400)
    assertpy.assert_that(body.get("message")).is_equal_to("Component version YAML definition is invalid.")


def test_get_component_version_test_executions_should_return_all_component_version_test_executions(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    get_component_version_test_executions,
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = get_component_version_test_executions(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value,
        version_id=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
    )

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    response = api_model.GetComponentVersionTestExecutionsResponse.parse_obj(body)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.component_version_test_execution_summaries).is_not_none()
    assertpy.assert_that(len(response.component_version_test_execution_summaries)).is_equal_to(2)


def test_get_component_version_test_execution_should_return_logs_url_for_a_specific_component_version_test_execution(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    get_component_version_test_execution_logs_url,
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = get_component_version_test_execution_logs_url(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value,
        version_id=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
        execution_id=GlobalVariables.TEST_TEST_EXECUTION_ID.value,
        instance_id=GlobalVariables.TEST_INSTANCE_ID.value,
    )

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    response = api_model.GetComponentVersionTestExecutionLogsUrlResponse.parse_obj(body)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.logs_url).is_not_none()
    assertpy.assert_that(response.logs_url).is_equal_to(GlobalVariables.TEST_S3_LOG_PRESIGNED_URL.value)


def test_retire_component_version_should_succeed(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_release_component_version_cmd_handler,
    retire_component_version,
):
    from app.packaging.entrypoints.api import handler

    # ARRANGE
    handler.dependencies = mocked_dependencies
    status_code, body = retire_component_version(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value,
        version_id=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)


# Recipe Tests
def test_create_recipe_command_should_succeed(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_create_recipe_cmd_handler,
    create_recipe,
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    status_code, body = create_recipe()

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    mocked_create_recipe_cmd_handler.assert_called_once_with(
        create_recipe_command.CreateRecipeCommand(
            projectId=project_id_value_object.from_str(GlobalVariables.TEST_PROJECT_ID.value),
            recipeName=recipe_name_value_object.from_str(GlobalVariables.TEST_RECIPE_NAME.value),
            recipeDescription=recipe_description_value_object.from_str(GlobalVariables.TEST_RECIPE_DESCRIPTION.value),
            recipeSystemConfiguration=recipe_system_configuration_value_object.from_attrs(
                platform=GlobalVariables.TEST_COMPONENT_PLATFORM.value,
                architecture=GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value[0],
                os_version=GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value[0],
            ),
            createdBy=user_id_value_object.from_str(GlobalVariables.TEST_CREATED_BY.value),
        )
    )


def test_create_recipe_command_should_fail(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_create_recipe_cmd_handler,
    create_recipe,
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = create_recipe(
        recipe_architecture="RISC-V",
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(400)
    assertpy.assert_that(body.get("message")).is_equal_to(
        str(f"Recipe architecture should be in {RecipeArchitecture.list()}.")
    )


def test_archive_recipe_command_should_succeed(
    archive_recipe,
    create_recipe,
    mocked_dependencies,
    list_recipes,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    create_status_code, _ = create_recipe()
    list_status_code, list_body = list_recipes()
    recipe_id = list_body["recipes"][0]["recipeId"]

    # ACT
    archive_status_code, _ = archive_recipe(project_id=GlobalVariables.TEST_PROJECT_ID.value, recipe_id=recipe_id)

    # ASSERT
    assertpy.assert_that(create_status_code).is_equal_to(200)
    assertpy.assert_that(list_status_code).is_equal_to(200)
    assertpy.assert_that(archive_status_code).is_equal_to(200)


def test_get_recipes_should_return_all_recipes(lambda_context, authenticated_event, mocked_dependencies, list_recipes):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = list_recipes()

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    response = api_model.GetRecipesResponse.parse_obj(body)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.recipes).is_not_none()
    assertpy.assert_that(len(response.recipes)).is_equal_to(2)


def test_get_recipe_should_return_a_specific_recipe(
    lambda_context, authenticated_event, mocked_dependencies, get_recipe
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    status_code, body = get_recipe(recipe_id=GlobalVariables.TEST_RECIPE_ID.value)

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    response = api_model.GetRecipeResponse.parse_obj(body)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.recipe).is_not_none()
    assertpy.assert_that(response.recipe).is_equal_to(
        api_model.Recipe(
            projectId=GlobalVariables.TEST_PROJECT_ID.value,
            recipeId=GlobalVariables.TEST_RECIPE_ID.value,
            recipeDescription=GlobalVariables.TEST_RECIPE_DESCRIPTION.value,
            recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
            recipePlatform=GlobalVariables.TEST_COMPONENT_PLATFORM.value,
            recipeArchitecture=GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value[0],
            recipeOsVersion=GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value[0],
            status=GlobalVariables.TEST_RECIPE_STATUS.value,
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            createdBy=GlobalVariables.TEST_CREATED_BY.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
            lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        )
    )


def test_create_recipe_version_should_succeed(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_create_recipe_version_cmd_handler,
    create_recipe_version,
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = create_recipe_version(
        recipe_id=GlobalVariables.TEST_RECIPE_ID.value,
        recipe_version_components_versions=[
            api_model.RecipeComponentVersion(
                componentId=GlobalVariables.TEST_COMPONENT_ID.value,
                componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
                componentVersionId=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
                componentVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
                componentVersionType=GlobalVariables.TEST_COMPONENT_VERSION_TYPE.value,
                order=1,
            )
        ],
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    mocked_create_recipe_version_cmd_handler.assert_called_once_with(
        create_recipe_version_command.CreateRecipeVersionCommand(
            projectId=project_id_value_object.from_str(GlobalVariables.TEST_PROJECT_ID.value),
            recipeId=recipe_id_value_object.from_str(GlobalVariables.TEST_RECIPE_ID.value),
            recipeVersionDescription=recipe_version_description_value_object.from_str(
                GlobalVariables.TEST_RECIPE_VERSION_DESCRIPTION.value
            ),
            recipeVersionReleaseType=recipe_version_release_type_value_object.from_str(
                GlobalVariables.TEST_RECIPE_VERSION_RELEASE_TYPE.value
            ),
            recipeComponentsVersions=recipe_version_components_versions_value_object.from_list(
                [
                    api_model.RecipeComponentVersion(
                        componentId=GlobalVariables.TEST_COMPONENT_ID.value,
                        componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
                        componentVersionId=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
                        componentVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
                        componentVersionType=GlobalVariables.TEST_COMPONENT_VERSION_TYPE.value,
                        order=1,
                    ),
                ]
            ),
            recipeVersionVolumeSize=recipe_version_volume_size_value_object.from_str(
                GlobalVariables.TEST_RECIPE_VERSION_VOLUME_SIZE.value
            ),
            recipeVersionIntegrations=recipe_version_integration_value_object.from_str_array([]),
            createdBy=user_id_value_object.from_str(GlobalVariables.TEST_CREATED_BY.value),
        )
    )


def test_get_recipe_versions_should_return_all_recipe_versions(
    lambda_context, authenticated_event, mocked_dependencies, list_recipe_versions
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    status_code, body = list_recipe_versions(
        recipe_id=GlobalVariables.TEST_RECIPE_ID.value,
    )

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    response = api_model.GetRecipeVersionsResponse.parse_obj(body)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.recipe_versions).is_not_none()
    assertpy.assert_that(len(response.recipe_versions)).is_equal_to(2)


def test_retire_recipe_version_should_succeed(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_release_recipe_version_cmd_handler,
    retire_recipe_version,
):
    from app.packaging.entrypoints.api import handler

    # ARRANGE
    handler.dependencies = mocked_dependencies
    status_code, body = retire_recipe_version(
        recipe_id=GlobalVariables.TEST_RECIPE_ID.value,
        version_id=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)


def test_get_recipe_version_should_return_a_specific_recipe_version(
    lambda_context, authenticated_event, mocked_dependencies, get_recipe_version
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = get_recipe_version(
        recipe_id=GlobalVariables.TEST_RECIPE_ID.value,
        version_id=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
    )

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    response = api_model.GetRecipeVersionResponse.parse_obj(body)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.recipe_version).is_not_none()
    assertpy.assert_that(response.recipe_version).is_equal_to(
        api_model.RecipeVersion(
            recipeId=GlobalVariables.TEST_RECIPE_ID.value,
            recipeVersionId=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
            recipeVersionName=GlobalVariables.TEST_RECIPE_VERSION_NAME.value,
            recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
            recipeVersionDescription=GlobalVariables.TEST_RECIPE_VERSION_DESCRIPTION.value,
            recipeComponentsVersions=[
                component_version_entry.ComponentVersionEntry(
                    componentId=GlobalVariables.TEST_COMPONENT_ID.value,
                    componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
                    componentVersionId=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
                    componentVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
                    componentVersionType=GlobalVariables.TEST_COMPONENT_VERSION_TYPE.value,
                    order=1,
                )
            ],
            recipeVersionIntegrations=[],
            parentImageUpstreamId=GlobalVariables.TEST_IMAGE_UPSTREAM_ID.value,
            recipeVersionVolumeSize=GlobalVariables.TEST_RECIPE_VERSION_VOLUME_SIZE.value,
            status=recipe_version.RecipeVersionStatus.Creating,
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            createdBy=GlobalVariables.TEST_CREATED_BY.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
            lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        )
    )


def test_update_recipe_version_should_succeed(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_update_recipe_version_cmd_handler,
    update_recipe_version,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = update_recipe_version(
        recipe_id=GlobalVariables.TEST_RECIPE_ID.value,
        recipe_version_id=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
        recipe_version_description="Second Updated Description",
        recipe_version_components_versions=[
            api_model.RecipeComponentVersion(
                componentId=GlobalVariables.TEST_COMPONENT_ID.value,
                componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
                componentVersionId=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
                componentVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
                componentVersionType=GlobalVariables.TEST_COMPONENT_VERSION_TYPE.value,
                order=1,
            )
        ],
    )
    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    expected_request_call = update_recipe_version_command.UpdateRecipeVersionCommand(
        projectId=project_id_value_object.from_str(GlobalVariables.TEST_PROJECT_ID.value),
        recipeId=recipe_id_value_object.from_str(GlobalVariables.TEST_RECIPE_ID.value),
        recipeVersionId=recipe_version_id_value_object.from_str(GlobalVariables.TEST_RECIPE_VERSION_ID.value),
        recipeVersionDescription=recipe_version_description_value_object.from_str("Second Updated Description"),
        recipeComponentsVersions=recipe_version_components_versions_value_object.from_list(
            [
                api_model.RecipeComponentVersion(
                    componentId=GlobalVariables.TEST_COMPONENT_ID.value,
                    componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
                    componentVersionId=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
                    componentVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
                    componentVersionType=GlobalVariables.TEST_COMPONENT_VERSION_TYPE.value,
                    order=1,
                ),
            ]
        ),
        recipeVersionVolumeSize=recipe_version_volume_size_value_object.from_str(
            GlobalVariables.TEST_RECIPE_VERSION_VOLUME_SIZE.value
        ),
        recipeVersionIntegrations=[],
        lastUpdatedBy=user_id_value_object.from_str(GlobalVariables.TEST_CREATED_BY.value),
    )
    mocked_update_recipe_version_cmd_handler.assert_called_once_with(expected_request_call)


def test_release_recipe_version_should_succeed(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_release_recipe_version_cmd_handler,
    release_recipe_version,
):
    from app.packaging.entrypoints.api import handler

    # ARRANGE
    handler.dependencies = mocked_dependencies
    status_code, body = release_recipe_version(
        recipe_id=GlobalVariables.TEST_RECIPE_ID.value,
        version_id=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)


def test_get_recipe_version_test_executions_should_return_all_recipe_version_test_executions(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    list_recipe_version_test_executions,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = list_recipe_version_test_executions(
        recipe_id=GlobalVariables.TEST_RECIPE_ID.value,
        version_id=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
    )
    response = api_model.GetRecipeVersionTestExecutionsResponse.parse_obj(body)
    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.recipe_version_test_execution_summaries).is_not_none()
    assertpy.assert_that(len(response.recipe_version_test_execution_summaries)).is_equal_to(2)


def test_get_recipe_version_test_execution_should_return_logs_url_of_a_specific_version_test_executions(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    get_recipe_version_test_execution_logs_url,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = get_recipe_version_test_execution_logs_url(
        recipe_id=GlobalVariables.TEST_RECIPE_ID.value,
        version_id=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
        execution_id=GlobalVariables.TEST_RECIPE_VERSION_TEST_EXECUTION_ID.value,
    )
    response = api_model.GetRecipeVersionTestExecutionLogsUrlResponse.parse_obj(body)
    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.logs_url).is_not_none()
    assertpy.assert_that(response.logs_url).is_equal_to(GlobalVariables.TEST_S3_LOG_PRESIGNED_URL.value)


def test_get_mandatory_components_list_should_return_list(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    get_mandatory_component_list,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = get_mandatory_component_list()
    response = api_model.GetMandatoryComponentsListResponse.parse_obj(body)

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.mandatoryComponentsList).is_not_none()
    assertpy.assert_that(response.mandatoryComponentsList.mandatoryComponentsListArchitecture).is_equal_to(
        GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value[0]
    )
    assertpy.assert_that(response.mandatoryComponentsList.mandatoryComponentsListOsVersion).is_equal_to(
        GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value[0]
    )
    assertpy.assert_that(response.mandatoryComponentsList.mandatoryComponentsListPlatform).is_equal_to(
        GlobalVariables.TEST_COMPONENT_PLATFORM.value
    )
    # Check prepended components (old mandatory_components_versions are converted to prepended)
    assertpy.assert_that(len(response.mandatoryComponentsList.prependedComponentsVersions)).is_equal_to(
        GlobalVariables.TEST_MANDATORY_COMPONENTS_LIST_LENGTH.value
    )
    for i in range(GlobalVariables.TEST_MANDATORY_COMPONENTS_LIST_LENGTH.value):
        assertpy.assert_that(response.mandatoryComponentsList.prependedComponentsVersions[i].componentId).is_equal_to(
            f"comp-{i + 1}"
        )
        assertpy.assert_that(
            response.mandatoryComponentsList.prependedComponentsVersions[i].componentVersionId
        ).is_equal_to(f"vers-{i + 1}")
        assertpy.assert_that(response.mandatoryComponentsList.prependedComponentsVersions[i].componentName).is_equal_to(
            f"test-component-{i + 1}"
        )
        assertpy.assert_that(
            response.mandatoryComponentsList.prependedComponentsVersions[i].componentVersionName
        ).is_equal_to(GlobalVariables.TEST_COMPONENT_VERSION_NAME.value)
        assertpy.assert_that(response.mandatoryComponentsList.prependedComponentsVersions[i].order).is_equal_to(i + 1)


def test_create_mandatory_components_list_should_create_list(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    create_mandatory_components_list,
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = create_mandatory_components_list(
        mandatory_components_versions=[
            api_model.ComponentVersionEntry(
                componentId=GlobalVariables.TEST_COMPONENT_ID.value,
                componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
                componentVersionId=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
                componentVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
                order=1,
            )
        ],
    )

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)


def test_update_mandatory_components_list_should_update_list(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    update_mandatory_components_list,
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = update_mandatory_components_list(
        mandatory_components_versions=[
            api_model.ComponentVersionEntry(
                componentId=GlobalVariables.TEST_COMPONENT_ID.value,
                componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
                componentVersionId=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
                componentVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
                order=1,
            )
        ]
    )
    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)


def test_get_mandatory_components_lists_should_return_all_lists(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    list_mandatory_components_list,
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = list_mandatory_components_list()
    response = api_model.GetMandatoryComponentsListsResponse.parse_obj(body)

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)
    assertpy.assert_that(response.mandatoryComponentsLists).is_not_none()
    assertpy.assert_that(len(response.mandatoryComponentsLists)).is_equal_to(2)

    assertpy.assert_that(response.mandatoryComponentsLists[0].mandatoryComponentsListPlatform).is_equal_to("Linux")
    assertpy.assert_that(response.mandatoryComponentsLists[0].mandatoryComponentsListOsVersion).is_equal_to("Ubuntu 24")
    assertpy.assert_that(response.mandatoryComponentsLists[0].mandatoryComponentsListArchitecture).is_equal_to("amd64")
    assertpy.assert_that(response.mandatoryComponentsLists[1].mandatoryComponentsListPlatform).is_equal_to("Windows")
    assertpy.assert_that(response.mandatoryComponentsLists[1].mandatoryComponentsListOsVersion).is_equal_to(
        "Microsoft Windows Server 2025"
    )
    assertpy.assert_that(response.mandatoryComponentsLists[1].mandatoryComponentsListArchitecture).is_equal_to("amd64")
    for i in range(2):
        for j in range(GlobalVariables.TEST_MANDATORY_COMPONENTS_LIST_LENGTH.value):
            assertpy.assert_that(
                response.mandatoryComponentsLists[i].prependedComponentsVersions[j].componentId
            ).is_equal_to(f"comp-{j + 1}")
            assertpy.assert_that(
                response.mandatoryComponentsLists[i].prependedComponentsVersions[j].componentName
            ).is_equal_to(f"test-component-{j + 1}")
            assertpy.assert_that(
                response.mandatoryComponentsLists[i].prependedComponentsVersions[j].componentVersionId
            ).is_equal_to(f"vers-{j + 1}")
            assertpy.assert_that(
                response.mandatoryComponentsLists[i].prependedComponentsVersions[j].componentVersionName
            ).is_equal_to("1.0.0")
            assertpy.assert_that(response.mandatoryComponentsLists[i].prependedComponentsVersions[j].order).is_equal_to(
                j + 1
            )


def test_create_pipeline_command_should_succeed(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_create_pipeline_cmd_handler,
    create_pipeline,
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    status_code, body = create_pipeline(
        recipe_id=GlobalVariables.TEST_RECIPE_ID.value,
        recipe_version_id=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    mocked_create_pipeline_cmd_handler.assert_called_once_with(
        create_pipeline_command.CreatePipelineCommand(
            projectId=project_id_value_object.from_str(GlobalVariables.TEST_PROJECT_ID.value),
            buildInstanceTypes=pipeline_build_instance_types_value_object.from_list(
                list(GlobalVariables.TEST_PIPELINE_BUILD_INSTANCE_TYPES.value)
            ),
            pipelineDescription=pipeline_description_value_object.from_str(
                GlobalVariables.TEST_PIPELINE_DESCRIPTION.value
            ),
            pipelineName=pipeline_name_value_object.from_str(GlobalVariables.TEST_PIPELINE_NAME.value),
            pipelineSchedule=pipeline_schedule_value_object.from_str(GlobalVariables.TEST_PIPELINE_SCHEDULE.value),
            recipeId=recipe_id_value_object.from_str(GlobalVariables.TEST_RECIPE_ID.value),
            recipeVersionId=recipe_version_id_value_object.from_str(GlobalVariables.TEST_RECIPE_VERSION_ID.value),
            createdBy=user_id_value_object.from_str(GlobalVariables.TEST_CREATED_BY.value),
        )
    )


def test_get_pipelines_should_return_all_pipelines(
    lambda_context, authenticated_event, mocked_dependencies, list_pipelines
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = list_pipelines()

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    response = api_model.GetPipelinesResponse.parse_obj(body)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.pipelines).is_not_none()
    assertpy.assert_that(len(response.pipelines)).is_equal_to(2)


def test_get_pipeline_should_return_a_specific_pipeline(
    lambda_context, authenticated_event, mocked_dependencies, get_pipeline
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = get_pipeline(pipeline_id=GlobalVariables.TEST_PIPELINE_ID.value)

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    response = api_model.GetPipelineResponse.parse_obj(body)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.pipeline).is_not_none()
    assertpy.assert_that(response.pipeline).is_equal_to(
        api_model.Pipeline(
            projectId=GlobalVariables.TEST_PROJECT_ID.value,
            pipelineId=GlobalVariables.TEST_PIPELINE_ID.value,
            buildInstanceTypes=list(GlobalVariables.TEST_PIPELINE_BUILD_INSTANCE_TYPES.value),
            pipelineDescription=GlobalVariables.TEST_PIPELINE_DESCRIPTION.value,
            pipelineName=GlobalVariables.TEST_PIPELINE_NAME.value,
            pipelineSchedule=GlobalVariables.TEST_PIPELINE_SCHEDULE.value,
            recipeId=GlobalVariables.TEST_RECIPE_ID.value,
            recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
            recipeVersionId=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
            recipeVersionName=GlobalVariables.TEST_RECIPE_VERSION_NAME.value,
            status=pipeline.PipelineStatus.Created,
            distributionConfigArn=GlobalVariables.TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN.value,
            infrastructureConfigArn=GlobalVariables.TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN.value,
            pipelineArn=GlobalVariables.TEST_PIPELINE_PIPELINE_ARN.value,
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            createdBy=GlobalVariables.TEST_CREATED_BY.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
            lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATED_BY.value,
        )
    )


def test_retire_pipeline_command_should_succeed(
    lambda_context, authenticated_event, mocked_dependencies, retire_pipeline
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = retire_pipeline(pipeline_id=GlobalVariables.TEST_PIPELINE_ID.value)

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)


def test_update_pipeline_command_should_succeed_with_all_fields(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_update_pipeline_cmd_handler,
    update_pipeline,
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = update_pipeline(
        pipeline_id=GlobalVariables.TEST_PIPELINE_ID.value,
        build_instance_types=GlobalVariables.TEST_PIPELINE_BUILD_INSTANCE_TYPES.value,
        recipe_version_id=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
        pipeline_schedule=GlobalVariables.TEST_PIPELINE_SCHEDULE.value,
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    mocked_update_pipeline_cmd_handler.assert_called_once_with(
        update_pipeline_command.UpdatePipelineCommand(
            projectId=project_id_value_object.from_str(GlobalVariables.TEST_PROJECT_ID.value),
            buildInstanceTypes=pipeline_build_instance_types_value_object.from_list(
                list(GlobalVariables.TEST_PIPELINE_BUILD_INSTANCE_TYPES.value)
            ),
            pipelineId=pipeline_id_value_object.from_str(GlobalVariables.TEST_PIPELINE_ID.value),
            pipelineSchedule=pipeline_schedule_value_object.from_str(GlobalVariables.TEST_PIPELINE_SCHEDULE.value),
            recipeVersionId=recipe_version_id_value_object.from_str(GlobalVariables.TEST_RECIPE_VERSION_ID.value),
            lastUpdatedBy=user_id_value_object.from_str(GlobalVariables.TEST_LAST_UPDATED_BY.value),
        )
    )


def test_update_pipeline_command_should_succeed_with_recipe_version_update_only(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_update_pipeline_cmd_handler,
    update_pipeline,
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = update_pipeline(
        pipeline_id=GlobalVariables.TEST_PIPELINE_ID.value,
        recipe_version_id=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    mocked_update_pipeline_cmd_handler.assert_called_once_with(
        update_pipeline_command.UpdatePipelineCommand(
            projectId=project_id_value_object.from_str(GlobalVariables.TEST_PROJECT_ID.value),
            pipelineId=pipeline_id_value_object.from_str(GlobalVariables.TEST_PIPELINE_ID.value),
            recipeVersionId=recipe_version_id_value_object.from_str(GlobalVariables.TEST_RECIPE_VERSION_ID.value),
            lastUpdatedBy=user_id_value_object.from_str(GlobalVariables.TEST_LAST_UPDATED_BY.value),
        )
    )


def test_update_pipeline_command_should_succeed_with_instance_type_update_only(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_update_pipeline_cmd_handler,
    update_pipeline,
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = update_pipeline(
        pipeline_id=GlobalVariables.TEST_PIPELINE_ID.value,
        build_instance_types=list(GlobalVariables.TEST_PIPELINE_BUILD_INSTANCE_TYPES.value),
    )
    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    mocked_update_pipeline_cmd_handler.assert_called_once_with(
        update_pipeline_command.UpdatePipelineCommand(
            projectId=project_id_value_object.from_str(GlobalVariables.TEST_PROJECT_ID.value),
            buildInstanceTypes=pipeline_build_instance_types_value_object.from_list(
                list(GlobalVariables.TEST_PIPELINE_BUILD_INSTANCE_TYPES.value)
            ),
            pipelineId=pipeline_id_value_object.from_str(GlobalVariables.TEST_PIPELINE_ID.value),
            lastUpdatedBy=user_id_value_object.from_str(GlobalVariables.TEST_LAST_UPDATED_BY.value),
        )
    )


def test_update_pipeline_command_should_succeed_with_schedule_update_only(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_update_pipeline_cmd_handler,
    update_pipeline,
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = update_pipeline(
        pipeline_id=GlobalVariables.TEST_PIPELINE_ID.value,
        pipeline_schedule=GlobalVariables.TEST_PIPELINE_SCHEDULE.value,
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    mocked_update_pipeline_cmd_handler.assert_called_once_with(
        update_pipeline_command.UpdatePipelineCommand(
            projectId=project_id_value_object.from_str(GlobalVariables.TEST_PROJECT_ID.value),
            pipelineSchedule=pipeline_schedule_value_object.from_str(GlobalVariables.TEST_PIPELINE_SCHEDULE.value),
            pipelineId=pipeline_id_value_object.from_str(GlobalVariables.TEST_PIPELINE_ID.value),
            lastUpdatedBy=user_id_value_object.from_str(GlobalVariables.TEST_LAST_UPDATED_BY.value),
        )
    )


def test_create_image_should_succeed(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_create_image_cmd_handler,
    create_image,
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = create_image(pipeline_id=GlobalVariables.TEST_PIPELINE_ID.value)

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    mocked_create_image_cmd_handler.assert_called_once_with(
        create_image_command.CreateImageCommand(
            projectId=project_id_value_object.from_str(GlobalVariables.TEST_PROJECT_ID.value),
            pipelineId=pipeline_id_value_object.from_str(GlobalVariables.TEST_PIPELINE_ID.value),
        )
    )


def test_get_swagger_json(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    minimal_event = authenticated_event(None, "/_swagger", "GET", query_params={"format": "json"})

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)


def test_get_recipes_versions_should_return_all_recipes_versions(
    lambda_context, authenticated_event, mocked_dependencies, list_recipes_versions
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = list_recipes_versions(
        recipe_id=GlobalVariables.TEST_RECIPE_ID.value,
    )

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    response = api_model.GetRecipesVersionsResponse.parse_obj(body)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.recipes_versions_summary).is_not_none()
    assertpy.assert_that(len(response.recipes_versions_summary)).is_equal_to(6)


def test_get_all_images_for_project(lambda_context, authenticated_event, mocked_dependencies, list_images):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = list_images()

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    response = api_model.GetImagesResponse.parse_obj(body)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.images).is_not_none()
    assertpy.assert_that(response.images[0]).is_equal_to(
        api_model.Image(
            projectId=GlobalVariables.TEST_PROJECT_ID.value,
            imageId=GlobalVariables.TEST_IMAGE_ID.value,
            imageBuildVersion=GlobalVariables.TEST_IMAGE_BUILD_VERSION.value,
            imageBuildVersionArn=GlobalVariables.TEST_IMAGE_BUILD_VERSION_ARN.value,
            pipelineId=GlobalVariables.TEST_PIPELINE_ID.value,
            pipelineName=GlobalVariables.TEST_PIPELINE_NAME.value,
            recipeId=GlobalVariables.TEST_RECIPE_ID.value,
            recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
            recipeVersionId=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
            recipeVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
            status=image.ImageStatus.Created,
            imageUpstreamId=GlobalVariables.TEST_IMAGE_UPSTREAM_ID.value,
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        )
    )


def test_get_image_for_project(lambda_context, authenticated_event, mocked_dependencies, get_image):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = get_image(
        image_id=GlobalVariables.TEST_IMAGE_ID.value,
    )

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    response = api_model.GetImageResponse.parse_obj(body)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.image).is_not_none()
    assertpy.assert_that(response.image).is_equal_to(
        api_model.Image(
            projectId=GlobalVariables.TEST_PROJECT_ID.value,
            imageId=GlobalVariables.TEST_IMAGE_ID.value,
            imageBuildVersion=GlobalVariables.TEST_IMAGE_BUILD_VERSION.value,
            imageBuildVersionArn=GlobalVariables.TEST_IMAGE_BUILD_VERSION_ARN.value,
            pipelineId=GlobalVariables.TEST_PIPELINE_ID.value,
            pipelineName=GlobalVariables.TEST_PIPELINE_NAME.value,
            recipeId=GlobalVariables.TEST_RECIPE_ID.value,
            recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
            recipeVersionId=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
            recipeVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
            status=image.ImageStatus.Created,
            imageUpstreamId=GlobalVariables.TEST_IMAGE_UPSTREAM_ID.value,
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        )
    )


def test_get_pipelines_allowed_build_types(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    get_pipelines_allowed_build_types,
):
    # ARRANGE & ACT
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = get_pipelines_allowed_build_types()

    # ASSERT
    assertpy.assert_that(body).is_not_none()
    assertpy.assert_that(status_code).is_equal_to(200)

    response = api_model.GetPipelinesAllowedBuildTypesResponse.parse_obj(body)

    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.pipelines_allowed_build_types).is_not_none()
    assertpy.assert_that(response.pipelines_allowed_build_types).is_equal_to(
        list(GlobalVariables.TEST_PIPELINE_ALLOWED_BUILD_INSTANCE_TYPES.value)
    )


@pytest.mark.parametrize(
    "optional_fields",
    [
        {"licenseDashboard": None},
        {"notes": None},
    ],
)
def test_create_component_version_should_succeed_if_license_and_notes_is_not_empty(
    lambda_context,
    authenticated_event,
    get_test_component_yaml_definition,
    mocked_dependencies,
    mocked_create_component_version_cmd_handler,
    create_component_version,
    optional_fields,
):
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = create_component_version(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value,
        optional_fields=optional_fields,
    )
    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    mocked_create_component_version_cmd_handler.assert_called_once_with(
        create_component_version_command.CreateComponentVersionCommand(
            componentId=component_id_value_object.from_str(GlobalVariables.TEST_COMPONENT_ID.value),
            componentVersionDescription=component_version_description_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_DESCRIPTION.value
            ),
            componentVersionDependencies=component_version_dependencies_value_object.from_list([]),
            componentVersionReleaseType=component_version_release_type_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_RELEASE_TYPE.value
            ),
            componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_YAML_DEFINITION.value
            ),
            softwareVendor=component_software_vendor_value_object.from_str(GlobalVariables.TEST_SOFTWARE_VENDOR.value),
            softwareVersion=component_software_version_value_object.from_str(
                GlobalVariables.TEST_SOFTWARE_VERSION.value
            ),
            createdBy=user_id_value_object.from_str(GlobalVariables.TEST_CREATED_BY.value),
        )
    )


@pytest.mark.parametrize(
    "optional_fields",
    [
        {
            "licenseDashboard": GlobalVariables.TEST_COMPONENT_LICENSE_DASHBOARD.value,
            "notes": None,
        },
        {
            "notes": GlobalVariables.TEST_COMPONENT_SOFTWARE_VERSION_NOTES.value,
            "licenseDashboard": None,
        },
        {"notes": None, "licenseDashboard": None},
    ],
)
def test_create_component_version_should_succeed_if_license_or_notes_is_empty_and_if_both_empty(
    lambda_context,
    authenticated_event,
    get_test_component_yaml_definition,
    mocked_dependencies,
    mocked_create_component_version_cmd_handler,
    create_component_version,
    optional_fields,
):
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    status_code, body = create_component_version(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value,
        optional_fields=optional_fields,
    )
    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)
    mocked_create_component_version_cmd_handler.assert_called_once_with(
        create_component_version_command.CreateComponentVersionCommand(
            componentId=component_id_value_object.from_str(GlobalVariables.TEST_COMPONENT_ID.value),
            componentVersionDescription=component_version_description_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_DESCRIPTION.value
            ),
            componentVersionDependencies=component_version_dependencies_value_object.from_list([]),
            componentVersionReleaseType=component_version_release_type_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_RELEASE_TYPE.value
            ),
            componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
                GlobalVariables.TEST_COMPONENT_VERSION_YAML_DEFINITION.value
            ),
            softwareVendor=component_software_vendor_value_object.from_str(GlobalVariables.TEST_SOFTWARE_VENDOR.value),
            softwareVersion=component_software_version_value_object.from_str(
                GlobalVariables.TEST_SOFTWARE_VERSION.value
            ),
            licenseDashboard=(
                component_license_dashboard_url_value_object.from_str(
                    GlobalVariables.TEST_COMPONENT_LICENSE_DASHBOARD.value
                )
                if optional_fields.get("licenseDashboard")
                else None
            ),
            notes=(
                component_software_version_notes_value_object.from_str(
                    GlobalVariables.TEST_COMPONENT_SOFTWARE_VERSION_NOTES.value
                )
                if optional_fields.get("notes")
                else None
            ),
            createdBy=user_id_value_object.from_str(GlobalVariables.TEST_CREATED_BY.value),
        )
    )
