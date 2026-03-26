import json
from unittest import mock

import assertpy
import botocore
import pytest

from app.packaging.entrypoints.api.model import api_model
from app.packaging.entrypoints.api.tests.conftest import GlobalVariables


@mock.patch(
    "app.packaging.domain.value_objects.component.component_id_value_object.random.choice",
    lambda chars: "1",
)
def test_create_and_list_components_should_return_http_200(
    authenticated_event, lambda_context, create_component, list_components
):
    # ARRANGE & ACT
    create_status_code, create_body = create_component()
    list_status_code, list_body = list_components()

    # ASSERT

    assertpy.assert_that(api_model.CreateComponentResponse.parse_obj(json.loads(create_body)).componentId).is_equal_to(
        "comp-11111111"
    )
    assertpy.assert_that(create_status_code).is_equal_to(200)
    assertpy.assert_that(list_status_code).is_equal_to(200)
    assertpy.assert_that(len(list_body)).is_equal_to(1)


def test_validate_create_list_and_delete_component_versions_should_return_http_200(
    authenticated_event,
    lambda_context,
    create_component,
    create_component_version,
    validate_component_version,
    list_components,
    get_component_versions,
    delete_component_version,
    backend_app_dynamodb_table,
):
    # ARRANGE
    create_status_code, create_body = create_component()
    list_status_code, list_body = list_components()
    component_id = list_body.get("components")[0].get("componentId")
    validate_status_code, validate_body = validate_component_version(component_id)
    create_component_version_status_code, create_component_version_body = create_component_version(component_id)
    get_component_version_status_code, get_component_version_body = get_component_versions(component_id)
    component_version_id = get_component_version_body.get("component_versions")[0].get("componentVersionId")
    backend_app_dynamodb_table.update_item(
        Key={
            "PK": f"COMPONENT#{component_id}",
            "SK": f"VERSION#{component_version_id}",
        },
        AttributeUpdates={
            "status": {"Value": "VALIDATED"},
            "componentBuildVersionArn": {
                "Value": (
                    f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}"
                    f":{GlobalVariables.TEST_AWS_ACCOUNT_ID.value}:component/"
                    f"{component_id}/{component_version_id}"
                )
            },
        },
    )
    delete_component_version_status, delete_component_version_body = delete_component_version(
        component_id, component_version_id
    )

    # ASSERT
    assertpy.assert_that(create_status_code).is_equal_to(200)
    assertpy.assert_that(list_status_code).is_equal_to(200)
    assertpy.assert_that(len(list_body)).is_equal_to(1)
    assertpy.assert_that(create_component_version_status_code).is_equal_to(200)
    assertpy.assert_that(create_component_version_status_code).is_equal_to(200)
    assertpy.assert_that(get_component_version_status_code).is_equal_to(200)
    assertpy.assert_that(len(get_component_version_body)).is_equal_to(1)
    assertpy.assert_that(delete_component_version_status).is_equal_to(200)


@pytest.mark.parametrize("global_parameter_value,expected_length", (("true", 2), ("false", 1), (None, 1)))
def test_create_and_list_components_versions_should_succeed(
    authenticated_event,
    lambda_context,
    global_parameter_value,
    expected_length,
    create_component,
    list_components,
    create_component_version,
    get_released_component_versions,
):
    for _project_id in [GlobalVariables.TEST_PROJECT_ID.value, "proj-67890"]:
        create_component(project_id=_project_id)
        list_status_code, list_body = list_components(project_id=_project_id)
        component_id = list_body.get("components")[0].get("componentId")
        create_component_version(project_id=_project_id, component_id=component_id)
    parameters = {
        "status": "CREATING",
        "os": GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value[0],
        "platform": GlobalVariables.TEST_COMPONENT_PLATFORM.value,
        "arch": GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value[0],
    }
    if global_parameter_value is not None:
        parameters["global"] = global_parameter_value
    (
        get_released_component_versions_status_code,
        get_released_component_versions_body,
    ) = get_released_component_versions(parameters=parameters)

    assertpy.assert_that(get_released_component_versions_status_code).is_equal_to(200)
    assertpy.assert_that(get_released_component_versions_body).is_not_none()
    assertpy.assert_that(len(get_released_component_versions_body.get("components_versions_summary"))).is_equal_to(
        expected_length
    )


def test_create_and_list_recipes_should_return_http_200(
    authenticated_event, lambda_context, create_recipe, list_recipes
):
    # ARRANGE & ACT
    create_recipe_status_code, create_recipe_body = create_recipe()
    list_recipes_status_code, list_recipes_body = list_recipes()

    # ASSERT
    assertpy.assert_that(create_recipe_status_code).is_equal_to(200)
    assertpy.assert_that(list_recipes_status_code).is_equal_to(200)
    assertpy.assert_that(len(list_recipes_body)).is_equal_to(1)


def test_create_list_update_and_delete_recipe_versions_should_return_http_200(
    authenticated_event,
    lambda_context,
    backend_app_dynamodb_table,
    create_component,
    list_components,
    create_component_version,
    get_component_versions,
    create_recipe,
    list_recipes,
    create_recipe_version,
    list_recipe_versions,
    delete_recipe_version,
):
    # ARRANGE
    create_status_code, create_body = create_component()
    list_status_code, list_body = list_components()
    component_id = list_body.get("components")[0].get("componentId")
    create_component_version_status_code, create_component_version_body = create_component_version(component_id)
    get_component_version_status_code, get_component_version_body = get_component_versions(component_id)
    component_version_id = get_component_version_body.get("component_versions")[0].get("componentVersionId")
    backend_app_dynamodb_table.update_item(
        Key={
            "PK": f"COMPONENT#{component_id}",
            "SK": f"VERSION#{component_version_id}",
        },
        AttributeUpdates={
            "status": {"Value": "VALIDATED"},
            "componentBuildVersionArn": {
                "Value": (
                    f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}"
                    f":{GlobalVariables.TEST_AWS_ACCOUNT_ID.value}:"
                    f"component/{component_id}/{component_version_id}"
                )
            },
        },
    )

    create_recipe_status_code, create_recipe_body = create_recipe()
    list_recipes_status_code, list_recipes_body = list_recipes()
    recipe_id = list_recipes_body.get("recipes")[0].get("recipeId")
    create_recipe_version_status_code, create_recipe_version_body = create_recipe_version(
        recipe_id=recipe_id,
        recipe_version_components_versions=[
            api_model.RecipeComponentVersion(
                componentId=component_id,
                componentName="component-12345",
                componentVersionId=component_version_id,
                componentVersionName="1.0.0",
                componentVersionType="MAIN",
                order=1,
            ),
        ],
    )

    list_recipe_versions_status_code, list_recipe_versions_body = list_recipe_versions(recipe_id=recipe_id)
    recipe_version_id = list_recipe_versions_body.get("recipe_versions")[0].get("recipeVersionId")

    # ACT
    backend_app_dynamodb_table.update_item(
        Key={
            "PK": f"RECIPE#{recipe_id}",
            "SK": f"VERSION#{recipe_version_id}",
        },
        AttributeUpdates={
            "status": {"Value": "VALIDATED"},
            "recipeVersionArn": {
                "Value": (
                    f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}"
                    f":{GlobalVariables.TEST_AWS_ACCOUNT_ID.value}:image-recipe/{recipe_id}/{recipe_version_id}"
                )
            },
            "recipeVersionComponentArn": {
                "Value": (
                    f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}"
                    f":{GlobalVariables.TEST_AWS_ACCOUNT_ID.value}:component/{recipe_id}/{recipe_version_id}/1"
                )
            },
        },
    )

    delete_recipe_versions_status_code, delete_recipe_versions_body = delete_recipe_version(
        recipe_id=recipe_id, recipe_version_id=recipe_version_id
    )

    # ASSERT
    assertpy.assert_that(create_status_code).is_equal_to(200)
    assertpy.assert_that(list_status_code).is_equal_to(200)
    assertpy.assert_that(len(list_body)).is_equal_to(1)
    assertpy.assert_that(create_component_version_status_code).is_equal_to(200)
    assertpy.assert_that(get_component_version_status_code).is_equal_to(200)
    assertpy.assert_that(len(get_component_version_body)).is_equal_to(1)
    assertpy.assert_that(create_recipe_status_code).is_equal_to(200)
    assertpy.assert_that(list_recipes_status_code).is_equal_to(200)
    assertpy.assert_that(len(list_recipes_body)).is_equal_to(1)
    assertpy.assert_that(create_recipe_version_status_code).is_equal_to(200)
    assertpy.assert_that(list_recipe_versions_status_code).is_equal_to(200)
    assertpy.assert_that(len(list_recipe_versions_body)).is_equal_to(1)
    assertpy.assert_that(delete_recipe_versions_status_code).is_equal_to(200)


def test_get_and_update_recipe_version_should_return_http_200(
    authenticated_event,
    lambda_context,
    backend_app_dynamodb_table,
    create_component,
    list_components,
    create_component_version,
    get_component_versions,
    create_recipe,
    list_recipes,
    create_recipe_version,
    list_recipe_versions,
    delete_recipe_version,
    get_recipe_version,
    update_recipe_version,
):
    # ARRANGE & ACT
    components_details = list()

    for idx in range(2):
        component_name = f"test-component-{idx + 1}"
        create_component(component_name=component_name)
        list_status_code, list_body = list_components()
        component_id = list_body.get("components")[0].get("componentId")
        create_component_version(component_id)
        get_component_version_status_code, get_component_version_body = get_component_versions(component_id)
        component_version_id = get_component_version_body.get("component_versions")[0].get("componentVersionId")
        backend_app_dynamodb_table.update_item(
            Key={
                "PK": f"COMPONENT#{component_id}",
                "SK": f"VERSION#{component_version_id}",
            },
            AttributeUpdates={
                "status": {"Value": "VALIDATED"},
                "componentBuildVersionArn": {
                    "Value": (
                        f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}"
                        f":{GlobalVariables.TEST_AWS_ACCOUNT_ID.value}:"
                        f"component/{component_id}/{component_version_id}"
                    )
                },
            },
        )
        components_details.append({"component_id": component_id, "component_version_id": component_version_id})

    create_recipe_status_code, create_recipe_body = create_recipe()
    list_recipes_status_code, list_recipes_body = list_recipes()
    recipe_id = list_recipes_body.get("recipes")[0].get("recipeId")
    create_recipe_version_status_code, create_recipe_version_body = create_recipe_version(
        recipe_id=recipe_id,
        recipe_version_components_versions=[
            api_model.RecipeComponentVersion(
                componentId=components_details[0]["component_id"],
                componentName="component-12345",
                componentVersionId=components_details[0]["component_version_id"],
                componentVersionName="1.0.0",
                componentVersionType="MAIN",
                order=1,
            ),
        ],
    )

    list_recipe_versions_status_code, list_recipe_versions_body = list_recipe_versions(recipe_id=recipe_id)
    recipe_version_id = list_recipe_versions_body.get("recipe_versions")[0].get("recipeVersionId")

    # ACT
    backend_app_dynamodb_table.update_item(
        Key={
            "PK": f"RECIPE#{recipe_id}",
            "SK": f"VERSION#{recipe_version_id}",
        },
        AttributeUpdates={
            "status": {"Value": "VALIDATED"},
            "recipeVersionArn": {
                "Value": (
                    f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}"
                    f":{GlobalVariables.TEST_AWS_ACCOUNT_ID.value}:image-recipe/{recipe_id}/{recipe_version_id}"
                )
            },
            "recipeVersionComponentArn": {
                "Value": (
                    f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}"
                    f":{GlobalVariables.TEST_AWS_ACCOUNT_ID.value}:component/{recipe_id}/{recipe_version_id}/1"
                )
            },
        },
    )

    get_recipe_version_status_code, get_recipe_version_body = get_recipe_version(
        recipe_id=recipe_id, version_id=recipe_version_id
    )
    update_recipe_version_status_code, update_recipe_version_body = update_recipe_version(
        recipe_id=recipe_id,
        recipe_version_id=recipe_version_id,
        recipe_version_description="Second Update",
        recipe_version_components_versions=[
            api_model.RecipeComponentVersion(
                componentId=components_details[1]["component_id"],
                componentName="component-54321",
                componentVersionId=components_details[1]["component_version_id"],
                componentVersionName="1.0.0",
                componentVersionType="MAIN",
                order=1,
            ),
        ],
    )
    get_updated_recipe_version_status_code, get_updated_recipe_version_body = get_recipe_version(
        recipe_id=recipe_id, version_id=recipe_version_id
    )

    # ASSERT
    assertpy.assert_that(create_recipe_status_code).is_equal_to(200)
    assertpy.assert_that(list_recipes_status_code).is_equal_to(200)
    assertpy.assert_that(len(list_recipes_body)).is_equal_to(1)
    assertpy.assert_that(create_recipe_version_status_code).is_equal_to(200)
    assertpy.assert_that(list_recipe_versions_status_code).is_equal_to(200)
    assertpy.assert_that(len(list_recipe_versions_body)).is_equal_to(1)
    assertpy.assert_that(get_recipe_version_status_code).is_equal_to(200)
    assertpy.assert_that(len(get_recipe_version_body)).is_equal_to(1)
    assertpy.assert_that(update_recipe_version_status_code).is_equal_to(200)
    assertpy.assert_that(get_updated_recipe_version_status_code).is_equal_to(200)
    assertpy.assert_that(
        get_updated_recipe_version_body.get("recipe_version").get("recipeVersionDescription")
    ).is_equal_to("Second Update")
    assertpy.assert_that(
        get_updated_recipe_version_body.get("recipe_version").get("recipeComponentsVersions")[0].get("componentId")
    ).is_equal_to(components_details[1]["component_id"])
    assertpy.assert_that(
        get_updated_recipe_version_body.get("recipe_version")
        .get("recipeComponentsVersions")[0]
        .get("componentVersionId")
    ).is_equal_to(components_details[1]["component_version_id"])


def test_get_mandatory_components_list_when_has_no_components_should_succeed(
    backend_app_dynamodb_table,
    get_mandatory_component_list,
):
    # ARRANGE & ACT
    status_code, _ = get_mandatory_component_list()

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(200)


def test_create_get_and_update_mandatory_components_list_should_succeed(
    authenticated_event,
    lambda_context,
    backend_app_dynamodb_table,
    create_component,
    list_components,
    create_component_version,
    get_component_versions,
    create_mandatory_components_list,
    update_mandatory_components_list,
    get_mandatory_component_list,
):
    # ARRANGE & ACT
    components_details = list()
    for idx in range(2):
        component_name = f"test-component-{idx + 1}"
        create_component(component_name=component_name)
        list_status_code, list_body = list_components()
        components = sorted(
            list_body.get("components"),
            key=lambda component: component.get("componentName"),
        )
        component_id = components[idx].get("componentId")
        create_component_version(component_id)
        get_component_version_status_code, get_component_version_body = get_component_versions(component_id)
        component_version_id = get_component_version_body.get("component_versions")[0].get("componentVersionId")
        backend_app_dynamodb_table.update_item(
            Key={
                "PK": f"COMPONENT#{component_id}",
                "SK": f"VERSION#{component_version_id}",
            },
            AttributeUpdates={
                "status": {"Value": "RELEASED"},
                "componentBuildVersionArn": {
                    "Value": (
                        f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}"
                        f":{GlobalVariables.TEST_AWS_ACCOUNT_ID.value}:"
                        f"component/{component_id}/{component_version_id}"
                    )
                },
            },
        )
        components_details.append(
            {
                "component_id": component_id,
                "component_name": component_name,
                "component_version_id": component_version_id,
            }
        )
    cmcl_status_code, cmcl_body = create_mandatory_components_list(
        mandatory_components_versions=[
            api_model.ComponentVersionEntry(
                componentId=components_details[0]["component_id"],
                componentName=components_details[0]["component_name"],
                componentVersionId=components_details[0]["component_version_id"],
                componentVersionName="1.0.0",
                order=1,
            )
        ],
    )
    gmcl_status_code, gmcl_body = get_mandatory_component_list()
    umcl_status_code, umcl_body = update_mandatory_components_list(
        mandatory_components_versions=[
            api_model.ComponentVersionEntry(
                componentId=components_details[0]["component_id"],
                componentName=components_details[0]["component_name"],
                componentVersionId=components_details[0]["component_version_id"],
                componentVersionName="1.0.0",
                order=1,
            ),
            api_model.ComponentVersionEntry(
                componentId=components_details[1]["component_id"],
                componentName=components_details[1]["component_name"],
                componentVersionId=components_details[1]["component_version_id"],
                componentVersionName="1.0.0",
                order=2,
            ),
        ],
    )

    updated_gmcl_status_code, updated_gmcl_body = get_mandatory_component_list()

    # ASSERT
    assertpy.assert_that(cmcl_status_code).is_equal_to(200)
    assertpy.assert_that(gmcl_status_code).is_equal_to(200)
    assertpy.assert_that(gmcl_body).is_not_none()
    mandatory_components_list_object = gmcl_body.get("mandatoryComponentsList")
    assertpy.assert_that(mandatory_components_list_object.get("mandatoryComponentsListPlatform")).is_equal_to(
        GlobalVariables.TEST_COMPONENT_PLATFORM.value
    )
    assertpy.assert_that(mandatory_components_list_object.get("mandatoryComponentsListOsVersion")).is_equal_to(
        GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value[0]
    )
    assertpy.assert_that(mandatory_components_list_object.get("mandatoryComponentsListArchitecture")).is_equal_to(
        GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value[0]
    )
    assertpy.assert_that(len(mandatory_components_list_object.get("prependedComponentsVersions"))).is_equal_to(1)
    mandatory_component_version_object = mandatory_components_list_object.get("prependedComponentsVersions")[0]
    assertpy.assert_that(mandatory_component_version_object.get("componentId")).is_equal_to(
        components_details[0]["component_id"],
    )
    assertpy.assert_that(mandatory_component_version_object.get("componentName")).is_equal_to(
        components_details[0]["component_name"]
    )
    assertpy.assert_that(mandatory_component_version_object.get("componentVersionId")).is_equal_to(
        components_details[0]["component_version_id"]
    )
    assertpy.assert_that(mandatory_component_version_object.get("componentVersionName")).is_equal_to("1.0.0")
    assertpy.assert_that(mandatory_component_version_object.get("order")).is_equal_to(1)
    assertpy.assert_that(umcl_status_code).is_equal_to(200)
    assertpy.assert_that(updated_gmcl_status_code).is_equal_to(200)
    assertpy.assert_that(updated_gmcl_body).is_not_none()
    updated_mandatory_components_list_object = updated_gmcl_body.get("mandatoryComponentsList")
    assertpy.assert_that(updated_mandatory_components_list_object.get("mandatoryComponentsListPlatform")).is_equal_to(
        GlobalVariables.TEST_COMPONENT_PLATFORM.value
    )
    assertpy.assert_that(updated_mandatory_components_list_object.get("mandatoryComponentsListOsVersion")).is_equal_to(
        GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value[0]
    )
    assertpy.assert_that(
        updated_mandatory_components_list_object.get("mandatoryComponentsListArchitecture")
    ).is_equal_to(GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value[0])
    assertpy.assert_that(len(updated_mandatory_components_list_object.get("prependedComponentsVersions"))).is_equal_to(
        2
    )
    for idx in range(2):
        update_mandatory_component_version_object = updated_mandatory_components_list_object.get(
            "prependedComponentsVersions"
        )[idx]
        assertpy.assert_that(update_mandatory_component_version_object.get("componentId")).is_equal_to(
            components_details[idx]["component_id"]
        )
        assertpy.assert_that(update_mandatory_component_version_object.get("componentName")).is_equal_to(
            components_details[idx]["component_name"]
        )
        assertpy.assert_that(update_mandatory_component_version_object.get("componentVersionId")).is_equal_to(
            components_details[idx]["component_version_id"]
        )
        assertpy.assert_that(update_mandatory_component_version_object.get("componentVersionName")).is_equal_to("1.0.0")
        assertpy.assert_that(update_mandatory_component_version_object.get("order")).is_equal_to(idx + 1)


def test_create_and_get_mandatory_components_lists_should_return_all_the_lists(
    authenticated_event,
    lambda_context,
    backend_app_dynamodb_table,
    create_component,
    list_components,
    create_component_version,
    get_component_versions,
    create_mandatory_components_list,
    list_mandatory_components_list,
):
    # ARRANGE & ACT
    create_component()
    list_status_code, list_body = list_components()
    component_id = list_body.get("components")[0].get("componentId")
    create_component_version(component_id)
    get_component_version_status_code, get_component_version_body = get_component_versions(component_id)
    component_version_id = get_component_version_body.get("component_versions")[0].get("componentVersionId")
    backend_app_dynamodb_table.update_item(
        Key={
            "PK": f"COMPONENT#{component_id}",
            "SK": f"VERSION#{component_version_id}",
        },
        AttributeUpdates={
            "status": {"Value": "RELEASED"},
            "componentBuildVersionArn": {
                "Value": (
                    f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}"
                    f":{GlobalVariables.TEST_AWS_ACCOUNT_ID.value}:"
                    f"component/{component_id}/{component_version_id}"
                )
            },
        },
    )

    for list_info in [
        {"platform": "Linux", "os": "Ubuntu 24"},
        {"platform": "Windows", "os": "Microsoft Windows Server 2025"},
    ]:
        create_mandatory_components_list(
            mandatory_component_list_platform=list_info.get("platform"),
            mandatory_component_list_os=list_info.get("os"),
            mandatory_components_versions=[
                api_model.ComponentVersionEntry(
                    componentId=component_id,
                    componentName="test-component-1",
                    componentVersionId=component_version_id,
                    componentVersionName="1.0.0",
                    order=1,
                )
            ],
        )

    lmcl_status_code, lmcl_body = list_mandatory_components_list()

    # ASSERT
    assertpy.assert_that(lmcl_status_code).is_equal_to(200)
    assertpy.assert_that(lmcl_body).is_not_none()
    mandatory_components_lists_object = lmcl_body.get("mandatoryComponentsLists")
    assertpy.assert_that(len(mandatory_components_lists_object)).is_equal_to(2)

    assertpy.assert_that(mandatory_components_lists_object[0].get("mandatoryComponentsListPlatform")).is_equal_to(
        "Linux"
    )
    assertpy.assert_that(mandatory_components_lists_object[0].get("mandatoryComponentsListOsVersion")).is_equal_to(
        "Ubuntu 24"
    )
    assertpy.assert_that(mandatory_components_lists_object[0].get("mandatoryComponentsListArchitecture")).is_equal_to(
        "amd64"
    )

    assertpy.assert_that(mandatory_components_lists_object[1].get("mandatoryComponentsListPlatform")).is_equal_to(
        "Windows"
    )
    assertpy.assert_that(mandatory_components_lists_object[1].get("mandatoryComponentsListOsVersion")).is_equal_to(
        "Microsoft Windows Server 2025"
    )
    assertpy.assert_that(mandatory_components_lists_object[1].get("mandatoryComponentsListArchitecture")).is_equal_to(
        "amd64"
    )
    for i in range(2):
        assertpy.assert_that(
            mandatory_components_lists_object[i].get("prependedComponentsVersions")[0].get("componentId")
        ).is_equal_to(component_id)
        assertpy.assert_that(
            mandatory_components_lists_object[i].get("prependedComponentsVersions")[0].get("componentName")
        ).is_equal_to("test-component-1")
        assertpy.assert_that(
            mandatory_components_lists_object[i].get("prependedComponentsVersions")[0].get("componentVersionId")
        ).is_equal_to(component_version_id)
        assertpy.assert_that(
            mandatory_components_lists_object[i].get("prependedComponentsVersions")[0].get("componentVersionName")
        ).is_equal_to("1.0.0")
        assertpy.assert_that(
            mandatory_components_lists_object[i].get("prependedComponentsVersions")[0].get("order")
        ).is_equal_to(1)


def test_create_list_update_and_retire_pipelines_should_return_http_200(
    authenticated_event,
    lambda_context,
    create_component,
    list_components,
    create_component_version,
    get_component_versions,
    update_component_version_status,
    create_recipe,
    list_recipes,
    create_recipe_version,
    update_recipe_version_status,
    create_pipeline,
    list_recipe_versions,
    list_pipelines,
    update_pipeline_status,
    get_pipeline,
    update_pipeline,
    retire_pipeline,
):
    # ARRANGE & ACT
    create_component_status_code, create_component_body = create_component()
    list_component_status_code, list_component_body = list_components()
    component_id = list_component_body.get("components")[0].get("componentId")
    create_component_version_status_code, create_component_version_body = create_component_version(component_id)
    get_component_version_status_code, get_component_version_body = get_component_versions(component_id)
    component_version_id = get_component_version_body.get("component_versions")[0].get("componentVersionId")
    update_component_version_status(component_id, component_version_id, "RELEASED")
    create_recipe_status_code, create_recipe_body = create_recipe()
    list_recipes_status_code, list_recipes_body = list_recipes()
    recipe_id = list_recipes_body.get("recipes")[0].get("recipeId")
    recipe_version_ids = list()
    for idx in range(2):
        create_recipe_version(
            recipe_id=recipe_id,
            recipe_version_components_versions=[
                api_model.RecipeComponentVersion(
                    componentId=component_id,
                    componentName="component-12345",
                    componentVersionId=component_version_id,
                    componentVersionName="1.0.0",
                    componentVersionType="MAIN",
                    order=1,
                ),
            ],
        )

        list_recipe_versions_status_code, list_recipe_versions_body = list_recipe_versions(recipe_id=recipe_id)
        recipe_version_id = list_recipe_versions_body.get("recipe_versions")[0].get("recipeVersionId")
        update_recipe_version_status(recipe_id, recipe_version_id, "RELEASED")
        recipe_version_ids.append(recipe_version_id)

    pipeline_status_code, pipeline_body = create_pipeline(
        recipe_id=recipe_id,
        recipe_version_id=recipe_version_ids[0],
    )
    list_pipelines_status_code, list_pipelines_body = list_pipelines()
    pipeline_id = list_pipelines_body.get("pipelines")[0].get("pipelineId")
    update_pipeline_status(pipeline_id, "CREATED")
    get_pipeline_status_code, get_pipeline_body = get_pipeline(pipeline_id)

    update_pipeline_status_code, update_pipeline_body = update_pipeline(
        pipeline_id=pipeline_id, recipe_version_id=recipe_version_ids[1]
    )
    get_updated_pipeline_status_code, get_updated_pipeline_body = get_pipeline(pipeline_id)
    update_pipeline_status(pipeline_id, "CREATED")

    retire_pipeline_status_code, retire_pipeline_body = retire_pipeline(pipeline_id)
    retired_get_pipelines_status_code, retired_get_pipelines_body = get_pipeline(pipeline_id=pipeline_id)
    # ASSERT
    assertpy.assert_that(create_component_status_code).is_equal_to(200)
    assertpy.assert_that(list_component_status_code).is_equal_to(200)
    assertpy.assert_that(len(list_recipes_body)).is_equal_to(1)
    assertpy.assert_that(create_component_version_status_code).is_equal_to(200)
    assertpy.assert_that(get_component_version_status_code).is_equal_to(200)
    assertpy.assert_that(len(get_component_version_body)).is_equal_to(1)
    assertpy.assert_that(create_recipe_status_code).is_equal_to(200)
    assertpy.assert_that(pipeline_status_code).is_equal_to(200)
    assertpy.assert_that(list_pipelines_status_code).is_equal_to(200)
    assertpy.assert_that(len(list_pipelines_body)).is_equal_to(1)
    assertpy.assert_that(get_pipeline_status_code).is_equal_to(200)
    assertpy.assert_that(len(get_pipeline_body)).is_equal_to(1)

    assertpy.assert_that(get_pipeline_body.get("pipeline").get("buildInstanceTypes")).is_equal_to(
        GlobalVariables.TEST_PIPELINE_BUILD_INSTANCE_TYPES.value
    )
    assertpy.assert_that(get_pipeline_body.get("pipeline").get("pipelineDescription")).is_equal_to(
        GlobalVariables.TEST_PIPELINE_DESCRIPTION.value
    )
    assertpy.assert_that(get_pipeline_body.get("pipeline").get("pipelineName")).is_equal_to(
        GlobalVariables.TEST_PIPELINE_NAME.value
    )
    assertpy.assert_that(get_pipeline_body.get("pipeline").get("pipelineSchedule")).is_equal_to(
        GlobalVariables.TEST_PIPELINE_SCHEDULE.value
    )
    assertpy.assert_that(get_pipeline_body.get("pipeline").get("recipeId")).is_equal_to(recipe_id)
    assertpy.assert_that(get_pipeline_body.get("pipeline").get("recipeVersionId")).is_equal_to(recipe_version_ids[0])
    assertpy.assert_that(update_pipeline_status_code).is_equal_to(200)
    assertpy.assert_that(get_updated_pipeline_status_code).is_equal_to(200)
    assertpy.assert_that(get_updated_pipeline_body.get("pipeline").get("buildInstanceTypes")).is_equal_to(
        GlobalVariables.TEST_PIPELINE_BUILD_INSTANCE_TYPES.value
    )
    assertpy.assert_that(get_updated_pipeline_body.get("pipeline").get("pipelineDescription")).is_equal_to(
        GlobalVariables.TEST_PIPELINE_DESCRIPTION.value
    )
    assertpy.assert_that(get_updated_pipeline_body.get("pipeline").get("pipelineName")).is_equal_to(
        GlobalVariables.TEST_PIPELINE_NAME.value
    )
    assertpy.assert_that(get_updated_pipeline_body.get("pipeline").get("pipelineSchedule")).is_equal_to(
        GlobalVariables.TEST_PIPELINE_SCHEDULE.value
    )
    assertpy.assert_that(get_updated_pipeline_body.get("pipeline").get("recipeId")).is_equal_to(recipe_id)
    assertpy.assert_that(get_updated_pipeline_body.get("pipeline").get("recipeVersionId")).is_equal_to(
        recipe_version_ids[1]
    )
    assertpy.assert_that(get_updated_pipeline_body.get("pipeline").get("status")).is_equal_to("UPDATING")
    assertpy.assert_that(retire_pipeline_status_code).is_equal_to(200)
    assertpy.assert_that(retired_get_pipelines_status_code).is_equal_to(200)
    assertpy.assert_that(retired_get_pipelines_body.get("pipeline").get("status")).is_equal_to("UPDATING")


orig = botocore.client.BaseClient._make_api_call


@pytest.fixture()
def mock_moto_calls():
    invocations = {
        "ListImagePipelineImages": {"imageSummaryList": []},
        "StartImagePipelineExecution": {
            "clientToken": "Test Token",
            "imageBuildVersionArn": (
                f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}:"
                f"{GlobalVariables.TEST_AWS_ACCOUNT_ID.value}:image/"
                f"{GlobalVariables.TEST_AMI_ID.value}/"
                f"{GlobalVariables.TEST_AMI_VERSION.value}/1"
            ),
            "requestId": "Test request",
        },
    }

    def _interceptor(self, operation_name, kwarg):
        if operation_name in invocations:
            return invocations[operation_name]

        return orig(self, operation_name, kwarg)

    with mock.patch("botocore.client.BaseClient._make_api_call", new=_interceptor):
        yield invocations


def test_create_and_list_images_should_return_http_200(
    authenticated_event,
    lambda_context,
    backend_app_dynamodb_table,
    mock_moto_calls,
    create_component,
    list_components,
    create_component_version,
    get_component_versions,
    update_component_version_status,
    create_recipe,
    list_recipes,
    create_recipe_version,
    update_recipe_version_status,
    create_pipeline,
    list_pipelines,
    update_pipeline_status,
    get_pipeline,
    create_image,
    list_images,
    get_image,
    list_recipe_versions,
):
    # ARRANGE
    create_component_status_code, create_component_body = create_component()
    list_component_status_code, list_component_body = list_components()
    component_id = list_component_body.get("components")[0].get("componentId")
    create_component_version_status_code, create_component_version_body = create_component_version(component_id)
    get_component_version_status_code, get_component_version_body = get_component_versions(component_id)
    component_version_id = get_component_version_body.get("component_versions")[0].get("componentVersionId")
    update_component_version_status(component_id, component_version_id, "RELEASED")
    create_recipe_status_code, create_recipe_body = create_recipe()
    list_recipes_status_code, list_recipes_body = list_recipes()
    recipe_id = list_recipes_body.get("recipes")[0].get("recipeId")
    recipe_version_ids = list()
    for idx in range(2):
        create_recipe_version(
            recipe_id=recipe_id,
            recipe_version_components_versions=[
                api_model.RecipeComponentVersion(
                    componentId=component_id,
                    componentName="component-12345",
                    componentVersionId=component_version_id,
                    componentVersionName="1.0.0",
                    componentVersionType="MAIN",
                    order=1,
                ),
            ],
        )

        list_recipe_versions_status_code, list_recipe_versions_body = list_recipe_versions(recipe_id=recipe_id)
        recipe_version_id = list_recipe_versions_body.get("recipe_versions")[0].get("recipeVersionId")
        update_recipe_version_status(recipe_id, recipe_version_id, "RELEASED")
        recipe_version_ids.append(recipe_version_id)

    pipeline_status_code, pipeline_body = create_pipeline(
        recipe_id=recipe_id,
        recipe_version_id=recipe_version_ids[0],
    )
    list_pipelines_status_code, list_pipelines_body = list_pipelines()
    pipeline_id = list_pipelines_body.get("pipelines")[0].get("pipelineId")
    update_pipeline_status(pipeline_id, "CREATED")
    get_pipeline_status_code, get_pipeline_body = get_pipeline(pipeline_id)
    create_image_status_code, create_image_body = create_image(pipeline_id)

    list_images_status_code, list_images_body = list_images()
    image_id = list_images_body.get("images")[0].get("imageId")
    get_image_status_code, get_image_body = get_image(image_id)

    # Assert
    # ASSERT
    assertpy.assert_that(create_component_status_code).is_equal_to(200)
    assertpy.assert_that(list_component_status_code).is_equal_to(200)
    assertpy.assert_that(len(list_recipes_body)).is_equal_to(1)
    assertpy.assert_that(create_component_version_status_code).is_equal_to(200)
    assertpy.assert_that(get_component_version_status_code).is_equal_to(200)
    assertpy.assert_that(len(get_component_version_body)).is_equal_to(1)
    assertpy.assert_that(create_recipe_status_code).is_equal_to(200)
    assertpy.assert_that(pipeline_status_code).is_equal_to(200)
    assertpy.assert_that(list_pipelines_status_code).is_equal_to(200)
    assertpy.assert_that(len(list_pipelines_body)).is_equal_to(1)
    assertpy.assert_that(get_pipeline_status_code).is_equal_to(200)
    assertpy.assert_that(len(get_pipeline_body)).is_equal_to(1)
    assertpy.assert_that(create_image_status_code).is_equal_to(200)
    assertpy.assert_that(list_images_status_code).is_equal_to(200)
    assertpy.assert_that(len(list_images_body)).is_equal_to(1)
    assertpy.assert_that(list_images_body.get("images")[0].get("imageBuildVersionArn")).is_equal_to(
        (
            f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}:"
            f"{GlobalVariables.TEST_AWS_ACCOUNT_ID.value}:image/"
            f"{GlobalVariables.TEST_AMI_ID.value}/"
            f"{GlobalVariables.TEST_AMI_VERSION.value}/1"
        )
    )
    assertpy.assert_that(get_image_status_code).is_equal_to(200)
    assertpy.assert_that(len(get_image_body)).is_equal_to(1)


def test_create_mandatory_components_list_with_positioned_components_and_recipe_version_should_succeed(
    authenticated_event,
    lambda_context,
    backend_app_dynamodb_table,
    create_component,
    list_components,
    create_component_version,
    get_component_versions,
    create_mandatory_components_list,
    get_mandatory_component_list,
    create_recipe,
    list_recipes,
    create_recipe_version,
    list_recipe_versions,
    get_recipe_version,
):
    # ARRANGE - Create components
    components_details = []
    for idx in range(4):
        component_name = f"test-component-{idx + 1}"
        create_component(component_name=component_name)
        list_status_code, list_body = list_components()
        components = sorted(
            list_body.get("components"),
            key=lambda component: component.get("componentName"),
        )
        component_id = components[idx].get("componentId")
        create_component_version(component_id)
        get_component_version_status_code, get_component_version_body = get_component_versions(component_id)
        component_version_id = get_component_version_body.get("component_versions")[0].get("componentVersionId")

        # Update component version status to RELEASED
        backend_app_dynamodb_table.update_item(
            Key={
                "PK": f"COMPONENT#{component_id}",
                "SK": f"VERSION#{component_version_id}",
            },
            AttributeUpdates={
                "status": {"Value": "RELEASED"},
                "componentVersionType": {"Value": "MAIN"},
                "componentBuildVersionArn": {
                    "Value": (
                        f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}"
                        f":{GlobalVariables.TEST_AWS_ACCOUNT_ID.value}:"
                        f"component/{component_id}/{component_version_id}"
                    )
                },
            },
        )
        components_details.append(
            {
                "component_id": component_id,
                "component_name": component_name,
                "component_version_id": component_version_id,
            }
        )

    # ACT - Create mandatory components list with prepended and appended components
    cmcl_status_code, cmcl_body = create_mandatory_components_list(
        prepended_components_versions=[
            api_model.ComponentVersionEntry(
                componentId=components_details[0]["component_id"],
                componentName=components_details[0]["component_name"],
                componentVersionId=components_details[0]["component_version_id"],
                componentVersionName="1.0.0",
                order=1,
            ),
            api_model.ComponentVersionEntry(
                componentId=components_details[1]["component_id"],
                componentName=components_details[1]["component_name"],
                componentVersionId=components_details[1]["component_version_id"],
                componentVersionName="1.0.0",
                order=2,
            ),
        ],
        appended_components_versions=[
            api_model.ComponentVersionEntry(
                componentId=components_details[2]["component_id"],
                componentName=components_details[2]["component_name"],
                componentVersionId=components_details[2]["component_version_id"],
                componentVersionName="1.0.0",
                order=1,
            ),
        ],
    )

    # Verify mandatory components list was created successfully
    gmcl_status_code, gmcl_body = get_mandatory_component_list()

    # Create recipe and recipe version with user-selected component
    create_recipe_status_code, create_recipe_body = create_recipe()
    list_recipes_status_code, list_recipes_body = list_recipes()
    recipe_id = list_recipes_body.get("recipes")[0].get("recipeId")

    create_recipe_version_status_code, create_recipe_version_body = create_recipe_version(
        recipe_id=recipe_id,
        recipe_version_components_versions=[
            api_model.RecipeComponentVersion(
                componentId=components_details[3]["component_id"],
                componentName=components_details[3]["component_name"],
                componentVersionId=components_details[3]["component_version_id"],
                componentVersionName="1.0.0",
                componentVersionType="MAIN",
                order=1,
            ),
        ],
    )

    # Get the created recipe version
    list_recipe_versions_status_code, list_recipe_versions_body = list_recipe_versions(recipe_id=recipe_id)
    assertpy.assert_that(list_recipe_versions_status_code).is_equal_to(200)
    assertpy.assert_that(list_recipe_versions_body.get("recipe_versions")).is_not_empty()
    recipe_version_id = list_recipe_versions_body.get("recipe_versions")[0].get("recipeVersionId")
    get_recipe_version_status_code, get_recipe_version_body = get_recipe_version(
        recipe_id=recipe_id, version_id=recipe_version_id
    )

    # ASSERT
    # Verify mandatory components list creation
    assertpy.assert_that(cmcl_status_code).is_equal_to(200)
    assertpy.assert_that(gmcl_status_code).is_equal_to(200)

    mandatory_components_list_object = gmcl_body.get("mandatoryComponentsList")
    assertpy.assert_that(mandatory_components_list_object).is_not_none()

    # Verify prepended components
    prepended_components = mandatory_components_list_object.get("prependedComponentsVersions")
    assertpy.assert_that(len(prepended_components)).is_equal_to(2)
    assertpy.assert_that(prepended_components[0].get("componentId")).is_equal_to(components_details[0]["component_id"])
    assertpy.assert_that(prepended_components[0].get("position")).is_equal_to("PREPEND")
    assertpy.assert_that(prepended_components[1].get("componentId")).is_equal_to(components_details[1]["component_id"])
    assertpy.assert_that(prepended_components[1].get("position")).is_equal_to("PREPEND")

    # Verify appended components
    appended_components = mandatory_components_list_object.get("appendedComponentsVersions")
    assertpy.assert_that(len(appended_components)).is_equal_to(1)
    assertpy.assert_that(appended_components[0].get("componentId")).is_equal_to(components_details[2]["component_id"])
    assertpy.assert_that(appended_components[0].get("position")).is_equal_to("APPEND")

    # Verify recipe version creation
    assertpy.assert_that(create_recipe_version_status_code).is_equal_to(200)
    assertpy.assert_that(get_recipe_version_status_code).is_equal_to(200)

    # Verify component order in recipe version: [prepended] + [user] + [appended]
    recipe_components = get_recipe_version_body.get("recipe_version").get("recipeComponentsVersions")
    assertpy.assert_that(len(recipe_components)).is_equal_to(4)

    # First two should be prepended mandatory components
    assertpy.assert_that(recipe_components[0].get("componentId")).is_equal_to(components_details[0]["component_id"])
    assertpy.assert_that(recipe_components[0].get("order")).is_equal_to(1)

    assertpy.assert_that(recipe_components[1].get("componentId")).is_equal_to(components_details[1]["component_id"])
    assertpy.assert_that(recipe_components[1].get("order")).is_equal_to(2)

    # Third should be user-selected component
    assertpy.assert_that(recipe_components[2].get("componentId")).is_equal_to(components_details[3]["component_id"])
    assertpy.assert_that(recipe_components[2].get("order")).is_equal_to(3)

    # Fourth should be appended mandatory component
    assertpy.assert_that(recipe_components[3].get("componentId")).is_equal_to(components_details[2]["component_id"])
    assertpy.assert_that(recipe_components[3].get("order")).is_equal_to(4)


def test_migration_and_backward_compatibility_should_succeed(
    authenticated_event,
    lambda_context,
    backend_app_dynamodb_table,
    create_component,
    list_components,
    create_component_version,
    get_component_versions,
    get_mandatory_component_list,
    create_recipe,
    list_recipes,
    create_recipe_version,
    list_recipe_versions,
    get_recipe_version,
):
    # ARRANGE - Create components
    components_details = []
    for idx in range(3):
        component_name = f"test-component-{idx + 1}"
        create_component(component_name=component_name)
        list_status_code, list_body = list_components()
        components = sorted(
            list_body.get("components"),
            key=lambda component: component.get("componentName"),
        )
        component_id = components[idx].get("componentId")
        create_component_version(component_id)
        get_component_version_status_code, get_component_version_body = get_component_versions(component_id)
        component_version_id = get_component_version_body.get("component_versions")[0].get("componentVersionId")

        # Update component version status to RELEASED
        backend_app_dynamodb_table.update_item(
            Key={
                "PK": f"COMPONENT#{component_id}",
                "SK": f"VERSION#{component_version_id}",
            },
            AttributeUpdates={
                "status": {"Value": "RELEASED"},
                "componentBuildVersionArn": {
                    "Value": (
                        f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}"
                        f":{GlobalVariables.TEST_AWS_ACCOUNT_ID.value}:"
                        f"component/{component_id}/{component_version_id}"
                    )
                },
            },
        )
        components_details.append(
            {
                "component_id": component_id,
                "component_name": component_name,
                "component_version_id": component_version_id,
            }
        )

    # ACT - Simulate legacy mandatory components list (without position field)
    # Insert directly into DynamoDB to simulate pre-migration data
    platform = GlobalVariables.TEST_COMPONENT_PLATFORM.value
    os_version = GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value[0]
    architecture = GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value[0]

    backend_app_dynamodb_table.put_item(
        Item={
            "PK": f"PLATFORM#{platform}",
            "SK": f"OS#{os_version}#ARCH#{architecture}",
            "mandatoryComponentsListPlatform": platform,
            "mandatoryComponentsListOsVersion": os_version,
            "mandatoryComponentsListArchitecture": architecture,
            "mandatoryComponentsVersions": [
                {
                    "componentId": components_details[0]["component_id"],
                    "componentName": components_details[0]["component_name"],
                    "componentVersionId": components_details[0]["component_version_id"],
                    "componentVersionName": "1.0.0",
                    "order": 1,
                    # Note: No position field - simulating legacy data
                },
                {
                    "componentId": components_details[1]["component_id"],
                    "componentName": components_details[1]["component_name"],
                    "componentVersionId": components_details[1]["component_version_id"],
                    "componentVersionName": "1.0.0",
                    "order": 2,
                    # Note: No position field - simulating legacy data
                },
            ],
            "createDate": "2024-01-01T00:00:00Z",
            "createdBy": GlobalVariables.TEST_CREATED_BY.value,
            "lastUpdateDate": "2024-01-01T00:00:00Z",
            "lastUpdatedBy": GlobalVariables.TEST_LAST_UPDATED_BY.value,
            "entity": "MandatoryComponentsList",
        }
    )

    # Simulate migration by updating the item with position = PREPEND
    from app.packaging.domain.model.shared.component_version_entry import (
        ComponentVersionEntryPosition,
    )

    response = backend_app_dynamodb_table.get_item(
        Key={
            "PK": f"PLATFORM#{platform}",
            "SK": f"OS#{os_version}#ARCH#{architecture}",
        }
    )

    item = response["Item"]
    updated_components = []
    for component in item["mandatoryComponentsVersions"]:
        if "position" not in component:
            component["position"] = ComponentVersionEntryPosition.Prepend.value
        updated_components.append(component)

    backend_app_dynamodb_table.update_item(
        Key={
            "PK": f"PLATFORM#{platform}",
            "SK": f"OS#{os_version}#ARCH#{architecture}",
        },
        UpdateExpression="set #mandatoryComponentsVersions = :components, #lastUpdateDate = :lastUpdateDate",
        ExpressionAttributeNames={
            "#mandatoryComponentsVersions": "mandatoryComponentsVersions",
            "#lastUpdateDate": "lastUpdateDate",
        },
        ExpressionAttributeValues={
            ":components": updated_components,
            ":lastUpdateDate": "2024-01-02T00:00:00Z",
        },
    )

    # Verify migration was successful
    gmcl_status_code, gmcl_body = get_mandatory_component_list()

    # Create recipe and recipe version after migration
    create_recipe_status_code, create_recipe_body = create_recipe()
    list_recipes_status_code, list_recipes_body = list_recipes()
    recipe_id = list_recipes_body.get("recipes")[0].get("recipeId")

    create_recipe_version_status_code, create_recipe_version_body = create_recipe_version(
        recipe_id=recipe_id,
        recipe_version_components_versions=[
            api_model.RecipeComponentVersion(
                componentId=components_details[2]["component_id"],
                componentName=components_details[2]["component_name"],
                componentVersionId=components_details[2]["component_version_id"],
                componentVersionName="1.0.0",
                componentVersionType="MAIN",
                order=1,
            ),
        ],
    )

    # Get the created recipe version
    list_recipe_versions_status_code, list_recipe_versions_body = list_recipe_versions(recipe_id=recipe_id)
    recipe_version_id = list_recipe_versions_body.get("recipe_versions")[0].get("recipeVersionId")
    get_recipe_version_status_code, get_recipe_version_body = get_recipe_version(
        recipe_id=recipe_id, version_id=recipe_version_id
    )

    # ASSERT
    # Verify all existing components have position = PREPEND after migration
    assertpy.assert_that(gmcl_status_code).is_equal_to(200)
    mandatory_components_list_object = gmcl_body.get("mandatoryComponentsList")
    assertpy.assert_that(mandatory_components_list_object).is_not_none()

    # Check that migrated components are in prepended list
    prepended_components = mandatory_components_list_object.get("prependedComponentsVersions")
    assertpy.assert_that(len(prepended_components)).is_equal_to(2)

    for idx, component in enumerate(prepended_components):
        assertpy.assert_that(component.get("componentId")).is_equal_to(components_details[idx]["component_id"])
        assertpy.assert_that(component.get("order")).is_equal_to(idx + 1)

    # Verify appended list is empty (all legacy components should be prepended)
    appended_components = mandatory_components_list_object.get("appendedComponentsVersions")
    assertpy.assert_that(len(appended_components)).is_equal_to(0)

    # Verify recipe version creation works correctly after migration
    assertpy.assert_that(create_recipe_version_status_code).is_equal_to(200)
    assertpy.assert_that(get_recipe_version_status_code).is_equal_to(200)

    # Verify component order in recipe version: [prepended mandatory] + [user]
    recipe_components = get_recipe_version_body.get("recipe_version").get("recipeComponentsVersions")
    assertpy.assert_that(len(recipe_components)).is_equal_to(3)

    # First two should be prepended mandatory components (from migration)
    assertpy.assert_that(recipe_components[0].get("componentId")).is_equal_to(components_details[0]["component_id"])
    assertpy.assert_that(recipe_components[0].get("order")).is_equal_to(1)

    assertpy.assert_that(recipe_components[1].get("componentId")).is_equal_to(components_details[1]["component_id"])
    assertpy.assert_that(recipe_components[1].get("order")).is_equal_to(2)

    # Third should be user-selected component
    assertpy.assert_that(recipe_components[2].get("componentId")).is_equal_to(components_details[2]["component_id"])
    assertpy.assert_that(recipe_components[2].get("position")).is_none()
    assertpy.assert_that(recipe_components[2].get("order")).is_equal_to(3)
