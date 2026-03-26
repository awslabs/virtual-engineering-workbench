import logging
from typing import List
from unittest import mock

import boto3
import moto
import pytest
from freezegun import freeze_time

from app.packaging.domain.commands.component import (
    remove_component_version_command,
    retire_component_version_command,
    share_component_command,
    update_component_version_command,
)
from app.packaging.domain.commands.image import (
    create_image_command,
    register_automated_image_command,
    register_image_command,
)
from app.packaging.domain.commands.pipeline import (
    create_pipeline_command,
    deploy_pipeline_command,
    remove_pipeline_command,
    retire_pipeline_command,
    update_pipeline_command,
)
from app.packaging.domain.commands.recipe import (
    check_recipe_version_testing_environment_launch_status_command,
    check_recipe_version_testing_environment_setup_status_command,
    check_recipe_version_testing_test_status_command,
    complete_recipe_version_testing_command,
    create_recipe_version_command,
    deploy_recipe_version_command,
    launch_recipe_version_testing_environment_command,
    remove_recipe_version_command,
    retire_recipe_version_command,
    run_recipe_version_testing_command,
    setup_recipe_version_testing_environment_command,
    update_recipe_version_command,
    update_recipe_version_on_component_update_command,
)
from app.packaging.domain.events.pipeline import (
    pipeline_creation_started,
    pipeline_update_started,
)
from app.packaging.domain.model.component import (
    component,
    component_version,
    mandatory_components_list,
)
from app.packaging.domain.model.image import image
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.model.recipe import (
    recipe,
    recipe_version,
    recipe_version_test_execution,
)
from app.packaging.domain.model.shared import (
    component_version_entry,
    recipe_version_entry,
)
from app.packaging.domain.model.shared.component_version_entry import (
    ComponentVersionEntry,
)
from app.packaging.domain.ports import (
    component_query_service,
    component_version_definition_service,
    component_version_query_service,
    component_version_service,
    component_version_test_execution_query_service,
    component_version_testing_service,
    image_query_service,
    mandatory_components_list_query_service,
    parameter_service,
    pipeline_query_service,
    pipeline_service,
    publishing_query_service,
    recipe_query_service,
    recipe_version_query_service,
    recipe_version_service,
    recipe_version_test_execution_query_service,
    recipe_version_testing_service,
)
from app.packaging.domain.value_objects.component import (
    component_build_version_arn_value_object,
    component_id_value_object,
)
from app.packaging.domain.value_objects.component_version import (
    component_software_vendor_value_object,
    component_software_version_value_object,
    component_version_dependencies_value_object,
    component_version_description_value_object,
    component_version_id_value_object,
    component_version_yaml_definition_value_object,
)
from app.packaging.domain.value_objects.image import (
    ami_id_value_object,
    image_build_version_arn_value_object,
    image_status_value_object,
    image_upstream_id_value_object,
    product_id_value_object,
)
from app.packaging.domain.value_objects.pipeline import (
    pipeline_arn_value_object,
    pipeline_build_instance_types_value_object,
    pipeline_description_value_object,
    pipeline_distribution_config_arn_value_object,
    pipeline_id_value_object,
    pipeline_infrastructure_config_arn_value_object,
    pipeline_name_value_object,
    pipeline_schedule_value_object,
)
from app.packaging.domain.value_objects.recipe import (
    recipe_id_value_object,
    recipe_name_value_object,
)
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_arn_value_object,
    recipe_version_components_versions_value_object,
    recipe_version_description_value_object,
    recipe_version_id_value_object,
    recipe_version_name_value_object,
    recipe_version_parent_image_upstream_id_value_object,
    recipe_version_release_type_value_object,
    recipe_version_volume_size_value_object,
)
from app.packaging.domain.value_objects.recipe_version_test_execution import (
    recipe_version_test_execution_id_value_object,
)
from app.packaging.domain.value_objects.shared import (
    project_id_value_object,
    user_id_value_object,
    user_role_value_object,
    version_release_type_value_object,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.middleware.authorization import VirtualWorkbenchRoles

TEST_AMI_ID = "ami-01234567890abcdef"
TEST_ARCHITECTURE = "amd64"
TEST_BUILD_INSTANCE_TYPES = ["m8a.4xlarge", "m8i.4xlarge"]
TEST_COMMAND_ID = "ef7fdfd8-9b57-4151-a15c-000000000000"
TEST_COMPONENT_ID = "comp-1234abcd"
TEST_COMPONENT_NAME = "proserve-component-a"
TEST_COMPONENT_VERSION_ID = "vers-1234abcd"
TEST_DATE = "2023-10-01T00:00:00+00:00"
TEST_IMAGE_BUILD_VERSION = 1
TEST_IMAGE_ID = "image-12345abc"
TEST_INSTANCE_ID = "i-01234567890abcdef"
TEST_INSTANCE_TYPE = "m8i.2xlarge"
TEST_OS_VERSION = "Ubuntu 24"
TEST_PIPELINE_DESCRIPTION = "Test pipeline."
TEST_PIPELINE_ID = "pipe-12345abc"
TEST_PIPELINE_NAME = "test-pipeline"
TEST_PIPELINE_SCHEDULE = "0 10 * * ? *"
TEST_PLATFORM = "Linux"
TEST_PROJECT_ID = "proj-12345"
TEST_PROJECT_IDS = [TEST_PROJECT_ID, "proj-67890", "proj-91011", "proj-121314"]
TEST_RECIPE_ID = "reci-1234abcd"
TEST_RECIPE_NAME = "proserve-recipe-a"
TEST_RECIPE_VERSION_ID = "vers-1234abcd"
TEST_RECIPE_VERSION_NAME = "1.0.0"
TEST_RECIPE_VERSION_VOLUME_SIZE = "8"
TEST_REGION = "us-east-1"
TEST_TEST_EXECUTION_ID = "c0220642-ced2-4f46-bea3-1601a70b5c55"
TEST_USER_ID = "T123456"
TEST_COMPONENT_TEST_S3_BUCKET_NAME = "test-bucket"
TEST_RECIPE_TEST_S3_BUCKET_NAME = "test-bucket"
TEST_PRODUCT_ID = "product-12345"


@pytest.fixture()
def get_test_project_id():
    return TEST_PROJECT_ID


@pytest.fixture()
def get_test_project_ids():
    return TEST_PROJECT_IDS


@pytest.fixture()
def get_test_ami_id():
    return TEST_AMI_ID


@pytest.fixture()
def get_test_architecture():
    return TEST_ARCHITECTURE


@pytest.fixture()
def get_test_os_version():
    return TEST_OS_VERSION


@pytest.fixture()
def get_test_platform():
    return TEST_PLATFORM


@pytest.fixture()
def get_test_recipe_id():
    return TEST_RECIPE_ID


@pytest.fixture()
def get_test_component_id():
    return TEST_COMPONENT_ID


@pytest.fixture()
def get_test_recipe_name():
    return TEST_RECIPE_NAME


@pytest.fixture()
def get_test_recipe_version_arn():
    def _get_test_recipe_version_arn(version_name: str):
        return f"arn:aws:imagebuilder:us-east-1:123456789012:image-recipe/proserve-autosar-recipe/{version_name}"

    return _get_test_recipe_version_arn


@pytest.fixture()
def get_test_recipe_version_component_arn():
    def _get_test_recipe_version_component_arn(version_name: str):
        return f"arn:aws:imagebuilder:us-east-1:123456789012:component/proserve-autosar-recipe/{version_name}/1"

    return _get_test_recipe_version_component_arn


@pytest.fixture()
def get_test_component_version_arn():
    def _get_test_component_version_arn(version_name: str):
        return f"arn:aws:imagebuilder:us-east-1:123456789012:component/{TEST_COMPONENT_ID}/{version_name}/1"

    return _get_test_component_version_arn


@pytest.fixture()
def get_test_recipe_version_id():
    return TEST_RECIPE_VERSION_ID


@pytest.fixture()
def get_test_execution_id():
    return TEST_TEST_EXECUTION_ID


@pytest.fixture()
def get_test_instance_type():
    return TEST_INSTANCE_TYPE


@pytest.fixture()
def get_test_instance_id():
    return TEST_INSTANCE_ID


@pytest.fixture()
def get_test_command_id():
    return TEST_COMMAND_ID


@pytest.fixture()
def get_test_component_version_id():
    return TEST_COMPONENT_VERSION_ID


@pytest.fixture()
def get_test_test_execution_id():
    return TEST_TEST_EXECUTION_ID


@pytest.fixture()
def get_test_component_yaml_definition():
    def _get_test_component_yaml_definition():
        # Ref: https://docs.aws.amazon.com/imagebuilder/latest/userguide/toe-use-documents.html#document-example
        component_yaml_definition = """
        name: LinuxBin
        description: Download and run a custom Linux binary file.
        schemaVersion: 1.0
        phases:
          - name: build
            steps:
              - name: Download
                action: S3Download
                inputs:
                  - source: s3://<replaceable>mybucket</replaceable>/<replaceable>myapplication</replaceable>
                    destination: /tmp/<replaceable>myapplication</replaceable>
              - name: Enable
                action: ExecuteBash
                onFailure: Continue
                inputs:
                  commands:
                    - 'chmod u+x {{ build.Download.inputs[0].destination }}'
              - name: Install
                action: ExecuteBinary
                onFailure: Continue
                inputs:
                  path: '{{ build.Download.inputs[0].destination }}'
                  arguments:
                    - '--install'
              - name: Delete
                action: DeleteFile
                inputs:
                  - path: '{{ build.Download.inputs[0].destination }}'
        """
        return component_yaml_definition

    return _get_test_component_yaml_definition


@pytest.fixture()
def get_test_build_instance_types():
    return TEST_BUILD_INSTANCE_TYPES


@pytest.fixture()
def get_test_pipeline_arn(pipeline_id: str = TEST_PIPELINE_ID):
    def _get_test_pipeline_arn() -> str:
        return f"arn:aws:imagebuilder:us-east-1:123456789012:image-pipeline/{TEST_PIPELINE_ID}"

    return _get_test_pipeline_arn


@pytest.fixture()
def get_test_pipeline_description():
    return TEST_PIPELINE_DESCRIPTION


@pytest.fixture()
def get_test_pipeline_distribution_config_arn(pipeline_id: str = TEST_PIPELINE_ID):
    def _get_test_pipeline_distribution_config_arn() -> str:
        return f"arn:aws:imagebuilder:us-east-1:123456789012:distribution-configuration/{pipeline_id}"

    return _get_test_pipeline_distribution_config_arn


@pytest.fixture()
def get_test_pipeline_infrastructure_config_arn(pipeline_id: str = TEST_PIPELINE_ID):
    def _get_test_pipeline_infrastructure_config_arn() -> str:
        return f"arn:aws:imagebuilder:us-east-1:123456789012:infrastructure-configuration/{pipeline_id}"

    return _get_test_pipeline_infrastructure_config_arn


@pytest.fixture()
def get_test_pipeline_id():
    return TEST_PIPELINE_ID


@pytest.fixture()
def get_test_pipeline_name():
    return TEST_PIPELINE_NAME


@pytest.fixture()
def get_test_pipeline_schedule():
    return TEST_PIPELINE_SCHEDULE


@pytest.fixture()
def get_test_image_build_version():
    return TEST_IMAGE_BUILD_VERSION


@pytest.fixture()
def get_test_image_id():
    return TEST_IMAGE_ID


@pytest.fixture()
def get_test_image_build_version_arn():
    def _get_test_image_build_version_arn(build_version: int, recipe_name: str, version_name: str) -> str:
        return f"arn:aws:imagebuilder:us-east-1:123456789012:image/{recipe_name}/{version_name}/{build_version}"

    return _get_test_image_build_version_arn


@pytest.fixture()
def get_test_user_id():
    return TEST_USER_ID


@pytest.fixture()
def get_test_component():
    return component.Component(
        componentId="comp-1234abcd",
        componentDescription="Test description",
        componentName="test-component",
        componentPlatform="Linux",
        componentSupportedArchitectures=["amd64"],
        componentSupportedOsVersions=["Ubuntu 24"],
        status=component.ComponentStatus.Created,
        createDate="2023-10-27T00:00:00+00:00",
        createdBy="T000001",
        lastUpdateDate="2023-10-27T00:00:00+00:00",
        lastUpdatedBy="T000001",
    )


@pytest.fixture()
def get_test_component_version(get_test_component_version_arn):
    return component_version.ComponentVersion(
        componentId="comp-1234abcd",
        componentVersionId="vers-1234abcd",
        componentVersionName="1.0.0-rc.1",
        componentName="test-component",
        componentVersionDescription="Test description",
        componentBuildVersionArn=get_test_component_version_arn("1.0.0-rc.1"),
        componentVersionS3Uri="s3://test/component.yaml",
        componentPlatform="Linux",
        componentSupportedArchitectures=["arm64"],
        componentSupportedOsVersions=["Ubuntu 24"],
        componentVersionDependencies=[],
        softwareVendor="vector",
        softwareVersion="1.0.0",
        status=component_version.ComponentVersionStatus.Created,
        createDate="2023-10-27T00:00:00+00:00",
        createdBy="T000001",
        lastUpdateDate="2023-10-27T00:00:00+00:00",
        lastUpdatedBy="T000001",
    )


@pytest.fixture()
def get_test_component_version_with_dependencies(get_test_component_version_arn):
    components_list = [
        component_version.ComponentVersion(
            componentId="comp-1234abcd",
            componentVersionId="vers-1234abcd",
            componentVersionName="1.0.0-rc.1",
            componentName="test-component",
            componentVersionDescription="Test description",
            componentBuildVersionArn=get_test_component_version_arn("1.0.0-rc.1"),
            componentVersionS3Uri="s3://test/component.yaml",
            componentPlatform="Linux",
            componentSupportedArchitectures=["arm64"],
            componentSupportedOsVersions=["Ubuntu 24"],
            status=component_version.ComponentVersionStatus.Created,
            createDate="2023-10-27T00:00:00+00:00",
            createdBy="T000001",
            lastUpdateDate="2023-10-27T00:00:00+00:00",
            lastUpdatedBy="T000001",
            componentVersionDependencies=[
                ComponentVersionEntry(
                    componentId="comp-0",
                    componentName=TEST_COMPONENT_NAME,
                    componentVersionId=TEST_COMPONENT_VERSION_ID,
                    componentVersionName="1.0.2",
                    order=1,
                ),
                ComponentVersionEntry(
                    componentId="comp-1",
                    componentName=TEST_COMPONENT_NAME,
                    componentVersionId=f"{TEST_COMPONENT_VERSION_ID}",
                    componentVersionName="1.0.0",
                    order=2,
                ),
            ],
            softwareVendor="vector",
            softwareVersion="1.0.0",
        )
    ]
    for i in range(3):
        components_list.append(
            component_version.ComponentVersion(
                componentId=f"comp-{i}",
                componentName=TEST_COMPONENT_NAME,
                componentVersionId=TEST_COMPONENT_VERSION_ID,
                componentVersionName="1.0.0-rc1",
                componentVersionDescription="test component order",
                componentBuildVersionArn=f"arn:aws:imagebuilder:us-east-1:123456789012:component/comp-{i}/1.0.0-rc1/1",
                componentVersionS3Uri=f"s3://test-component-bucket/comp-{i}/1.0.0-rc1/component.yaml",
                componentPlatform="Linux",
                componentSupportedArchitectures=["amd64", "arm64"],
                componentSupportedOsVersions=["Ubuntu 24"],
                softwareVendor="vector",
                softwareVersion="1.0.0",
                status="VALIDATED",
                createDate="2024-01-11",
                createdBy="2024-01-11",
                lastUpdateDate="2024-01-11",
                lastUpdatedBy="T0000001",
            )
        )
    return components_list


@pytest.fixture()
def get_test_component_version_with_specific_component_id_version_name_and_status(
    get_test_component_version_arn,
):
    def _get_test_component_version_with_specific_component_id_version_name_and_status(
        component_id: str = TEST_COMPONENT_ID,
        component_version_id: str = TEST_COMPONENT_VERSION_ID,
        version_name: str = "1.0.0",
        status: component_version.ComponentVersionStatus = component_version.ComponentVersionStatus.Created,
    ):
        return component_version.ComponentVersion(
            componentId=component_id,
            componentVersionId=component_version_id,
            componentVersionName=version_name,
            componentName="test-component",
            componentVersionDescription="Test description",
            componentBuildVersionArn=get_test_component_version_arn(version_name),
            componentVersionS3Uri="s3://test/component.yaml",
            componentPlatform=TEST_PLATFORM,
            componentSupportedArchitectures=[TEST_ARCHITECTURE],
            componentSupportedOsVersions=[TEST_OS_VERSION],
            softwareVendor="vector",
            softwareVersion="1.0.0",
            status=status,
            createDate="2023-10-27T00:00:00+00:00",
            createdBy="T000001",
            lastUpdateDate="2023-10-27T00:00:00+00:00",
            lastUpdatedBy="T000001",
        )

    return _get_test_component_version_with_specific_component_id_version_name_and_status


@pytest.fixture()
def get_test_component_with_specific_platform_architecture_and_os_version():
    def _get_test_component_with_specific_platform_architecture_and_os_version(
        platform: str,
        supported_architectures: List[str],
        supported_os_versions: List[str],
    ):
        return component.Component(
            componentId="comp-1234abcd",
            componentDescription="Test description",
            componentName="test-component",
            componentPlatform=platform,
            componentSupportedArchitectures=supported_architectures,
            componentSupportedOsVersions=supported_os_versions,
            status=component.ComponentStatus.Created,
            createDate="2023-10-27T00:00:00+00:00",
            createdBy="T000001",
            lastUpdateDate="2023-10-27T00:00:00+00:00",
            lastUpdatedBy="T000001",
        )

    return _get_test_component_with_specific_platform_architecture_and_os_version


@pytest.fixture()
def get_test_component_version_with_specific_status():
    def _get_test_component_version_with_specific_status(
        status: component_version.ComponentVersionStatus,
    ):
        return component_version.ComponentVersion(
            componentId="comp-1234abcd",
            componentVersionId="vers-1234abcd",
            componentVersionName="1.0.0-rc.1",
            componentName="test-component",
            componentVersionDescription="Test description",
            componentBuildVersionArn="arn::test",
            componentVersionS3Uri="s3://test/component.yaml",
            componentPlatform="Linux",
            componentSupportedArchitectures=["arm64"],
            componentSupportedOsVersions=["Ubuntu 24"],
            softwareVendor="vector",
            softwareVersion="1.0.0",
            status=status,
            createDate="2023-10-27T00:00:00+00:00",
            createdBy="T000001",
            lastUpdateDate="2023-10-27T00:00:00+00:00",
            lastUpdatedBy="T000001",
        )

    return _get_test_component_version_with_specific_status


@pytest.fixture()
def get_test_component_version_with_specific_version_name(
    get_test_component_version_arn,
):
    def _get_test_component_version_with_specific_version_name(version_name: str):
        return component_version.ComponentVersion(
            componentId="comp-1234abcd",
            componentVersionId="vers-1234abcd",
            componentVersionName=version_name,
            componentName="test-component",
            componentVersionDescription="Test description",
            componentBuildVersionArn=get_test_component_version_arn(version_name),
            componentVersionS3Uri="s3://test/component.yaml",
            componentPlatform="Linux",
            componentSupportedArchitectures=["arm64"],
            componentSupportedOsVersions=["Ubuntu 24"],
            status=component_version.ComponentVersionStatus.Created,
            createDate="2023-10-27T00:00:00+00:00",
            createdBy="T000001",
            lastUpdateDate="2023-10-27T00:00:00+00:00",
            lastUpdatedBy="T000001",
        )

    return _get_test_component_version_with_specific_version_name


@pytest.fixture()
def get_test_component_version_with_specific_version_name_and_status(
    get_test_component_version_arn, mock_recipe_object, mock_recipe_version_object
):
    def _get_test_component_version_with_specific_version_name_and_status(
        version_name: str, status: component_version.ComponentVersionStatus
    ):
        return component_version.ComponentVersion(
            componentId="comp-1234abcd",
            componentVersionId="vers-1234abcd",
            componentVersionName=version_name,
            componentName="test-component",
            componentVersionDescription="Test description",
            componentBuildVersionArn=get_test_component_version_arn(version_name),
            componentVersionS3Uri="s3://test/component.yaml",
            componentPlatform="Linux",
            componentSupportedArchitectures=["arm64"],
            componentSupportedOsVersions=["Ubuntu 24"],
            softwareVendor="vector",
            softwareVersion="1.0.0",
            status=status,
            createDate="2023-10-27T00:00:00+00:00",
            createdBy="T000001",
            lastUpdateDate="2023-10-27T00:00:00+00:00",
            lastUpdatedBy="T000001",
            componentVersionDependencies=[
                ComponentVersionEntry(
                    componentId="comp-0",
                    componentName=TEST_COMPONENT_NAME,
                    componentVersionId=TEST_COMPONENT_VERSION_ID,
                    componentVersionName="1.0.2",
                    order=1,
                ),
                ComponentVersionEntry(
                    componentId="comp-1",
                    componentName=TEST_COMPONENT_NAME,
                    componentVersionId=f"{TEST_COMPONENT_VERSION_ID}",
                    componentVersionName="1.0.0",
                    order=2,
                ),
            ],
        )

    return _get_test_component_version_with_specific_version_name_and_status


@pytest.fixture()
def get_test_component_version_with_specific_version_name_and_status_with_recipe(
    get_test_component_version_arn, mock_recipe_object, mock_recipe_version_object
):
    def _get_test_component_version_with_specific_version_name_and_status(
        version_name: str, status: component_version.ComponentVersionStatus
    ):
        return component_version.ComponentVersion(
            componentId="comp-1234abcd",
            componentVersionId="vers-1234abcd",
            componentVersionName=version_name,
            componentName="test-component",
            componentVersionDescription="Test description",
            componentBuildVersionArn=get_test_component_version_arn(version_name),
            componentVersionS3Uri="s3://test/component.yaml",
            componentPlatform="Linux",
            componentSupportedArchitectures=["arm64"],
            componentSupportedOsVersions=["Ubuntu 24"],
            softwareVendor="vector",
            softwareVersion="1.0.0",
            status=status,
            createDate="2023-10-27T00:00:00+00:00",
            createdBy="T000001",
            lastUpdateDate="2023-10-27T00:00:00+00:00",
            lastUpdatedBy="T000001",
            componentVersionDependencies=[
                ComponentVersionEntry(
                    componentId="comp-0",
                    componentName=TEST_COMPONENT_NAME,
                    componentVersionId=TEST_COMPONENT_VERSION_ID,
                    componentVersionName="1.0.2",
                    order=1,
                ),
                ComponentVersionEntry(
                    componentId="comp-1",
                    componentName=TEST_COMPONENT_NAME,
                    componentVersionId=f"{TEST_COMPONENT_VERSION_ID}",
                    componentVersionName="1.0.0",
                    order=2,
                ),
            ],
            associatedRecipesVersions=[
                recipe_version_entry.RecipeVersionEntry(
                    recipeId=mock_recipe_object.recipeId,
                    recipeName=mock_recipe_object.recipeName,
                    recipeVersionId=mock_recipe_version_object.recipeVersionId,
                    recipeVersionName=mock_recipe_version_object.recipeVersionName,
                )
            ],
        )

    return _get_test_component_version_with_specific_version_name_and_status


@pytest.fixture
def mock_system_configuration_mapping():
    return {
        TEST_PLATFORM: {
            TEST_ARCHITECTURE: {
                TEST_OS_VERSION: {
                    # Adding /test/ prefix since /aws/service/ is reserved and can't be mocked
                    "ami_ssm_param_name": "/test/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id",
                    "command_ssm_document_name": "AWS-RunShellScript",
                    "run_testing_command": "awstoe run --documents << documents >> --execution-id /<< instance_id >> --log-s3-bucket-name << log_s3_bucket_name >> --log-s3-key-prefix << object_id >>/<< version_id >> --trace",
                    "setup_testing_environment_command": "curl https://awstoe-us-east-1.s3.us-east-1.amazonaws.com/latest/linux/amd64/awstoe --output /usr/bin/awstoe && chmod +x /usr/bin/awstoe",
                    "instance_type": "m8i.2xlarge",
                }
            }
        },
    }


@pytest.fixture()
def mock_ami_ssm_param(mock_system_configuration_mapping, mock_ssm_client):
    mock_ssm_client.put_parameter(
        Name=mock_system_configuration_mapping.get(TEST_PLATFORM)
        .get(TEST_ARCHITECTURE)
        .get(TEST_OS_VERSION)
        .get("ami_ssm_param_name"),
        Type="String",
        Value=TEST_AMI_ID,
    )


@pytest.fixture()
def component_version_query_service_mock():
    component_version_qry_srv = mock.create_autospec(spec=component_version_query_service.ComponentVersionQueryService)

    return component_version_qry_srv


@pytest.fixture()
def component_query_service_mock():
    component_qry_srv = mock.create_autospec(spec=component_query_service.ComponentQueryService)

    return component_qry_srv


@pytest.fixture()
def component_version_test_execution_query_service_mock():
    component_version_test_execution_qry_srv = mock.create_autospec(
        spec=component_version_test_execution_query_service.ComponentVersionTestExecutionQueryService
    )

    return component_version_test_execution_qry_srv


@pytest.fixture()
def component_version_testing_service_mock():
    component_version_testing_srv = mock.create_autospec(
        spec=component_version_testing_service.ComponentVersionTestingService
    )

    return component_version_testing_srv


@pytest.fixture()
def mandatory_components_list_query_service_mock():
    mandatory_components_list_qry_srv = mock.create_autospec(
        spec=mandatory_components_list_query_service.MandatoryComponentsListQueryService
    )
    mandatory_components_list_qry_srv.get_mandatory_components_list.return_value = []
    return mandatory_components_list_qry_srv


@pytest.fixture()
def s3_service_mock():
    s3_service_mock = mock.create_autospec(spec=component_version_definition_service.ComponentVersionDefinitionService)

    return s3_service_mock


@pytest.fixture()
def get_test_mandatory_components_list_with_specific_mandatory_components_versions():
    def _get_test_mandatory_components_list_with_specific_mandatory_components_versions(
        mandatory_components_versions: list[component_version_entry.ComponentVersionEntry] = [
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234abc",
                componentName="component-1234abc",
                componentVersionId="vers-1234abc",
                componentVersionName="3.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=3,
                position=component_version_entry.ComponentVersionEntryPosition.Prepend,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234fghi",
                componentName="component-1234fghi",
                componentVersionId="vers-123fghi",
                componentVersionName="1.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=1,
                position=component_version_entry.ComponentVersionEntryPosition.Prepend,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234def",
                componentName="component-1234def",
                componentVersionId="vers-1234def",
                componentVersionName="2.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=2,
                position=component_version_entry.ComponentVersionEntryPosition.Prepend,
            ),
        ]
    ):
        return mandatory_components_list.MandatoryComponentsList(
            mandatoryComponentsListArchitecture=TEST_ARCHITECTURE,
            mandatoryComponentsListOsVersion=TEST_OS_VERSION,
            mandatoryComponentsListPlatform=TEST_ARCHITECTURE,
            mandatoryComponentsVersions=mandatory_components_versions,
            createDate="2023-10-27T00:00:00+00:00",
            createdBy="T000001",
            lastUpdateDate="2023-10-27T00:00:00+00:00",
            lastUpdatedBy="T000001",
        )

    return _get_test_mandatory_components_list_with_specific_mandatory_components_versions


@pytest.fixture()
def get_test_mandatory_components_list_with_specific_mandatory_components_versions_without_component_version_type_set():
    def _get_test_mandatory_components_list_with_specific_mandatory_components_versions_without_component_version_type_set(
        mandatory_components_versions: list[component_version_entry.ComponentVersionEntry] = [
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234abc",
                componentName="component-1234abc",
                componentVersionId="vers-1234abc",
                componentVersionName="3.0.0",
                order=3,
                position=component_version_entry.ComponentVersionEntryPosition.Prepend,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234fghi",
                componentName="component-1234fghi",
                componentVersionId="vers-123fghi",
                componentVersionName="1.0.0",
                order=1,
                position=component_version_entry.ComponentVersionEntryPosition.Prepend,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234def",
                componentName="component-1234def",
                componentVersionId="vers-1234def",
                componentVersionName="2.0.0",
                order=2,
                position=component_version_entry.ComponentVersionEntryPosition.Prepend,
            ),
        ]
    ):
        return mandatory_components_list.MandatoryComponentsList(
            mandatoryComponentsListArchitecture=TEST_ARCHITECTURE,
            mandatoryComponentsListOsVersion=TEST_OS_VERSION,
            mandatoryComponentsListPlatform=TEST_ARCHITECTURE,
            mandatoryComponentsVersions=mandatory_components_versions,
            createDate="2023-10-27T00:00:00+00:00",
            createdBy="T000001",
            lastUpdateDate="2023-10-27T00:00:00+00:00",
            lastUpdatedBy="T000001",
        )

    return _get_test_mandatory_components_list_with_specific_mandatory_components_versions_without_component_version_type_set


@pytest.fixture(autouse=True)
def mock_ssm_client():
    with moto.mock_aws():
        yield boto3.client("ssm", region_name=TEST_REGION)


@pytest.fixture()
def recipe_version_service_mock():
    recipe_version_srv = mock.create_autospec(spec=recipe_version_service.RecipeVersionService)

    return recipe_version_srv


@pytest.fixture()
def recipe_version_repo_mock():
    return mock.create_autospec(spec=unit_of_work.GenericRepository)


@pytest.fixture()
def component_version_definition_service_mock():
    return mock.create_autospec(spec=component_version_definition_service.ComponentVersionDefinitionService)


@pytest.fixture()
def component_version_service_mock():
    component_version_srv = mock.create_autospec(spec=component_version_service.ComponentVersionService)

    return component_version_srv


@pytest.fixture()
def recipe_version_query_service_mock():
    recipe_version_qry_srv = mock.create_autospec(spec=recipe_version_query_service.RecipeVersionQueryService)
    recipe_version_qry_srv.get_latest_recipe_version_name.return_value = "1.0.0"
    return recipe_version_qry_srv


@pytest.fixture()
def recipe_query_service_mock(mock_recipe_object):
    recipe_qry_srv = mock.create_autospec(spec=recipe_query_service.RecipeQueryService)
    recipe_qry_srv.get_recipe.return_value = mock_recipe_object
    return recipe_qry_srv


@pytest.fixture()
def recipe_version_test_execution_query_service_mock():
    recipe_version_test_execution_qry_srv = mock.create_autospec(
        spec=recipe_version_test_execution_query_service.RecipeVersionTestExecutionQueryService
    )

    return recipe_version_test_execution_qry_srv


@pytest.fixture()
def parameter_service_mock(get_test_ami_id):
    m = mock.create_autospec(spec=parameter_service.ParameterDefinitionService)
    m.get_parameter_value.return_value = get_test_ami_id
    return m


@pytest.fixture()
def image_query_service_mock():
    return mock.create_autospec(spec=image_query_service.ImageQueryService)


@pytest.fixture()
def recipe_component_versions_mock():
    return recipe_version_components_versions_value_object.from_list(
        [
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234jkl",
                componentName="component-1234jkl",
                componentVersionId="vers-1234jkl",
                componentVersionName="1.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=3,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234pqr",
                componentName="component-1234pqr",
                componentVersionId="vers-1234pqr",
                componentVersionName="3.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=1,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234mno",
                componentName="component-1234mno",
                componentVersionId="vers-1234mno",
                componentVersionName="2.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=2,
            ),
        ]
    )


@pytest.fixture()
def launch_recipe_version_testing_environment_command_mock() -> (
    launch_recipe_version_testing_environment_command.LaunchRecipeVersionTestingEnvironmentCommand
):
    return launch_recipe_version_testing_environment_command.LaunchRecipeVersionTestingEnvironmentCommand(
        projectId=project_id_value_object.from_str(TEST_PROJECT_ID),
        recipeId=recipe_id_value_object.from_str(TEST_RECIPE_ID),
        recipeVersionId=recipe_version_id_value_object.from_str(TEST_RECIPE_VERSION_ID),
        testExecutionId=recipe_version_test_execution_id_value_object.from_str(TEST_TEST_EXECUTION_ID),
    )


@pytest.fixture()
def recipe_version_testing_service_mock():
    recipe_version_testing_qry_srv = mock.create_autospec(
        spec=recipe_version_testing_service.RecipeVersionTestingService
    )

    return recipe_version_testing_qry_srv


@pytest.fixture()
def run_recipe_version_testing_command_mock() -> run_recipe_version_testing_command.RunRecipeVersionTestingCommand:
    return run_recipe_version_testing_command.RunRecipeVersionTestingCommand(
        recipeId=recipe_id_value_object.from_str(TEST_RECIPE_ID),
        recipeVersionId=recipe_version_id_value_object.from_str(TEST_RECIPE_VERSION_ID),
        testExecutionId=recipe_version_test_execution_id_value_object.from_str(TEST_TEST_EXECUTION_ID),
    )


@pytest.fixture()
def mock_recipe_object() -> recipe.Recipe:
    return recipe.Recipe(
        projectId=TEST_PROJECT_ID,
        recipeId=TEST_RECIPE_ID,
        recipeName="Test recipe",
        recipeDescription="This is a recipe for validation",
        recipePlatform="Linux",
        recipeArchitecture="amd64",
        recipeOsVersion="Ubuntu 24",
        status=recipe.RecipeStatus.Created,
        createdBy="T998765",
        createDate="2023-10-13T00:00:00+00:00",
        lastUpdatedBy="T998765",
        lastUpdateDate="2023-10-13T00:00:00+00:00",
    )


@pytest.fixture()
def mock_recipe_version_object(mock_recipe_object) -> recipe_version.RecipeVersion:
    return recipe_version.RecipeVersion(
        recipeId=mock_recipe_object.recipeId,
        recipeVersionId=TEST_RECIPE_VERSION_ID,
        recipeVersionName=TEST_RECIPE_VERSION_NAME,
        recipeName="Test recipe",
        recipeVersionDescription="Test description",
        recipeComponentsVersions=[
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234jkl",
                componentName="component-1234jkl",
                componentVersionId="vers-1234jkl",
                componentVersionName="1.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=3,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234pqr",
                componentName="component-1234pqr",
                componentVersionId="vers-1234pqr",
                componentVersionName="3.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=1,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234mno",
                componentName="component-1234mno",
                componentVersionId="vers-1234mno",
                componentVersionName="2.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=2,
            ),
        ],
        recipeVersionVolumeSize=TEST_RECIPE_VERSION_VOLUME_SIZE,
        status=recipe_version.RecipeVersionStatus.Creating,
        recipeVersionComponentArn="arn:aws:imagebuilder:us-east-1:123456789123:component/comp-12345/1.0.0/1",
        parentImageUpstreamId=TEST_AMI_ID,
        createDate="2023-09-29T00:00:00+00:00",
        createdBy="T123456",
        lastUpdateDate="2023-09-29T00:00:00+00:00",
        lastUpdatedBy="T123456",
    )


@pytest.fixture()
def deploy_recipe_version_command_mock():
    def _deploy_recipe_version_command_mocked(recipe_version_value: str):
        return deploy_recipe_version_command.DeployRecipeVersionCommand(
            projectId=project_id_value_object.from_str(TEST_PROJECT_ID),
            recipeId=recipe_id_value_object.from_str(TEST_RECIPE_ID),
            parentImageUpstreamId=recipe_version_parent_image_upstream_id_value_object.from_str(
                "ami-08734ec479a1ace4a"
            ),
            recipeVersionId=recipe_version_id_value_object.from_str(TEST_RECIPE_VERSION_ID),
            recipeVersionName=recipe_version_name_value_object.from_str(recipe_version_value),
            components=recipe_version_components_versions_value_object.from_list(
                [
                    ComponentVersionEntry(
                        componentId="comp-8675abc",
                        componentName="component-8675abc",
                        componentVersionId="vers-1234abcd",
                        componentVersionName="2.0.0",
                        componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                        order=2,
                    ),
                    ComponentVersionEntry(
                        componentId="comp2-1234abc",
                        componentName="component2-1234abc",
                        componentVersionId="vers-1234abcd",
                        componentVersionName="1.0.0",
                        componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                        order=1,
                    ),
                    ComponentVersionEntry(
                        componentId="comp3-9867dfg",
                        componentName="component3-9867dfg",
                        componentVersionId="vers-1234abcd",
                        componentVersionName="3.0.0",
                        componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                        order=3,
                    ),
                ]
            ),
            recipeVersionVolumeSize=recipe_version_volume_size_value_object.from_str(TEST_RECIPE_VERSION_VOLUME_SIZE),
            lastUpdatedBy=user_id_value_object.from_str("T123456"),
        )

    return _deploy_recipe_version_command_mocked


@pytest.fixture()
def return_component_version():
    def _return_lazy_component_version(componentId: str, componentVersionId: str):
        component_version_name = "1.0.2"
        component_id = componentId
        component_version_id = componentVersionId
        if component_id is None:
            return None
        return component_version.ComponentVersion(
            componentId=component_id,
            componentName=TEST_COMPONENT_NAME,
            componentVersionId=component_version_id,
            componentVersionName=component_version_name,
            componentVersionDescription="test component order",
            componentBuildVersionArn=f"arn:aws:imagebuilder:us-east-1:123456789012:component/{component_id}/{component_version_name}/1",
            componentVersionS3Uri=f"s3://test-component-bucket/{component_id}/{component_version_name}/component.yaml",
            componentPlatform="Linux",
            componentSupportedArchitectures=["amd64", "arm64"],
            componentSupportedOsVersions=["Ubuntu 24"],
            softwareVendor="vector",
            softwareVersion="1.0.0",
            status="CREATED",
            createDate="2024-01-11",
            createdBy="2024-01-11",
            lastUpdateDate="2024-01-11",
            lastUpdatedBy="T0000001",
        )

    return _return_lazy_component_version


@pytest.fixture()
def get_test_recipe_version_with_specific_version_name():
    def _get_test_recipe_version_with_specific_version_name(version_name: str):
        return recipe_version.RecipeVersion(
            recipeId=TEST_RECIPE_ID,
            recipeVersionId=TEST_RECIPE_VERSION_ID,
            recipeVersionName=version_name,
            recipeName="Test recipe",
            recipeVersionDescription="Initial release",
            parentImageUpstreamId=TEST_AMI_ID,
            recipeComponentsVersions=[
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abcd",
                    componentVersionName="1.0.0",
                    order=1,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp2-1234abc",
                    componentName="component2-1234abc",
                    componentVersionId="vers-1234abcd",
                    componentVersionName="2.0.0",
                    order=2,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp2-1234abc",
                    componentName="component2-1234abc",
                    componentVersionId="vers-1234abcd",
                    componentVersionName="3.0.0",
                    order=3,
                ),
            ],
            recipeVersionVolumeSize=TEST_RECIPE_VERSION_VOLUME_SIZE,
            recipeVersionArn="arn:aws:imagebuilder:us-east-1:123456789012:\
                    image-recipe/proserve-autosar-recipe/1.0.0",
            status=recipe_version.RecipeVersionStatus.Created,
            createDate="2023-11-30T00:00:00+00:00",
            createdBy="T000001",
            lastUpdateDate="2023-11-30T00:00:00+00:00",
            lastUpdatedBy="T000001",
        )

    return _get_test_recipe_version_with_specific_version_name


@pytest.fixture()
def get_test_recipe_version_with_specific_status():
    def _get_test_recipe_version_with_specific_status(
        status: component_version.ComponentVersionStatus,
    ):
        return recipe_version.RecipeVersion(
            recipeId=TEST_RECIPE_ID,
            recipeVersionId=TEST_RECIPE_VERSION_ID,
            recipeVersionName=TEST_RECIPE_VERSION_NAME,
            recipeName="Test recipe",
            recipeVersionDescription="Initial release",
            parentImageUpstreamId=TEST_AMI_ID,
            recipeComponentsVersions=[
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abcd",
                    componentVersionName="1.0.0",
                    order=1,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp2-1234abc",
                    componentName="component2-1234abc",
                    componentVersionId="vers-1234abcd",
                    componentVersionName="2.0.0",
                    order=2,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp2-1234abc",
                    componentName="component2-1234abc",
                    componentVersionId="vers-1234abcd",
                    componentVersionName="3.0.0",
                    order=3,
                ),
            ],
            recipeVersionVolumeSize=TEST_RECIPE_VERSION_VOLUME_SIZE,
            recipeVersionArn="arn:aws:imagebuilder:us-east-1:123456789012:\
                            image-recipe/proserve-autosar-recipe/1.0.0",
            status=status,
            createDate="2023-11-30T00:00:00+00:00",
            createdBy="T000001",
            lastUpdateDate="2023-11-30T00:00:00+00:00",
            lastUpdatedBy="T000001",
        )

    return _get_test_recipe_version_with_specific_status


@pytest.fixture()
def get_test_recipe_version_with_specific_version_name_and_status(
    get_test_recipe_version_arn,
    get_test_recipe_version_component_arn,
):
    def _get_test_recipe_version_with_specific_version_name_and_status(
        version_name: str, status: recipe_version.RecipeVersionStatus
    ):
        return recipe_version.RecipeVersion(
            recipeId=TEST_RECIPE_ID,
            recipeVersionId=TEST_RECIPE_VERSION_ID,
            recipeVersionName=version_name,
            recipeName=TEST_RECIPE_NAME,
            recipeVersionDescription="Initial release",
            parentImageUpstreamId=TEST_AMI_ID,
            recipeComponentsVersions=[
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234jkl",
                    componentName="component-1234jkl",
                    componentVersionId="vers-1234jkl",
                    componentVersionName="1.0.0",
                    order=3,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234pqr",
                    componentName="component-1234pqr",
                    componentVersionId="vers-1234pqr",
                    componentVersionName="3.0.0",
                    order=1,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234mno",
                    componentName="component-1234mno",
                    componentVersionId="vers-1234mno",
                    componentVersionName="2.0.0",
                    order=2,
                ),
            ],
            parentImageId="image-12345",
            recipeVersionVolumeSize=TEST_RECIPE_VERSION_VOLUME_SIZE,
            recipeVersionArn=get_test_recipe_version_arn(version_name=version_name),
            recipeVersionComponentArn=get_test_recipe_version_component_arn(version_name=version_name),
            status=status,
            createDate="2023-11-30T00:00:00+00:00",
            createdBy="T000001",
            lastUpdateDate="2023-11-30T00:00:00+00:00",
            lastUpdatedBy="T000001",
        )

    return _get_test_recipe_version_with_specific_version_name_and_status


@pytest.fixture
def get_test_recipe_version_test_execution_with_specific_instance_id_and_status():
    def _get_test_recipe_version_test_execution_with_specific_instance_id_and_status(
        instance_id: str,
        instance_status: str,
        mock_recipe_version_object: recipe_version.RecipeVersion,
        mock_recipe_object: recipe.Recipe,
        status: recipe_version_test_execution.RecipeVersionTestExecutionStatus = recipe_version_test_execution.RecipeVersionTestExecutionStatus.Pending,
    ):
        return recipe_version_test_execution.RecipeVersionTestExecution(
            recipeVersionId=mock_recipe_version_object.recipeVersionId,
            testExecutionId=TEST_TEST_EXECUTION_ID,
            instanceId=instance_id,
            instanceArchitecture=mock_recipe_object.recipeArchitecture,
            instanceImageUpstreamId=mock_recipe_version_object.parentImageUpstreamId,
            instanceOsVersion=mock_recipe_object.recipeOsVersion,
            instancePlatform=mock_recipe_object.recipePlatform,
            instanceStatus=instance_status,
            createDate="2000-01-01",
            lastUpdateDate="2000-01-01",
            status=status,
        )

    return _get_test_recipe_version_test_execution_with_specific_instance_id_and_status


@pytest.fixture
def get_test_recipe_version_test_execution_with_specific_instance_id_architecture_os_version_and_platform():
    def _get_test_recipe_version_test_execution_with_specific_instance_id_architecture_os_version_and_platform(
        architecture: str,
        instance_id: str,
        os_version: str,
        platform: str,
        mock_recipe_version_object: recipe_version.RecipeVersion,
    ):
        return recipe_version_test_execution.RecipeVersionTestExecution(
            recipeVersionId=mock_recipe_version_object.recipeVersionId,
            testExecutionId=TEST_TEST_EXECUTION_ID,
            instanceId=instance_id,
            instanceArchitecture=architecture,
            instanceImageUpstreamId=mock_recipe_version_object.parentImageUpstreamId,
            instanceOsVersion=os_version,
            instancePlatform=platform,
            instanceStatus=recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.Connected.value,
            createDate="2000-01-01",
            lastUpdateDate="2000-01-01",
            status=recipe_version_test_execution.RecipeVersionTestExecutionStatus.Running.value,
        )

    return _get_test_recipe_version_test_execution_with_specific_instance_id_architecture_os_version_and_platform


@pytest.fixture()
def recipe_version_test_execution_repo_mock():
    return mock.create_autospec(spec=unit_of_work.GenericRepository, instance=True)


@pytest.fixture()
def check_recipe_version_testing_environment_launch_status_command_mock() -> (
    check_recipe_version_testing_environment_launch_status_command.CheckRecipeVersionTestingEnvironmentLaunchStatusCommand
):
    return check_recipe_version_testing_environment_launch_status_command.CheckRecipeVersionTestingEnvironmentLaunchStatusCommand(
        recipeVersionId=recipe_version_id_value_object.from_str(TEST_RECIPE_VERSION_ID),
        testExecutionId=recipe_version_test_execution_id_value_object.from_str(TEST_TEST_EXECUTION_ID),
    )


@pytest.fixture()
def check_recipe_version_testing_environment_setup_status_command_mock() -> (
    check_recipe_version_testing_environment_setup_status_command.CheckRecipeVersionTestingEnvironmentSetupStatusCommand
):
    return check_recipe_version_testing_environment_setup_status_command.CheckRecipeVersionTestingEnvironmentSetupStatusCommand(
        recipeVersionId=recipe_version_id_value_object.from_str(TEST_RECIPE_VERSION_ID),
        testExecutionId=recipe_version_test_execution_id_value_object.from_str(TEST_TEST_EXECUTION_ID),
    )


@pytest.fixture()
def check_recipe_version_testing_test_status_command_mock() -> (
    check_recipe_version_testing_test_status_command.CheckRecipeVersionTestingTestStatusCommand
):
    return check_recipe_version_testing_test_status_command.CheckRecipeVersionTestingTestStatusCommand(
        recipeVersionId=recipe_version_id_value_object.from_str(TEST_RECIPE_VERSION_ID),
        testExecutionId=recipe_version_test_execution_id_value_object.from_str(TEST_TEST_EXECUTION_ID),
    )


@pytest.fixture()
def create_recipe_version_command_mock(
    recipe_component_versions_mock,
) -> create_recipe_version_command.CreateRecipeVersionCommand:
    return create_recipe_version_command.CreateRecipeVersionCommand(
        projectId=project_id_value_object.from_str(TEST_PROJECT_ID),
        recipeId=recipe_id_value_object.from_str(TEST_RECIPE_ID),
        recipeComponentsVersions=recipe_component_versions_mock,
        recipeVersionDescription=recipe_version_description_value_object.from_str("Test description"),
        recipeVersionReleaseType=recipe_version_release_type_value_object.from_str("MAJOR"),
        recipeVersionVolumeSize=recipe_version_volume_size_value_object.from_str(TEST_RECIPE_VERSION_VOLUME_SIZE),
        recipeVersionIntegrations=[],
        createdBy=user_id_value_object.from_str("T123456"),
    )


@pytest.fixture()
def setup_recipe_version_testing_environment_command_mock() -> (
    setup_recipe_version_testing_environment_command.SetupRecipeVersionTestingEnvironmentCommand
):
    return setup_recipe_version_testing_environment_command.SetupRecipeVersionTestingEnvironmentCommand(
        recipeVersionId=recipe_version_id_value_object.from_str(TEST_RECIPE_VERSION_ID),
        testExecutionId=recipe_version_test_execution_id_value_object.from_str(TEST_TEST_EXECUTION_ID),
    )


@pytest.fixture()
def complete_recipe_version_testing_command_mock() -> (
    complete_recipe_version_testing_command.CompleteRecipeVersionTestingCommand
):
    return complete_recipe_version_testing_command.CompleteRecipeVersionTestingCommand(
        projectId=project_id_value_object.from_str(TEST_PROJECT_ID),
        recipeId=recipe_id_value_object.from_str(TEST_RECIPE_ID),
        recipeVersionId=recipe_version_id_value_object.from_str(TEST_RECIPE_VERSION_ID),
        testExecutionId=recipe_version_test_execution_id_value_object.from_str(TEST_TEST_EXECUTION_ID),
    )


@pytest.fixture()
def update_recipe_version_command_mock(
    recipe_component_versions_mock,
) -> update_recipe_version_command.UpdateRecipeVersionCommand:
    return update_recipe_version_command.UpdateRecipeVersionCommand(
        projectId=project_id_value_object.from_str(TEST_PROJECT_ID),
        recipeId=recipe_id_value_object.from_str(TEST_RECIPE_ID),
        recipeVersionId=recipe_version_id_value_object.from_str(TEST_RECIPE_VERSION_ID),
        recipeComponentsVersions=recipe_component_versions_mock,
        recipeVersionDescription=recipe_version_description_value_object.from_str("Second Release"),
        recipeVersionVolumeSize=recipe_version_volume_size_value_object.from_str(TEST_RECIPE_VERSION_VOLUME_SIZE),
        recipeVersionIntegrations=[],
        lastUpdatedBy=user_id_value_object.from_str("T123456"),
    )


@pytest.fixture()
def update_recipe_version_on_component_update_command_mock() -> (
    update_recipe_version_on_component_update_command.UpdateRecipeVersionOnComponentUpdateCommand
):
    return update_recipe_version_on_component_update_command.UpdateRecipeVersionOnComponentUpdateCommand(
        componentId=component_id_value_object.from_str(TEST_COMPONENT_ID),
        componentVersionId=component_version_id_value_object.from_str(TEST_COMPONENT_VERSION_ID),
        lastUpdatedBy=user_id_value_object.from_str("T123456"),
    )


@pytest.fixture()
def generic_repo_mock():
    return mock.create_autospec(spec=unit_of_work.GenericRepository, instance=True)


@pytest.fixture()
def get_retire_recipe_version_command_mock():
    def _get_retire_recipe_version_command_mock(
        user_roles: List[str] = [
            VirtualWorkbenchRoles.BetaUser,
            VirtualWorkbenchRoles.PlatformUser,
            VirtualWorkbenchRoles.ProductContributor,
        ]
    ):
        return retire_recipe_version_command.RetireRecipeVersionCommand(
            projectId=project_id_value_object.from_str(TEST_PROJECT_ID),
            recipeId=recipe_id_value_object.from_str(TEST_RECIPE_ID),
            recipeVersionId=recipe_version_id_value_object.from_str(TEST_RECIPE_VERSION_ID),
            userRoles=[user_role_value_object.from_str(user_role) for user_role in user_roles],
            lastUpdatedBy=user_id_value_object.from_str(TEST_USER_ID),
        )

    return _get_retire_recipe_version_command_mock


@pytest.fixture()
def get_retire_component_version_command_mock():
    def _get_retire_component_version_command_mock(
        user_roles: List[str] = [
            VirtualWorkbenchRoles.BetaUser,
            VirtualWorkbenchRoles.PlatformUser,
            VirtualWorkbenchRoles.ProductContributor,
        ]
    ):
        return retire_component_version_command.RetireComponentVersionCommand(
            componentId=component_id_value_object.from_str(TEST_COMPONENT_ID),
            componentVersionId=component_version_id_value_object.from_str(TEST_COMPONENT_VERSION_ID),
            userRoles=[user_role_value_object.from_str(user_role) for user_role in user_roles],
            lastUpdatedBy=user_id_value_object.from_str("T000001"),
        )

    return _get_retire_component_version_command_mock


@pytest.fixture()
def message_bus_mock():
    return mock.create_autospec(spec=message_bus.MessageBus)


@pytest.fixture()
def remove_recipe_version_command_mock(
    get_test_recipe_version_arn, get_test_recipe_version_component_arn
) -> remove_recipe_version_command.RemoveRecipeVersionCommand:
    return remove_recipe_version_command.RemoveRecipeVersionCommand(
        projectId=project_id_value_object.from_str(TEST_PROJECT_ID),
        recipeId=recipe_id_value_object.from_str(TEST_RECIPE_ID),
        recipeName=recipe_name_value_object.from_str(TEST_RECIPE_NAME),
        recipeVersionId=recipe_version_id_value_object.from_str(TEST_RECIPE_VERSION_ID),
        recipeVersionArn=recipe_version_arn_value_object.from_str(
            get_test_recipe_version_arn(version_name=TEST_RECIPE_VERSION_NAME)
        ),
        recipeVersionComponentArn=component_build_version_arn_value_object.from_str(
            get_test_recipe_version_component_arn(version_name=TEST_RECIPE_VERSION_NAME)
        ),
        recipeVersionName=recipe_version_name_value_object.from_str(TEST_RECIPE_VERSION_NAME),
        lastUpdatedBy=user_id_value_object.from_str(TEST_USER_ID),
    )


@pytest.fixture()
def remove_component_version_command_mock(
    get_test_component_version_arn,
) -> remove_component_version_command.RemoveComponentVersionCommand:
    return remove_component_version_command.RemoveComponentVersionCommand(
        componentId=component_id_value_object.from_str(TEST_COMPONENT_ID),
        componentVersionId=component_version_id_value_object.from_str(TEST_COMPONENT_VERSION_ID),
        componentBuildVersionArn=component_build_version_arn_value_object.from_str(
            get_test_component_version_arn(version_name="1.0.0")
        ),
    )


@pytest.fixture()
def get_share_component_command_mock():
    def _get_share_component_command_mock(user_roles: list[str] = None):
        if user_roles is None:
            user_roles = [
                VirtualWorkbenchRoles.Admin,
                VirtualWorkbenchRoles.ProductContributor,
            ]
        return share_component_command.ShareComponentCommand(
            projectIds=[project_id_value_object.from_str(m) for m in TEST_PROJECT_IDS],
            componentId=component_id_value_object.from_str(TEST_COMPONENT_ID),
            userRoles=[user_role_value_object.from_str(user_role) for user_role in user_roles],
        )

    return _get_share_component_command_mock


@pytest.fixture()
def uow_mock(generic_repo_mock):
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork, instance=True)
    uow_mock.get_repository.return_value = generic_repo_mock
    return uow_mock


@pytest.fixture()
def get_pipeline_creation_started_event():
    def _get_pipeline_creation_started_event(
        project_id: str = TEST_PROJECT_ID,
        pipeline_id: str = TEST_PIPELINE_ID,
    ) -> pipeline_creation_started.PipelineCreationStarted:
        return pipeline_creation_started.PipelineCreationStarted(
            projectId=project_id,
            pipelineId=pipeline_id,
        )

    return _get_pipeline_creation_started_event


@pytest.fixture()
def get_pipeline_update_started_event():
    def _get_pipeline_update_started_event(
        project_id: str = TEST_PROJECT_ID,
        pipeline_id: str = TEST_PIPELINE_ID,
    ) -> pipeline_update_started.PipelineUpdateStarted:
        return pipeline_update_started.PipelineUpdateStarted(
            projectId=project_id,
            pipelineId=pipeline_id,
        )

    return _get_pipeline_update_started_event


@pytest.fixture()
def get_pipeline_entity():
    def _get_pipeline_entity(
        project_id: str = TEST_PROJECT_ID,
        pipeline_id: str = TEST_PIPELINE_ID,
        build_instance_types: list[str] = TEST_BUILD_INSTANCE_TYPES,
        pipeline_description: str = TEST_PIPELINE_DESCRIPTION,
        pipeline_name: str = TEST_PIPELINE_NAME,
        pipeline_schedule: str = TEST_PIPELINE_SCHEDULE,
        recipe_id: str = TEST_RECIPE_ID,
        recipe_name: str = TEST_RECIPE_NAME,
        recipe_version_id: str = TEST_RECIPE_VERSION_ID,
        recipe_version_name: str = TEST_RECIPE_VERSION_NAME,
        status: pipeline.PipelineStatus = pipeline.PipelineStatus.Creating,
        distribution_config_arn: str | None = None,
        infrastructure_config_arn: str | None = None,
        pipeline_arn: str | None = None,
        product_id: str | None = None,
        created_date: str = TEST_DATE,
        last_updated_date: str = TEST_DATE,
        created_by: str = TEST_USER_ID,
        last_updated_by: str = TEST_USER_ID,
    ) -> pipeline.Pipeline:
        return pipeline.Pipeline(
            projectId=project_id,
            pipelineId=pipeline_id,
            buildInstanceTypes=build_instance_types,
            pipelineDescription=pipeline_description,
            pipelineName=pipeline_name,
            pipelineSchedule=pipeline_schedule,
            recipeId=recipe_id,
            recipeName=recipe_name,
            recipeVersionId=recipe_version_id,
            recipeVersionName=recipe_version_name,
            status=status,
            distributionConfigArn=distribution_config_arn,
            infrastructureConfigArn=infrastructure_config_arn,
            pipelineArn=pipeline_arn,
            productId=product_id,
            createDate=created_date,
            lastUpdateDate=last_updated_date,
            createdBy=created_by,
            lastUpdatedBy=last_updated_by,
        )

    return _get_pipeline_entity


@pytest.fixture()
def logger_mock():
    logger = mock.create_autospec(spec=logging.Logger)

    return logger


@pytest.fixture()
def pipeline_query_service_mock():
    pipeline_qry_srv = mock.create_autospec(spec=pipeline_query_service.PipelineQueryService)

    return pipeline_qry_srv


@pytest.fixture()
def pipeline_service_mock():
    pipeline_srv = mock.create_autospec(spec=pipeline_service.PipelineService)

    return pipeline_srv


@pytest.fixture()
def get_create_pipeline_command():
    def _get_create_pipeline_command(
        project_id: str = TEST_PROJECT_ID,
        build_instance_types: list[str] = TEST_BUILD_INSTANCE_TYPES,
        pipeline_description: str = TEST_PIPELINE_DESCRIPTION,
        pipeline_name: str = TEST_PIPELINE_NAME,
        pipeline_schedule: str = TEST_PIPELINE_SCHEDULE,
        recipe_id: str = TEST_RECIPE_ID,
        recipe_version_id: str = TEST_RECIPE_VERSION_ID,
        created_by: str = TEST_USER_ID,
        product_id: str | None = None,
    ) -> create_pipeline_command.CreatePipelineCommand:
        return create_pipeline_command.CreatePipelineCommand(
            projectId=project_id_value_object.from_str(project_id),
            buildInstanceTypes=pipeline_build_instance_types_value_object.from_list(build_instance_types),
            pipelineDescription=pipeline_description_value_object.from_str(pipeline_description),
            pipelineName=pipeline_name_value_object.from_str(pipeline_name),
            pipelineSchedule=pipeline_schedule_value_object.from_str(pipeline_schedule),
            recipeId=recipe_id_value_object.from_str(recipe_id),
            recipeVersionId=recipe_version_id_value_object.from_str(recipe_version_id),
            createdBy=user_id_value_object.from_str(created_by),
            productId=(product_id_value_object.from_str(product_id) if product_id else None),
        )

    return _get_create_pipeline_command


@pytest.fixture()
def get_deploy_pipeline_command():
    def _get_deploy_pipeline_command(
        project_id: str = TEST_PROJECT_ID,
        pipeline_id: str = TEST_PIPELINE_ID,
    ) -> deploy_pipeline_command.DeployPipelineCommand:
        return deploy_pipeline_command.DeployPipelineCommand(
            projectId=project_id_value_object.from_str(project_id),
            pipelineId=pipeline_id_value_object.from_str(pipeline_id),
        )

    return _get_deploy_pipeline_command


@pytest.fixture()
def get_remove_pipeline_command(
    get_test_pipeline_distribution_config_arn,
    get_test_pipeline_infrastructure_config_arn,
    get_test_pipeline_arn,
):
    def _get_remove_pipeline_command(
        project_id: str = TEST_PROJECT_ID,
        pipeline_id: str = TEST_PIPELINE_ID,
        distribution_config_arn: str | None = get_test_pipeline_distribution_config_arn(),
        infrastructure_config_arn: str | None = get_test_pipeline_infrastructure_config_arn(),
        pipeline_arn: str | None = get_test_pipeline_arn(),
    ) -> remove_pipeline_command.RemovePipelineCommand:
        return remove_pipeline_command.RemovePipelineCommand(
            projectId=project_id_value_object.from_str(project_id),
            pipelineId=pipeline_id_value_object.from_str(pipeline_id),
            distributionConfigArn=(
                pipeline_distribution_config_arn_value_object.from_str(distribution_config_arn)
                if distribution_config_arn
                else None
            ),
            infrastructureConfigArn=(
                pipeline_infrastructure_config_arn_value_object.from_str(infrastructure_config_arn)
                if infrastructure_config_arn
                else None
            ),
            pipelineArn=(pipeline_arn_value_object.from_str(pipeline_arn) if pipeline_arn else None),
        )

    return _get_remove_pipeline_command


@pytest.fixture()
def get_retire_pipeline_command():
    def _get_retire_pipeline_command(
        project_id: str = TEST_PROJECT_ID,
        pipeline_id: str = TEST_PIPELINE_ID,
        last_update_by: str = TEST_USER_ID,
    ) -> retire_pipeline_command.RetirePipelineCommand:
        return retire_pipeline_command.RetirePipelineCommand(
            projectId=project_id_value_object.from_str(project_id),
            pipelineId=pipeline_id_value_object.from_str(pipeline_id),
            lastUpdateBy=user_id_value_object.from_str(last_update_by),
        )

    return _get_retire_pipeline_command


@pytest.fixture()
def get_update_pipeline_command():
    def _get_update_pipeline_command(
        pipeline_id: str = TEST_PIPELINE_ID,
        project_id: str = TEST_PROJECT_ID,
        pipeline_schedule: str | None = None,
        build_instance_types: list[str] | None = None,
        recipe_version_id: str | None = None,
        product_id: str | None = None,
        last_updated_by: str = TEST_USER_ID,
    ) -> update_pipeline_command.UpdatePipelineCommand:
        kwargs = {}
        if build_instance_types:
            kwargs["buildInstanceTypes"] = pipeline_build_instance_types_value_object.from_list(build_instance_types)
        if pipeline_schedule:
            kwargs["pipelineSchedule"] = pipeline_schedule_value_object.from_str(pipeline_schedule)
        if recipe_version_id:
            kwargs["recipeVersionId"] = recipe_version_id_value_object.from_str(recipe_version_id)
        if product_id:
            kwargs["productId"] = product_id_value_object.from_str(product_id)
        return update_pipeline_command.UpdatePipelineCommand(
            pipelineId=pipeline_id_value_object.from_str(pipeline_id),
            projectId=project_id_value_object.from_str(project_id),
            lastUpdatedBy=user_id_value_object.from_str(last_updated_by),
            **kwargs,
        )

    return _get_update_pipeline_command


@pytest.fixture()
def get_image_entity(get_test_image_build_version_arn):
    def _get_image_entity(
        project_id: str = TEST_PROJECT_ID,
        image_id: str = TEST_IMAGE_ID,
        image_build_version: int = TEST_IMAGE_BUILD_VERSION,
        pipeline_id: str = TEST_PIPELINE_ID,
        pipeline_name: str = TEST_PIPELINE_NAME,
        recipe_id: str = TEST_RECIPE_ID,
        recipe_name: str = TEST_RECIPE_NAME,
        recipe_version_id: str = TEST_RECIPE_VERSION_ID,
        recipe_version_name: str = TEST_RECIPE_VERSION_NAME,
        status: image.ImageStatus = image.ImageStatus.Creating,
        image_upstream_id: str | None = None,
        created_date: str = TEST_DATE,
        last_updated_date: str = TEST_DATE,
    ) -> image.Image:
        return image.Image(
            projectId=project_id,
            imageId=image_id,
            imageBuildVersion=image_build_version,
            imageBuildVersionArn=get_test_image_build_version_arn(
                build_version=image_build_version,
                recipe_name=recipe_name,
                version_name=recipe_version_name,
            ),
            pipelineId=pipeline_id,
            pipelineName=pipeline_name,
            recipeId=recipe_id,
            recipeName=recipe_name,
            recipeVersionId=recipe_version_id,
            recipeVersionName=recipe_version_name,
            status=status,
            imageUpstreamId=image_upstream_id,
            createDate=created_date,
            lastUpdateDate=last_updated_date,
        )

    return _get_image_entity


@pytest.fixture()
def get_create_image_command():
    def _get_create_image_command(
        project_id: str = TEST_PROJECT_ID,
        pipeline_id: str = TEST_PIPELINE_ID,
    ) -> create_image_command.CreateImageCommand:
        return create_image_command.CreateImageCommand(
            projectId=project_id_value_object.from_str(project_id),
            pipelineId=pipeline_id_value_object.from_str(pipeline_id),
        )

    return _get_create_image_command


@pytest.fixture()
def get_register_image_command(get_test_image_build_version_arn):
    def _get_register_image_command(
        image_build_version: int = TEST_IMAGE_BUILD_VERSION,
        image_status: image.ImageStatus = image.ImageStatus.Created,
        image_upstream_id: str = TEST_AMI_ID,
        pipeline_id: str = TEST_PIPELINE_ID,
        recipe_name: str = TEST_RECIPE_NAME,
        recipe_version_name: str = TEST_RECIPE_VERSION_NAME,
    ) -> register_image_command.RegisterImageCommand:
        return register_image_command.RegisterImageCommand(
            imageBuildVersionArn=image_build_version_arn_value_object.from_str(
                get_test_image_build_version_arn(
                    build_version=image_build_version,
                    recipe_name=recipe_name,
                    version_name=recipe_version_name,
                )
            ),
            imageStatus=image_status_value_object.from_str(image_status),
            imageUpstreamId=(image_upstream_id_value_object.from_str(image_upstream_id) if image_upstream_id else None),
            pipelineId=pipeline_id_value_object.from_str(pipeline_id),
        )

    return _get_register_image_command


@pytest.fixture()
def register_automated_image_command_mock() -> register_automated_image_command.RegisterAutomatedImageCommand:
    return register_automated_image_command.RegisterAutomatedImageCommand(
        amiId=ami_id_value_object.from_str(TEST_AMI_ID),
        productId=product_id_value_object.from_str(TEST_PRODUCT_ID),
        projectId=project_id_value_object.from_str(TEST_PROJECT_ID),
        pipelineId=pipeline_id_value_object.from_str(TEST_PIPELINE_ID),
        productVersionReleaseType=version_release_type_value_object.from_str("MINOR"),
        userId=user_id_value_object.from_str(TEST_USER_ID),
    )


@pytest.fixture()
def update_component_version_without_dependencies_command_mock(
    get_test_component_yaml_definition, get_test_project_id
) -> update_component_version_command.UpdateComponentVersionCommand:
    return update_component_version_command.UpdateComponentVersionCommand(
        componentId=component_id_value_object.from_str(TEST_COMPONENT_ID),
        componentVersionId=component_version_id_value_object.from_str(TEST_COMPONENT_VERSION_ID),
        componentVersionDescription=component_version_description_value_object.from_str("Test description"),
        componentVersionDependencies=component_version_dependencies_value_object.from_list(list()),
        componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
            get_test_component_yaml_definition()
        ),
        softwareVendor=component_software_vendor_value_object.from_str("vector"),
        softwareVersion=component_software_version_value_object.from_str("1.0.0"),
        lastUpdatedBy=user_id_value_object.from_str(TEST_USER_ID),
        projectId=project_id_value_object.from_str(get_test_project_id),
    )


@pytest.fixture()
def get_mock_components_versions_list_with_dependencies():
    def _get_mock_components_versions_list_with_dependencies(
        dependencies_list_length: int = 3,
    ):
        main_component = component_version.ComponentVersion(
            componentId=TEST_COMPONENT_ID,
            componentName=TEST_COMPONENT_NAME,
            componentVersionId=TEST_COMPONENT_VERSION_ID,
            componentVersionName="1.0.0-rc.1",
            componentVersionDescription="Test component version",
            componentBuildVersionArn=f"arn:aws:imagebuilder:us-east-1:123456789012:component/{TEST_COMPONENT_ID}/1.0.0-rc.1/1",
            componentVersionS3Uri=f"s3://test-component-bucket/{TEST_COMPONENT_ID}/1.0.0-rc.1/component.yaml",
            componentPlatform="Linux",
            componentSupportedArchitectures=["amd64", "arm64"],
            componentSupportedOsVersions=["Ubuntu 24"],
            softwareVendor="Vector",
            softwareVersion="1.0.0",
            status="VALIDATED",
            createDate="2024-01-11",
            createdBy="2024-01-11",
            lastUpdateDate="2024-01-11",
            lastUpdatedBy="T0000001",
            associatedComponentsVersions=[
                ComponentVersionEntry(
                    componentId=f"comp-{i}",
                    componentName=f"component-{i}",
                    componentVersionId=f"vers-{i}",
                    componentVersionName="1.0.0-rc.1",
                    order=1,
                )
                for i in range(dependencies_list_length)
            ],
        )
        components_list = [main_component]

        # Create one component version entity for each associated component version of the main component
        for i in range(dependencies_list_length):
            components_list.append(
                component_version.ComponentVersion(
                    componentId=f"comp-{i}",
                    componentName=f"component-{i}",
                    componentVersionId=f"vers-{i}",
                    componentVersionName="1.0.0-rc.1",
                    componentVersionDescription="Test component version",
                    componentBuildVersionArn=f"arn:aws:imagebuilder:us-east-1:123456789012:component/comp-{i}/1.0.0-rc.1/1",
                    componentVersionS3Uri=f"s3://test-component-bucket/comp-{i}/1.0.0-rc.1/component.yaml",
                    componentPlatform="Linux",
                    componentSupportedArchitectures=["amd64", "arm64"],
                    componentSupportedOsVersions=["Ubuntu 24"],
                    softwareVendor="Vector",
                    softwareVersion="1.0.0",
                    componentVersionDependencies=[
                        ComponentVersionEntry(
                            componentId=TEST_COMPONENT_ID,
                            componentName=TEST_COMPONENT_NAME,
                            componentVersionId=TEST_COMPONENT_VERSION_ID,
                            componentVersionName="1.0.0-rc.1",
                            order=1,
                        )
                    ],
                    status="VALIDATED",
                    createDate="2024-01-11",
                    createdBy="2024-01-11",
                    lastUpdateDate="2024-01-11",
                    lastUpdatedBy="T0000001",
                )
            )

        return components_list

    return _get_mock_components_versions_list_with_dependencies


@pytest.fixture()
def get_recipe_version_with_rc_component(mock_recipe_object, mock_recipe_version_object):
    def _get_recipe_version_with_rc_component(
        component_id: str = "comp-1234abcd",
        component_name: str = "test-component",
        component_version_id: str = "vers-1234abcd",
        component_version_name: str = "1.0.0-rc2",
    ):
        rec = recipe_version.RecipeVersion(
            recipeId=mock_recipe_object.recipeId,
            recipeVersionId=mock_recipe_version_object.recipeVersionId,
            recipeVersionName=mock_recipe_version_object.recipeVersionName,
            recipeName=mock_recipe_object.recipeName,
            recipeVersionDescription=mock_recipe_version_object.recipeVersionDescription,
            recipeComponentsVersions=[
                component_version_entry.ComponentVersionEntry(
                    componentId=component_id,
                    componentName=component_name,
                    componentVersionId=component_version_id,
                    componentVersionName=component_version_name,
                    order=1,
                )
            ],
            status=recipe_version.RecipeVersionStatus.Validated,
            parentImageUpstreamId=mock_recipe_version_object.parentImageUpstreamId,
            recipeVersionVolumeSize=mock_recipe_version_object.recipeVersionVolumeSize,
            createDate=mock_recipe_version_object.createDate,
            createdBy=mock_recipe_version_object.createdBy,
            lastUpdateDate=mock_recipe_version_object.lastUpdateDate,
            lastUpdatedBy=mock_recipe_version_object.lastUpdatedBy,
        )
        return rec

    return _get_recipe_version_with_rc_component


@pytest.fixture()
def publishing_qry_svc_mock():
    qry_svc = mock.create_autospec(spec=publishing_query_service.PublishingQueryService)
    return qry_svc


@pytest.fixture(autouse=True)
def frozen_time():
    with freeze_time("2025-01-01 12:00:00+00:00"):
        yield


@pytest.fixture()
def get_test_mandatory_components_list_with_positioned_components():
    def _get_test_mandatory_components_list_with_positioned_components():
        return mandatory_components_list.MandatoryComponentsList(
            mandatoryComponentsListArchitecture=TEST_ARCHITECTURE,
            mandatoryComponentsListOsVersion=TEST_OS_VERSION,
            mandatoryComponentsListPlatform=TEST_ARCHITECTURE,
            mandatoryComponentsVersions=[
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-prepend-1",
                    componentName="PrependComponent1",
                    componentVersionId="vers-prepend-1",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-prepend-2",
                    componentName="PrependComponent2",
                    componentVersionId="vers-prepend-2",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-append-1",
                    componentName="AppendComponent1",
                    componentVersionId="vers-append-1",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Append,
                ),
            ],
            createDate="2023-10-27T00:00:00+00:00",
            createdBy="T000001",
            lastUpdateDate="2023-10-27T00:00:00+00:00",
            lastUpdatedBy="T000001",
        )

    return _get_test_mandatory_components_list_with_positioned_components


@pytest.fixture()
def get_test_mandatory_components_list_with_only_prepended():
    def _get_test_mandatory_components_list_with_only_prepended():
        return mandatory_components_list.MandatoryComponentsList(
            mandatoryComponentsListArchitecture=TEST_ARCHITECTURE,
            mandatoryComponentsListOsVersion=TEST_OS_VERSION,
            mandatoryComponentsListPlatform=TEST_ARCHITECTURE,
            mandatoryComponentsVersions=[
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-prepend-1",
                    componentName="PrependComponent1",
                    componentVersionId="vers-prepend-1",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-prepend-2",
                    componentName="PrependComponent2",
                    componentVersionId="vers-prepend-2",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
            ],
            createDate="2023-10-27T00:00:00+00:00",
            createdBy="T000001",
            lastUpdateDate="2023-10-27T00:00:00+00:00",
            lastUpdatedBy="T000001",
        )

    return _get_test_mandatory_components_list_with_only_prepended


@pytest.fixture()
def get_test_mandatory_components_list_with_only_appended():
    def _get_test_mandatory_components_list_with_only_appended():
        return mandatory_components_list.MandatoryComponentsList(
            mandatoryComponentsListArchitecture=TEST_ARCHITECTURE,
            mandatoryComponentsListOsVersion=TEST_OS_VERSION,
            mandatoryComponentsListPlatform=TEST_ARCHITECTURE,
            mandatoryComponentsVersions=[
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-append-1",
                    componentName="AppendComponent1",
                    componentVersionId="vers-append-1",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Append,
                ),
            ],
            createDate="2023-10-27T00:00:00+00:00",
            createdBy="T000001",
            lastUpdateDate="2023-10-27T00:00:00+00:00",
            lastUpdatedBy="T000001",
        )

    return _get_test_mandatory_components_list_with_only_appended


@pytest.fixture()
def create_recipe_version_command_with_duplicate_mandatory_component(
    get_test_project_id,
    get_test_recipe_id,
):
    return create_recipe_version_command.CreateRecipeVersionCommand(
        projectId=project_id_value_object.from_str(get_test_project_id),
        recipeId=recipe_id_value_object.from_str(get_test_recipe_id),
        recipeVersionDescription=recipe_version_description_value_object.from_str("Test description"),
        recipeVersionReleaseType=recipe_version_release_type_value_object.from_str(
            recipe_version.RecipeVersionReleaseType.Minor.value
        ),
        recipeVersionVolumeSize=recipe_version_volume_size_value_object.from_str("8"),
        recipeComponentsVersions=recipe_version_components_versions_value_object.from_list(
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-prepend-1",  # Duplicate with mandatory component
                    componentName="PrependComponent1",
                    componentVersionId="vers-prepend-1",
                    componentVersionName="1.0.0",
                    order=1,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="3.0.0",
                    order=2,
                ),
            ]
        ),
        recipeVersionIntegrations=[],
        createdBy=user_id_value_object.from_str("T000001"),
    )


@pytest.fixture()
def update_recipe_version_command_with_duplicate_mandatory_component(
    get_test_project_id,
    get_test_recipe_id,
    get_test_recipe_version_id,
):
    return update_recipe_version_command.UpdateRecipeVersionCommand(
        projectId=project_id_value_object.from_str(get_test_project_id),
        recipeId=recipe_id_value_object.from_str(get_test_recipe_id),
        recipeVersionId=recipe_version_id_value_object.from_str(get_test_recipe_version_id),
        recipeVersionDescription=recipe_version_description_value_object.from_str("Test description"),
        recipeComponentsVersions=recipe_version_components_versions_value_object.from_list(
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-prepend-1",  # Duplicate with mandatory component
                    componentName="PrependComponent1",
                    componentVersionId="vers-prepend-1",
                    componentVersionName="1.0.0",
                    order=1,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="3.0.0",
                    order=2,
                ),
            ]
        ),
        recipeVersionVolumeSize=recipe_version_volume_size_value_object.from_str("8"),
        lastUpdatedBy=user_id_value_object.from_str("T000001"),
    )
