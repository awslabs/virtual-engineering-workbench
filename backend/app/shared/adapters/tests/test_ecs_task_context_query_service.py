from unittest import mock

import assertpy

from app.shared.adapters.query_services import ecs_task_context_query_service
from app.shared.adapters.tests.conftest import GlobalVariables


@mock.patch("urllib.request.urlopen")
def test_get_task_context(
    mock_urlopen,
    get_test_container_metadata,
    get_test_task_context,
    get_test_task_metadata,
):
    # ARRANGE
    mock_request = mock.MagicMock()
    mock_request.__enter__.side_effect = [get_test_container_metadata(), get_test_task_metadata()]
    mock_urlopen.return_value = mock_request
    ecs_container_context_qry_srv = ecs_task_context_query_service.EcsTaskContextQueryService(
        endpoint=GlobalVariables.URL.value
    )

    # ACT
    task_context = ecs_container_context_qry_srv.get_task_context()

    # ASSERT
    assertpy.assert_that(task_context).is_equal_to(get_test_task_context())


@mock.patch("urllib.request.urlopen")
def test_get_task_context_without_limits(
    mock_urlopen,
    get_test_container_metadata,
    get_test_task_context,
    get_test_task_metadata,
):
    # ARRANGE
    mock_request = mock.MagicMock()
    mock_request.__enter__.side_effect = [get_test_container_metadata(limits=False), get_test_task_metadata()]
    mock_urlopen.return_value = mock_request
    ecs_container_context_qry_srv = ecs_task_context_query_service.EcsTaskContextQueryService(
        endpoint=GlobalVariables.URL.value
    )

    # ACT
    task_context = ecs_container_context_qry_srv.get_task_context()

    # ASSERT
    assertpy.assert_that(task_context).is_equal_to(
        get_test_task_context(memory_limit_in_mb=GlobalVariables.DEFAULT_MEMORY_LIMIT_IN_MB.value)
    )


@mock.patch("urllib.request.urlopen")
def test_get_task_context_without_memory_limit(
    mock_urlopen,
    get_test_container_metadata,
    get_test_task_context,
    get_test_task_metadata,
):
    # ARRANGE
    mock_request = mock.MagicMock()
    mock_request.__enter__.side_effect = [get_test_container_metadata(memory=None), get_test_task_metadata()]
    mock_urlopen.return_value = mock_request
    ecs_container_context_qry_srv = ecs_task_context_query_service.EcsTaskContextQueryService(
        endpoint=GlobalVariables.URL.value
    )

    # ACT
    task_context = ecs_container_context_qry_srv.get_task_context()

    # ASSERT
    assertpy.assert_that(task_context).is_equal_to(
        get_test_task_context(memory_limit_in_mb=GlobalVariables.DEFAULT_MEMORY_LIMIT_IN_MB.value)
    )
