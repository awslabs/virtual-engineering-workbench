import assertpy

from app.packaging.adapters.repository import dynamo_entity_config
from app.packaging.adapters.tests.conftest import GlobalVariables
from app.packaging.domain.model.component import component_version_test_execution


def fill_db_with_test_executions(
    backend_app_table,
    component_version_test_executions: list[component_version_test_execution.ComponentVersionTestExecution],
):
    for test_execution in component_version_test_executions:
        backend_app_table.put_item(
            Item={
                "PK": f"{dynamo_entity_config.DBPrefix.Version}#{test_execution.componentVersionId}",
                "SK": "#".join(
                    [
                        dynamo_entity_config.DBPrefix.Execution,
                        test_execution.testExecutionId,
                        dynamo_entity_config.DBPrefix.Instance,
                        test_execution.instanceId,
                    ]
                ),
                **test_execution.model_dump(),
            }
        )


def test_get_component_version_test_executions(
    get_mock_component_version_test_execution,
    backend_app_table,
    get_dynamodb_component_version_test_execution_query_service,
):
    # ARRANGE
    query_service = get_dynamodb_component_version_test_execution_query_service
    fill_db_with_test_executions(
        backend_app_table,
        [
            get_mock_component_version_test_execution(),
            get_mock_component_version_test_execution(component_version_id="version-2"),
            get_mock_component_version_test_execution(
                component_version_id="version-2", test_execution_id="09776d9f-349f-4f50-8ba4-b862d8eaa044"
            ),
            get_mock_component_version_test_execution(
                component_version_id="version-2", instance_id="i-56789012345ghijkl"
            ),
            get_mock_component_version_test_execution(
                component_version_id="version-2",
                test_execution_id="09776d9f-349f-4f50-8ba4-b862d8eaa044",
                instance_id="i-56789012345ghijkl",
            ),
        ],
    )

    # ACT
    component_version_test_executions_1 = query_service.get_component_version_test_executions(
        version_id=GlobalVariables.TEST_COMPONENT_VERSION_ID.value
    )
    component_version_test_executions_2 = query_service.get_component_version_test_executions(version_id="version-2")
    component_version_test_executions_3 = query_service.get_component_version_test_executions(version_id="version-3")

    # ASSERT
    assertpy.assert_that(component_version_test_executions_1).is_not_none()
    assertpy.assert_that(component_version_test_executions_2).is_not_none()
    assertpy.assert_that(component_version_test_executions_3).is_not_none()
    assertpy.assert_that(len(component_version_test_executions_1)).is_equal_to(1)
    assertpy.assert_that(len(component_version_test_executions_2)).is_equal_to(4)
    assertpy.assert_that(len(component_version_test_executions_3)).is_equal_to(0)


def test_get_component_version_test_execution(
    get_dynamodb_component_version_test_execution_query_service,
    get_mock_component_version_test_execution,
    backend_app_table,
):
    # ARRANGE
    query_service = get_dynamodb_component_version_test_execution_query_service
    fill_db_with_test_executions(backend_app_table, [get_mock_component_version_test_execution()])

    # ACT
    component = query_service.get_component_version_test_execution(
        version_id=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
        test_execution_id=GlobalVariables.TEST_TEST_EXECUTION_ID.value,
        instance_id=GlobalVariables.TEST_INSTANCE_ID.value,
    )

    # ASSERT
    assertpy.assert_that(component).is_not_none()
    assertpy.assert_that(component).is_equal_to(get_mock_component_version_test_execution())


def test_get_component_version_test_executions_by_test_execution_id(
    get_dynamodb_component_version_test_execution_query_service,
    get_mock_component_version_test_execution,
    backend_app_table,
):
    # ARRANGE
    query_service = get_dynamodb_component_version_test_execution_query_service
    fill_db_with_test_executions(
        backend_app_table,
        [
            get_mock_component_version_test_execution(),
            get_mock_component_version_test_execution(component_version_id="version-2"),
            get_mock_component_version_test_execution(
                component_version_id="version-2", test_execution_id="09776d9f-349f-4f50-8ba4-b862d8eaa044"
            ),
            get_mock_component_version_test_execution(
                component_version_id="version-2", instance_id="i-56789012345ghijkl"
            ),
            get_mock_component_version_test_execution(
                component_version_id="version-2",
                test_execution_id="09776d9f-349f-4f50-8ba4-b862d8eaa044",
                instance_id="i-56789012345ghijkl",
            ),
        ],
    )

    # ACT
    component_version_test_executions_1 = query_service.get_component_version_test_executions_by_test_execution_id(
        version_id="version-1", test_execution_id=GlobalVariables.TEST_TEST_EXECUTION_ID.value
    )
    component_version_test_executions_2 = query_service.get_component_version_test_executions_by_test_execution_id(
        version_id="version-2", test_execution_id=GlobalVariables.TEST_TEST_EXECUTION_ID.value
    )
    component_version_test_executions_3 = query_service.get_component_version_test_executions_by_test_execution_id(
        version_id="version-2", test_execution_id="09776d9f-349f-4f50-8ba4-b862d8eaa044"
    )
    component_version_test_executions_4 = query_service.get_component_version_test_executions_by_test_execution_id(
        version_id="version-3", test_execution_id=GlobalVariables.TEST_TEST_EXECUTION_ID.value
    )

    # ASSERT
    assertpy.assert_that(component_version_test_executions_1).is_not_none()
    assertpy.assert_that(component_version_test_executions_2).is_not_none()
    assertpy.assert_that(component_version_test_executions_3).is_not_none()
    assertpy.assert_that(component_version_test_executions_4).is_not_none()
    assertpy.assert_that(len(component_version_test_executions_1)).is_equal_to(1)
    assertpy.assert_that(len(component_version_test_executions_2)).is_equal_to(2)
    assertpy.assert_that(len(component_version_test_executions_3)).is_equal_to(2)
    assertpy.assert_that(len(component_version_test_executions_4)).is_equal_to(0)


def test_can_raise_adapter_exception_when_component_version_test_execution_not_found(
    get_dynamodb_component_version_test_execution_query_service, backend_app_table
):
    # ARRANGE
    query_service = get_dynamodb_component_version_test_execution_query_service

    # ACT
    component_version_test_execution_entity = query_service.get_component_version_test_execution(
        version_id=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
        test_execution_id=GlobalVariables.TEST_TEST_EXECUTION_ID.value,
        instance_id=GlobalVariables.TEST_INSTANCE_ID.value,
    )

    # ASSERT
    assertpy.assert_that(component_version_test_execution_entity).is_equal_to(None)
