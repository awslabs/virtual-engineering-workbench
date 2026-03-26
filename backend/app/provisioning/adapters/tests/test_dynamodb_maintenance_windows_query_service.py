import assertpy

from app.provisioning.adapters.query_services import dynamodb_maintenance_windows_query_service
from app.provisioning.adapters.repository.dynamo_entity_config import DBPrefix
from app.provisioning.adapters.tests import conftest
from app.provisioning.domain.model import maintenance_window


def get_fake_maintenance_windows():
    maintenance_window_count = 5
    return [
        maintenance_window.MaintenanceWindow(
            day=maintenance_window.WeekDay.MONDAY,
            startTime=f"0{i}:00",
            endTime=f"0{i+4}:00",
            userId=f"T001{i}AA",
        )
        for i in range(maintenance_window_count)
    ]


def fill_db_with_maintenance_windows(
    backend_app_dynamodb_table, maintenance_windows: list[maintenance_window.MaintenanceWindow]
):
    for mw in maintenance_windows:
        backend_app_dynamodb_table.put_item(
            Item={
                "PK": f"{DBPrefix.MAINTENANCE_WINDOW.value}#{mw.day.value}#{mw.nearestStartHour}",
                "SK": f"{DBPrefix.USER.value}#{mw.userId}",
                **mw.dict(),
            }
        )


def test_maintenance_windows_query_service_when_user_exists_returns_entity(mock_dynamodb, backend_app_dynamodb_table):
    # Arrange
    query_service = dynamodb_maintenance_windows_query_service.DynamoDBMaintenanceWindowsQueryService(
        table_name=conftest.TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=conftest.GSI_NAME_INVERTED_PK,
    )
    fake_maintenance_windows = get_fake_maintenance_windows()
    fill_db_with_maintenance_windows(backend_app_dynamodb_table, fake_maintenance_windows)

    # Act
    maintenance_ws = query_service.get_maintenance_windows_by_user_id("T0010AA")

    # Assert
    assertpy.assert_that(maintenance_ws).is_not_empty()
    assertpy.assert_that(len(maintenance_ws)).is_equal_to(1)
    assertpy.assert_that(maintenance_ws[0].dict()).is_equal_to(fake_maintenance_windows[0].dict())


def test_maintenance_windows_query_service_when_user_not_exists_returns_none(mock_dynamodb, backend_app_dynamodb_table):
    # Arrange
    query_service = dynamodb_maintenance_windows_query_service.DynamoDBMaintenanceWindowsQueryService(
        table_name=conftest.TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=conftest.GSI_NAME_INVERTED_PK,
    )
    fake_maintenance_windows = get_fake_maintenance_windows()
    fill_db_with_maintenance_windows(backend_app_dynamodb_table, fake_maintenance_windows)

    # Act
    maintenance_ws = query_service.get_maintenance_windows_by_user_id("T0011BB")

    # Assert
    assertpy.assert_that(maintenance_ws).is_empty()


def test_maintenance_windows_query_service_when_maintenance_windows_exists_returns_entity(
    mock_dynamodb, backend_app_dynamodb_table
):
    # Arrange
    query_service = dynamodb_maintenance_windows_query_service.DynamoDBMaintenanceWindowsQueryService(
        table_name=conftest.TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=conftest.GSI_NAME_INVERTED_PK,
    )
    fake_maintenance_windows = get_fake_maintenance_windows()
    fill_db_with_maintenance_windows(backend_app_dynamodb_table, fake_maintenance_windows)

    # Act
    maintenance_ws = query_service.get_maintenance_windows_by_time(maintenance_window.WeekDay.MONDAY, 0)

    # Assert
    assertpy.assert_that(maintenance_ws).is_not_empty()
    assertpy.assert_that(len(maintenance_ws)).is_equal_to(1)
    assertpy.assert_that(maintenance_ws[0].dict()).is_equal_to(fake_maintenance_windows[0].dict())


def test_maintenance_windows_query_service_when_maintenance_windows_not_exists_returns_empty(
    mock_dynamodb, backend_app_dynamodb_table
):
    # Arrange
    query_service = dynamodb_maintenance_windows_query_service.DynamoDBMaintenanceWindowsQueryService(
        table_name=conftest.TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=conftest.GSI_NAME_INVERTED_PK,
    )
    fake_maintenance_windows = get_fake_maintenance_windows()
    fill_db_with_maintenance_windows(backend_app_dynamodb_table, fake_maintenance_windows)

    # Act
    maintenance_ws = query_service.get_maintenance_windows_by_time(maintenance_window.WeekDay.TUESDAY, 0)

    # Assert
    assertpy.assert_that(maintenance_ws).is_empty()
