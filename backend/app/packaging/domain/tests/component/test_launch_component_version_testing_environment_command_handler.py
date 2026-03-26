from itertools import product

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component import (
    launch_component_version_testing_environment_command_handler,
)
from app.packaging.domain.commands.component import (
    launch_component_version_testing_environment_command,
)
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import (
    component_version,
    component_version_test_execution,
)
from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import (
    component_version_id_value_object,
)
from app.packaging.domain.value_objects.component_version_test_execution import (
    component_version_test_execution_id_value_object,
)

TEST_COMPONENT_ID = "comp-1234abcd"
TEST_COMPONENT_VERSION_ID = "vers-1234abcd"
TEST_TEST_EXECUTION_ID = "c0220642-ced2-4f46-bea3-1601a70b5c55"


@pytest.fixture()
def launch_component_version_testing_environment_command_mock() -> (
    launch_component_version_testing_environment_command.LaunchComponentVersionTestingEnvironmentCommand
):
    return launch_component_version_testing_environment_command.LaunchComponentVersionTestingEnvironmentCommand(
        componentId=component_id_value_object.from_str(TEST_COMPONENT_ID),
        componentVersionId=component_version_id_value_object.from_str(TEST_COMPONENT_VERSION_ID),
        testExecutionId=component_version_test_execution_id_value_object.from_str(TEST_TEST_EXECUTION_ID),
    )


@pytest.mark.parametrize(
    "platform, supported_architectures, supported_os_versions, instance_types, image_upstream_ids, instance_ids",
    (
        (
            "Linux",
            ["amd64"],
            ["Ubuntu 24"],
            ["m8i.2xlarge"],
            ["ami-01234567890abcdef"],
            ["i-01234567890abcdef"],
        ),
        (
            "Linux",
            ["amd64", "arm64"],
            ["Ubuntu 24"],
            ["m8i.2xlarge", "m8g.2xlarge"],
            ["ami-01234567890abcdef", "ami-56789012345abcdef"],
            ["i-01234567890abcdef", "i-56789012345abcdef"],
        ),
        (
            "Windows",
            ["amd64"],
            ["Microsoft Windows Server 2025"],
            ["m8i.2xlarge"],
            ["ami-01234567890abcdef"],
            ["i-01234567890abcdef"],
        ),
        (
            "Windows",
            ["amd64"],
            ["Microsoft Windows Server 2025"],
            ["m8i.2xlarge"],
            ["ami-01234567890abcdef"],
            ["i-01234567890abcdef"],
        ),
    ),
)
@freeze_time("2023-09-29")
def test_handle_should_launch_component_version_testing(
    component_query_service_mock,
    component_version_testing_service_mock,
    get_test_component_with_specific_platform_architecture_and_os_version,
    launch_component_version_testing_environment_command_mock,
    generic_repo_mock,
    uow_mock,
    platform,
    supported_architectures,
    supported_os_versions,
    image_upstream_ids,
    instance_types,
    instance_ids,
):
    # ARRANGE
    component_query_service_mock.get_component.return_value = (
        get_test_component_with_specific_platform_architecture_and_os_version(
            platform=platform,
            supported_architectures=supported_architectures,
            supported_os_versions=supported_os_versions,
        )
    )
    component_version_testing_service_mock.get_testing_environment_image_upstream_id.side_effect = image_upstream_ids
    component_version_testing_service_mock.get_testing_environment_instance_type.side_effect = instance_types
    component_version_testing_service_mock.launch_testing_environment.side_effect = instance_ids

    # ACT
    launch_component_version_testing_environment_command_handler.handle(
        command=launch_component_version_testing_environment_command_mock,
        component_qry_srv=component_query_service_mock,
        component_version_testing_srv=component_version_testing_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_called_once_with(
        component_version.ComponentVersionPrimaryKey(
            componentId=launch_component_version_testing_environment_command_mock.componentId.value,
            componentVersionId=launch_component_version_testing_environment_command_mock.componentVersionId.value,
        ),
        status=component_version.ComponentVersionStatus.Testing,
    )
    for index, value in enumerate(product(supported_architectures, supported_os_versions)):
        architecture = value[0]
        image_upstream_id = image_upstream_ids[index]
        instance_type = instance_types[index]
        instance_id = instance_ids[index]
        os_version = value[1]

        component_version_testing_service_mock.get_testing_environment_image_upstream_id.assert_any_call(
            architecture=architecture,
            platform=platform,
            os_version=os_version,
        )
        component_version_testing_service_mock.get_testing_environment_instance_type.assert_any_call(
            architecture=architecture,
            platform=platform,
            os_version=os_version,
        )
        component_version_testing_service_mock.launch_testing_environment.assert_any_call(
            image_upstream_id=image_upstream_id, instance_type=instance_type
        )
        generic_repo_mock.add.assert_any_call(
            component_version_test_execution.ComponentVersionTestExecution(
                componentVersionId=TEST_COMPONENT_VERSION_ID,
                testExecutionId=TEST_TEST_EXECUTION_ID,
                instanceId=instance_id,
                instanceArchitecture=architecture,
                instanceImageUpstreamId=image_upstream_id,
                instanceOsVersion=os_version,
                instancePlatform=platform,
                instanceStatus=component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Disconnected.value,
                createDate="2023-09-29T00:00:00+00:00",
                lastUpdateDate="2023-09-29T00:00:00+00:00",
                status=component_version_test_execution.ComponentVersionTestExecutionStatus.Pending.value,
            )
        )
    uow_mock.commit.assert_called()


def test_handle_should_raise_exception_when_component_is_none(
    launch_component_version_testing_environment_command_mock,
    component_query_service_mock,
    component_version_testing_service_mock,
    uow_mock,
):
    # ARRANGE
    component_query_service_mock.get_component.return_value = None

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        launch_component_version_testing_environment_command_handler.handle(
            command=launch_component_version_testing_environment_command_mock,
            component_qry_srv=component_query_service_mock,
            component_version_testing_srv=component_version_testing_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Component {launch_component_version_testing_environment_command_mock.componentId.value} does not exist."
    )
