from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.image import register_image_command_handler
from app.packaging.domain.events.image import (
    automated_image_registration_completed,
    image_registration_completed,
)
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version_detail
from app.packaging.domain.model.image import image
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.tests.conftest import TEST_DATE, TEST_PRODUCT_ID


def test_register_image_command_handler_should_raise_an_exception_when_pipeline_can_not_be_found(
    component_version_query_service_mock,
    get_register_image_command,
    image_query_service_mock,
    message_bus_mock,
    pipeline_query_service_mock,
    recipe_version_query_service_mock,
    uow_mock,
    recipe_query_service_mock,
):
    # ARRANGE
    pipeline_query_service_mock.get_pipeline_by_pipeline_id.return_value = None
    register_image_command_mock = get_register_image_command()

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        register_image_command_handler.handle(
            command=register_image_command_mock,
            component_version_qry_srv=component_version_query_service_mock,
            image_qry_srv=image_query_service_mock,
            message_bus=message_bus_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            uow=uow_mock,
            recipe_qry_srv=recipe_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Pipeline {register_image_command_mock.pipelineId.value} can not be found."
    )


def test_register_image_command_handler_should_raise_an_exception_when_recipe_can_not_be_found(
    component_version_query_service_mock,
    get_register_image_command,
    get_pipeline_entity,
    image_query_service_mock,
    message_bus_mock,
    pipeline_query_service_mock,
    recipe_version_query_service_mock,
    uow_mock,
    recipe_query_service_mock,
):
    # ARRANGE
    pipeline_entity = get_pipeline_entity()
    pipeline_query_service_mock.get_pipeline_by_pipeline_id.return_value = pipeline_entity
    register_image_command_mock = get_register_image_command()
    recipe_query_service_mock.get_recipe.return_value = None

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        register_image_command_handler.handle(
            command=register_image_command_mock,
            component_version_qry_srv=component_version_query_service_mock,
            image_qry_srv=image_query_service_mock,
            message_bus=message_bus_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            uow=uow_mock,
            recipe_qry_srv=recipe_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(f"Recipe {pipeline_entity.recipeId} can not be found.")


def test_register_image_command_handler_should_raise_an_exception_when_recipe_version_can_not_be_found(
    component_version_query_service_mock,
    get_image_entity,
    get_pipeline_entity,
    get_register_image_command,
    image_query_service_mock,
    message_bus_mock,
    pipeline_query_service_mock,
    recipe_version_query_service_mock,
    uow_mock,
    recipe_query_service_mock,
    mock_recipe_object,
):
    # ARRANGE
    image_entity = get_image_entity()
    image_query_service_mock.get_image_by_image_build_version_arn.return_value = image_entity
    image_query_service_mock.get_images_by_recipe_id_and_version_name.return_value = [image_entity]
    pipeline_query_service_mock.get_pipeline_by_pipeline_id.return_value = get_pipeline_entity()
    recipe_version_query_service_mock.get_recipe_version.return_value = None
    register_image_command_mock = get_register_image_command()
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        register_image_command_handler.handle(
            command=register_image_command_mock,
            component_version_qry_srv=component_version_query_service_mock,
            image_qry_srv=image_query_service_mock,
            message_bus=message_bus_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            uow=uow_mock,
            recipe_qry_srv=recipe_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"No recipe version {image_entity.recipeId} found for {image_entity.recipeVersionId}."
    )


def test_register_image_command_handler_should_raise_an_exception_when_recipe_component_version_can_not_be_found(
    component_version_query_service_mock,
    get_image_entity,
    get_pipeline_entity,
    get_register_image_command,
    image_query_service_mock,
    message_bus_mock,
    mock_recipe_version_object,
    pipeline_query_service_mock,
    recipe_version_query_service_mock,
    uow_mock,
    recipe_query_service_mock,
    mock_recipe_object,
):
    # ARRANGE
    component_version_query_service_mock.get_component_version.return_value = None
    image_entity = get_image_entity()
    image_query_service_mock.get_image_by_image_build_version_arn.return_value = image_entity
    image_query_service_mock.get_images_by_recipe_id_and_version_name.return_value = [image_entity]
    pipeline_query_service_mock.get_pipeline_by_pipeline_id.return_value = get_pipeline_entity()
    recipe_version_entity = mock_recipe_version_object
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity
    register_image_command_mock = get_register_image_command()
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        register_image_command_handler.handle(
            command=register_image_command_mock,
            component_version_qry_srv=component_version_query_service_mock,
            image_qry_srv=image_query_service_mock,
            message_bus=message_bus_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            uow=uow_mock,
            recipe_qry_srv=recipe_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Component version {recipe_version_entity.recipeComponentsVersions[0].componentVersionId} "
        f"for {recipe_version_entity.recipeComponentsVersions[0].componentId} not found."
    )


@freeze_time(TEST_DATE)
@mock.patch("app.packaging.domain.model.image.image.random.choice", lambda _: "1")
@pytest.mark.parametrize(
    "image_entities,image_entity,image_status,pipeline_entity,register_image_command",
    (
        (
            None,
            None,
            image.ImageStatus.Created,
            {
                "status": pipeline.PipelineStatus.Created,
            },
            {
                "image_status": image.ImageStatus.Created,
            },
        ),
        (
            None,
            None,
            image.ImageStatus.Created,
            {
                "project_id": "proj-67890",
                "pipeline_id": "pipe-67890def",
                "recipe_id": "reci-67890def",
                "recipe_name": "proserve-recipe-b",
                "recipe_version_id": "vers-67890def",
                "recipe_version_name": "1.0.0",
                "status": pipeline.PipelineStatus.Created,
            },
            {
                "image_build_version": 1,
                "image_status": image.ImageStatus.Created,
                "pipeline_id": "pipe-67890def",
                "recipe_name": "proserve-recipe-b",
                "recipe_version_name": "2.0.0",
            },
        ),
        (
            None,
            {
                "status": image.ImageStatus.Creating,
            },
            image.ImageStatus.Created,
            {
                "status": pipeline.PipelineStatus.Created,
            },
            {
                "image_status": image.ImageStatus.Created,
            },
        ),
        (
            None,
            {
                "project_id": "proj-67890",
                "image_id": "imag-67890def",
                "image_build_version": 2,
                "recipe_id": "reci-67890def",
                "recipe_name": "proserve-recipe-b",
                "recipe_version_id": "vers-67890def",
                "recipe_version_name": "2.0.0",
                "status": image.ImageStatus.Creating,
            },
            image.ImageStatus.Created,
            {
                "status": pipeline.PipelineStatus.Created,
            },
            {
                "image_build_version": 2,
                "image_status": image.ImageStatus.Created,
                "recipe_name": "proserve-recipe-b",
                "recipe_version_name": "2.0.0",
            },
        ),
        (
            None,
            None,
            image.ImageStatus.Failed,
            {
                "status": pipeline.PipelineStatus.Created,
            },
            {
                "image_status": image.ImageStatus.Failed,
                "image_upstream_id": None,
            },
        ),
        (
            [
                {
                    "image_build_version": 1,
                    "image_upstream_id": "ami-01234567890abcdef",
                    "status": image.ImageStatus.Retired,
                },
                {
                    "image_build_version": 3,
                    "image_upstream_id": "ami-67890012345defabc",
                    "status": image.ImageStatus.Created,
                },
            ],
            None,
            image.ImageStatus.Retired,
            {
                "status": pipeline.PipelineStatus.Created,
            },
            {
                "image_build_version": 2,
                "image_status": image.ImageStatus.Created,
            },
        ),
        (
            [
                {
                    "project_id": "proj-67890",
                    "image_build_version": 1,
                    "image_upstream_id": "ami-01234567890abcdef",
                    "status": image.ImageStatus.Retired,
                },
                {
                    "project_id": "proj-67890",
                    "image_id": "imag-67890def",
                    "image_build_version": 2,
                    "image_upstream_id": "ami-67890012345defabc",
                    "status": image.ImageStatus.Created,
                },
            ],
            None,
            image.ImageStatus.Created,
            {
                "project_id": "proj-67890",
                "status": pipeline.PipelineStatus.Created,
            },
            {
                "image_build_version": 3,
                "image_status": image.ImageStatus.Created,
            },
        ),
    ),
)
def test_register_image_command_handler_should_register_image(
    component_version_query_service_mock,
    generic_repo_mock,
    get_image_entity,
    get_pipeline_entity,
    get_register_image_command,
    get_test_component_version,
    image_entities,
    image_entity,
    image_query_service_mock,
    image_status,
    message_bus_mock,
    mock_recipe_version_object,
    pipeline_entity,
    pipeline_query_service_mock,
    recipe_version_query_service_mock,
    register_image_command,
    uow_mock,
    recipe_query_service_mock,
    mock_recipe_object,
):
    # ARRANGE
    component_version_entity = get_test_component_version
    component_version_query_service_mock.get_component_version.return_value = component_version_entity
    recipe_version_entity = mock_recipe_version_object
    recipe_version_entity.recipeVersionIntegrations = ["GitHub"]
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity
    register_image_command_mock = get_register_image_command(**register_image_command)
    test_image_build_version = register_image_command_mock.imageBuildVersionArn.value.split("/")[3]
    test_pipeline_entity = get_pipeline_entity(**pipeline_entity)
    new_image_entity = get_image_entity(
        project_id=test_pipeline_entity.projectId,
        image_id="image-11111111",
        image_build_version=test_image_build_version,
        pipeline_id=test_pipeline_entity.pipelineId,
        recipe_id=test_pipeline_entity.recipeId,
        recipe_name=test_pipeline_entity.recipeName,
        recipe_version_id=test_pipeline_entity.recipeVersionId,
        recipe_version_name=register_image_command_mock.imageBuildVersionArn.value.split("/")[2],
        status=image.ImageStatus.Creating,
    )
    test_image_entities = (
        [get_image_entity(**image_entity) for image_entity in image_entities] if image_entities else list()
    )
    test_image_entity = get_image_entity(**image_entity) if image_entity else None
    expected_image_entity = test_image_entity if test_image_entity else new_image_entity

    test_image_entities.append(expected_image_entity)

    image_query_service_mock.get_image_by_image_build_version_arn.return_value = test_image_entity
    image_query_service_mock.get_images_by_recipe_id_and_version_name.return_value = (
        test_image_entities if test_image_entities else [new_image_entity]
    )
    pipeline_query_service_mock.get_pipeline_by_pipeline_id.return_value = test_pipeline_entity
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object

    # ACT
    register_image_command_handler.handle(
        command=register_image_command_mock,
        component_version_qry_srv=component_version_query_service_mock,
        image_qry_srv=image_query_service_mock,
        message_bus=message_bus_mock,
        pipeline_qry_srv=pipeline_query_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        uow=uow_mock,
        recipe_qry_srv=recipe_query_service_mock,
    )

    # ASSERT
    if not test_image_entity:
        generic_repo_mock.add.assert_called_with(expected_image_entity)
    update_attrs = {"status": image_status, "lastUpdateDate": TEST_DATE}
    if register_image_command_mock.imageUpstreamId:
        update_attrs["imageUpstreamId"] = register_image_command_mock.imageUpstreamId.value
    generic_repo_mock.update_attributes.assert_any_call(
        image.ImagePrimaryKey(
            projectId=expected_image_entity.projectId,
            imageId=expected_image_entity.imageId,
        ),
        **update_attrs,
    )
    if image_status == image.ImageStatus.Created:
        components_versions_details = list()
        retired_amis_ids = list()

        for existing_image_entity in [
            existing_image_entity
            for existing_image_entity in test_image_entities
            if existing_image_entity.status == image.ImageStatus.Created
        ]:
            generic_repo_mock.update_attributes.assert_any_call(
                image.ImagePrimaryKey(
                    projectId=existing_image_entity.projectId,
                    imageId=existing_image_entity.imageId,
                ),
                status=image.ImageStatus.Retired,
                lastUpdateDate=TEST_DATE,
            )
            retired_amis_ids.append(existing_image_entity.imageUpstreamId)
        for recipe_component_version in recipe_version_entity.recipeComponentsVersions:
            components_versions_details.append(
                component_version_detail.ComponentVersionDetail(
                    componentName=component_version_entity.componentName,
                    componentVersionType=recipe_component_version.componentVersionType,
                    softwareVendor=component_version_entity.softwareVendor,
                    softwareVersion=component_version_entity.softwareVersion,
                    licenseDashboard=(
                        component_version_entity.licenseDashboard if component_version_entity.licenseDashboard else None
                    ),
                    notes=(component_version_entity.notes if component_version_entity.notes else None),
                )
            )
        message_bus_mock.publish.assert_any_call(
            image_registration_completed.ImageRegistrationCompleted(
                projectId=expected_image_entity.projectId,
                amiDescription=recipe_version_entity.recipeName,
                amiId=register_image_command_mock.imageUpstreamId.value,
                amiName=f"Version {recipe_version_entity.recipeVersionName} of {recipe_version_entity.recipeName}",
                componentsVersionsDetails=components_versions_details,
                retiredAmiIds=retired_amis_ids,
                osVersion="Ubuntu 24",
                createDate=TEST_DATE,
                platform="Linux",
                architecture="amd64",
                integrations=["GitHub"],
            )
        )
        message_bus_mock.publish.assert_any_call(
            automated_image_registration_completed.AutomatedImageRegistrationCompleted(
                amiId=register_image_command_mock.imageUpstreamId.value,
                productId=test_pipeline_entity.productId,
                projectId=expected_image_entity.projectId,
                releaseType="PATCH",
                userId="SYSTEM",
                componentsVersionsDetails=components_versions_details,
                osVersion="Ubuntu 24",
                platform="Linux",
                architecture="amd64",
                integrations=["GitHub"],
            )
        )
    uow_mock.commit.assert_called()


@freeze_time(TEST_DATE)
@mock.patch("app.packaging.domain.model.image.image.random.choice", lambda _: "1")
def test_register_image_command_handler_should_always_publish_automated_image_registration_completed(
    component_version_query_service_mock,
    generic_repo_mock,
    get_image_entity,
    get_pipeline_entity,
    get_register_image_command,
    get_test_component_version,
    image_query_service_mock,
    message_bus_mock,
    mock_recipe_version_object,
    pipeline_query_service_mock,
    recipe_version_query_service_mock,
    uow_mock,
    recipe_query_service_mock,
    mock_recipe_object,
):
    # ARRANGE
    component_version_entity = get_test_component_version
    component_version_query_service_mock.get_component_version.return_value = component_version_entity
    recipe_version_entity = mock_recipe_version_object
    recipe_version_entity.recipeVersionIntegrations = []
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity
    register_image_command_mock = get_register_image_command(image_status=image.ImageStatus.Created)
    test_pipeline_entity = get_pipeline_entity(status=pipeline.PipelineStatus.Created, product_id=TEST_PRODUCT_ID)
    new_image_entity = get_image_entity(
        project_id=test_pipeline_entity.projectId,
        image_id="image-11111111",
        image_build_version=1,
        pipeline_id=test_pipeline_entity.pipelineId,
        recipe_id=test_pipeline_entity.recipeId,
        recipe_name=test_pipeline_entity.recipeName,
        recipe_version_id=test_pipeline_entity.recipeVersionId,
        recipe_version_name=register_image_command_mock.imageBuildVersionArn.value.split("/")[2],
        status=image.ImageStatus.Creating,
    )

    image_query_service_mock.get_image_by_image_build_version_arn.return_value = None
    image_query_service_mock.get_images_by_recipe_id_and_version_name.return_value = [new_image_entity]
    pipeline_query_service_mock.get_pipeline_by_pipeline_id.return_value = test_pipeline_entity
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object

    # ACT
    register_image_command_handler.handle(
        command=register_image_command_mock,
        component_version_qry_srv=component_version_query_service_mock,
        image_qry_srv=image_query_service_mock,
        message_bus=message_bus_mock,
        pipeline_qry_srv=pipeline_query_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        uow=uow_mock,
        recipe_qry_srv=recipe_query_service_mock,
    )

    # ASSERT - Should publish both ImageRegistrationCompleted and AutomatedImageRegistrationCompleted
    assertpy.assert_that(message_bus_mock.publish.call_count).is_equal_to(2)

    # First call should be ImageRegistrationCompleted
    first_event = message_bus_mock.publish.call_args_list[0][0][0]
    assertpy.assert_that(first_event.event_name).is_equal_to("ImageRegistrationCompleted")

    # Second call should be AutomatedImageRegistrationCompleted with product details
    second_event = message_bus_mock.publish.call_args_list[1][0][0]
    assertpy.assert_that(second_event.event_name).is_equal_to("AutomatedImageRegistrationCompleted")
    assertpy.assert_that(second_event.productId).is_equal_to(TEST_PRODUCT_ID)
    assertpy.assert_that(second_event.releaseType).is_equal_to("PATCH")
    assertpy.assert_that(second_event.userId).is_equal_to("SYSTEM")
    assertpy.assert_that(second_event.osVersion).is_equal_to(mock_recipe_object.recipeOsVersion)
    assertpy.assert_that(second_event.platform).is_equal_to(mock_recipe_object.recipePlatform)
    assertpy.assert_that(second_event.architecture).is_equal_to(mock_recipe_object.recipeArchitecture)
