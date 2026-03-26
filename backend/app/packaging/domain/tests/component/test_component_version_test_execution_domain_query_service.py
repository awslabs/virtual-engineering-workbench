import assertpy
import pytest

from app.packaging.domain.model.component import component_version_test_execution
from app.packaging.domain.query_services import (
    component_version_test_execution_domain_query_service,
)
from app.packaging.domain.value_objects.component_version import (
    component_version_id_value_object,
)
from app.packaging.domain.value_objects.component_version_test_execution import (
    component_version_test_execution_id_value_object,
    component_version_test_execution_instance_id_value_object,
)

TEST_COMPONENT_VERSION_ID = "version-1"
TEST_TEST_EXECUTION_ID = "c0220642-ced2-4f46-bea3-1601a70b5c55"
TEST_INSTANCE_ID = "i-01234567890abcdef"
TEST_COMMAND_ID = "750ac01c-c984-4ea0-b16f-d79819930140"
TEST_S3_LOG_LOCATION = "s3://mytestbucket/comp-123456/vers-12345/i-12345679012/console.log"
TEST_S3_PRESIGNED_URL = "https://example.com"


@pytest.fixture
def get_test_component_version_test_execution():
    def _get_test_component_version_test_execution(
        component_version_id: str = TEST_COMPONENT_VERSION_ID,
        test_execution_id: str = TEST_TEST_EXECUTION_ID,
        instance_id: str = TEST_INSTANCE_ID,
        setup_command_status: str = "SUCCESS",
        test_command_status: str = "SUCCESS",
        create_date: str = "2000-01-01T00:00:00.00000+00:00",
        last_update_date: str = "2000-01-01T00:00:00.00000+00:00",
        status: component_version_test_execution.ComponentVersionTestExecutionStatus = component_version_test_execution.ComponentVersionTestExecutionStatus.Pending.value,
    ):
        return component_version_test_execution.ComponentVersionTestExecution(
            componentVersionId=component_version_id,
            testExecutionId=test_execution_id,
            instanceId=instance_id,
            instanceArchitecture="amd64",
            instanceImageUpstreamId="ami-01234567890abcdef",
            instanceOsVersion="Ubuntu 24",
            instancePlatform="Linux",
            instanceStatus="CONNECTED",
            setupCommandId="750ac01c-c984-4ea0-b16f-d79819930140",
            setupCommandStatus=setup_command_status,
            testCommandId="750ac01c-c984-4ea0-b16f-d79819930140",
            testCommandStatus=test_command_status,
            createDate=create_date,
            lastUpdateDate=last_update_date,
            status=status,
            s3LogLocation=TEST_S3_LOG_LOCATION,
        )

    return _get_test_component_version_test_execution


@pytest.mark.parametrize(
    "component_version_id, test_execution_id, instance_id,  setup_command_status, test_command_status, create_date, last_update_date, status",
    [
        (
            TEST_COMPONENT_VERSION_ID,
            TEST_TEST_EXECUTION_ID,
            TEST_INSTANCE_ID,
            None,
            None,
            "2000-01-01T00:00:00.00000+00:00",
            "2000-01-01T00:00:00.00000+00:00",
            component_version_test_execution.ComponentVersionTestExecutionStatus.Pending.value,
        ),
    ],
)
def test_should_return_a_specific_component_version_test_execution_logs_url(
    component_version_test_execution_query_service_mock,
    s3_service_mock,
    get_test_component_version_test_execution,
    component_version_id,
    test_execution_id,
    instance_id,
    setup_command_status,
    test_command_status,
    create_date,
    last_update_date,
    status,
):
    # ARRANGE
    component_version_test_execution_query_service_mock.get_component_version_test_execution.return_value = (
        get_test_component_version_test_execution(
            component_version_id=component_version_id,
            test_execution_id=test_execution_id,
            instance_id=instance_id,
            setup_command_status=setup_command_status,
            test_command_status=test_command_status,
            create_date=create_date,
            last_update_date=last_update_date,
            status=status,
        )
    )
    s3_service_mock.get_s3_presigned_url.return_value = TEST_S3_PRESIGNED_URL
    test_executions_domain_query_service = (
        component_version_test_execution_domain_query_service.ComponentVersionTestExecutionDomainQueryService(
            component_version_test_execution_qry_srv=component_version_test_execution_query_service_mock,
            component_version_definition_srv=s3_service_mock,
        )
    )

    # ACT
    s3_presigned_url = test_executions_domain_query_service.get_component_version_test_execution_logs_url(
        version_id=component_version_id_value_object.from_str(component_version_id),
        test_execution_id=component_version_test_execution_id_value_object.from_str(test_execution_id),
        instance_id=component_version_test_execution_instance_id_value_object.from_str(instance_id),
    )

    # ASSERT
    assertpy.assert_that(s3_presigned_url).is_equal_to(TEST_S3_PRESIGNED_URL)


def test_should_return_the_correct_component_version_test_execution_summaries(
    component_version_test_execution_query_service_mock,
    get_test_component_version_test_execution,
    s3_service_mock,
):
    # ARRANGE
    component_version_test_execution_query_service_mock.get_component_version_test_executions.side_effect = [
        [get_test_component_version_test_execution()],
        [
            get_test_component_version_test_execution(component_version_id="version-2"),
            get_test_component_version_test_execution(
                component_version_id="version-2",
                test_execution_id="09776d9f-349f-4f50-8ba4-b862d8eaa044",
            ),
            get_test_component_version_test_execution(
                component_version_id="version-2", instance_id="i-56789012345ghijkl"
            ),
            get_test_component_version_test_execution(
                component_version_id="version-2",
                test_execution_id="09776d9f-349f-4f50-8ba4-b862d8eaa044",
                instance_id="i-56789012345ghijkl",
            ),
        ],
        [],
    ]
    test_executions_domain_query_service = (
        component_version_test_execution_domain_query_service.ComponentVersionTestExecutionDomainQueryService(
            component_version_test_execution_qry_srv=component_version_test_execution_query_service_mock,
            component_version_definition_srv=s3_service_mock,
        )
    )

    # ACT
    component_version_test_execution_summaries_1 = (
        test_executions_domain_query_service.get_component_version_test_execution_summaries(
            version_id=component_version_id_value_object.from_str("version-1")
        )
    )
    component_version_test_execution_summaries_2 = (
        test_executions_domain_query_service.get_component_version_test_execution_summaries(
            version_id=component_version_id_value_object.from_str("version-2")
        )
    )
    component_version_test_execution_summaries_3 = (
        test_executions_domain_query_service.get_component_version_test_execution_summaries(
            version_id=component_version_id_value_object.from_str("version-3")
        )
    )

    # ASSERT
    assertpy.assert_that(component_version_test_execution_summaries_1).is_not_none()
    assertpy.assert_that(component_version_test_execution_summaries_2).is_not_none()
    assertpy.assert_that(component_version_test_execution_summaries_3).is_not_none()
    assertpy.assert_that(len(component_version_test_execution_summaries_1)).is_equal_to(1)
    assertpy.assert_that(len(component_version_test_execution_summaries_2)).is_equal_to(4)
    assertpy.assert_that(len(component_version_test_execution_summaries_3)).is_equal_to(0)
