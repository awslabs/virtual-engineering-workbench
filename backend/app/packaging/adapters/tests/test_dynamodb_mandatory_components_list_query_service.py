import assertpy

from app.packaging.adapters.repository import dynamo_entity_config
from app.packaging.domain.model.component import mandatory_components_list


def fill_db_with_mandatory_components_list(
    backend_app_table,
    mandatory_components_list_entity: mandatory_components_list.MandatoryComponentsList,
):
    backend_app_table.put_item(
        Item={
            "PK": f"{dynamo_entity_config.DBPrefix.Platform}#{mandatory_components_list_entity.mandatoryComponentsListPlatform}",
            "SK": f"{dynamo_entity_config.DBPrefix.Os}#{mandatory_components_list_entity.mandatoryComponentsListOsVersion}#{dynamo_entity_config.DBPrefix.Arch}#{mandatory_components_list_entity.mandatoryComponentsListArchitecture}",
            **mandatory_components_list_entity.model_dump(),
        }
    )


def test_get_mandatory_components_list(
    mock_dynamodb,
    get_mock_mandatory_components_list,
    backend_app_table,
    get_mandatory_components_query_service,
):
    # ARRANGE
    architecture = "amd64"
    os = "Ubuntu 24"
    platform = "Linux"
    query_service = get_mandatory_components_query_service
    fill_db_with_mandatory_components_list(
        backend_app_table,
        get_mock_mandatory_components_list(platform=platform, os=os, architecture=architecture),
    )

    # ACT
    mandatory_components_list_entity = query_service.get_mandatory_components_list(
        platform=platform, os=os, architecture=architecture
    )

    # ASSERT
    assertpy.assert_that(mandatory_components_list_entity).is_not_none()
    assertpy.assert_that(mandatory_components_list_entity).is_equal_to(
        get_mock_mandatory_components_list(platform=platform, os=os, architecture=architecture)
    )


def test_get_mandatory_components_list_returns_none_if_no_match(
    mock_dynamodb,
    get_mock_mandatory_components_list,
    backend_app_table,
    get_mandatory_components_query_service,
):
    # ARRANGE
    architecture = "amd64"
    os = "Ubuntu 24"
    platform = "Linux"
    query_service = get_mandatory_components_query_service
    fill_db_with_mandatory_components_list(
        backend_app_table,
        get_mock_mandatory_components_list(platform=platform, os=os, architecture=architecture),
    )

    # ACT
    mandatory_components_list_entity = query_service.get_mandatory_components_list(
        platform="Windows", os=os, architecture=architecture
    )

    # ASSERT
    assertpy.assert_that(mandatory_components_list_entity).is_equal_to(None)


def test_get_mandatory_components_lists(
    mock_dynamodb,
    get_mock_mandatory_components_list,
    backend_app_table,
    get_mandatory_components_query_service,
):
    # ARRANGE
    query_service = get_mandatory_components_query_service
    fill_db_with_mandatory_components_list(
        backend_app_table,
        get_mock_mandatory_components_list(platform="Linux", os="Ubuntu 24", architecture="amd64"),
    )
    fill_db_with_mandatory_components_list(
        backend_app_table,
        get_mock_mandatory_components_list(
            platform="Windows", os="Microsoft Windows Server 2025", architecture="amd64"
        ),
    )

    # ACT
    mandatory_components_lists_entity = query_service.get_mandatory_components_lists()

    # ASSERT
    assertpy.assert_that(mandatory_components_lists_entity).is_not_none()
    assertpy.assert_that(len(mandatory_components_lists_entity)).is_equal_to(2)

    assertpy.assert_that(mandatory_components_lists_entity[0]).is_equal_to(
        get_mock_mandatory_components_list(platform="Linux", os="Ubuntu 24", architecture="amd64"),
    )
    assertpy.assert_that(mandatory_components_lists_entity[1]).is_equal_to(
        get_mock_mandatory_components_list(
            platform="Windows", os="Microsoft Windows Server 2025", architecture="amd64"
        ),
    )


def test_get_mandatory_components_lists_returns_empty_list_if_no_match(
    mock_dynamodb, backend_app_table, get_mandatory_components_query_service
):
    # ARRANGE
    query_service = get_mandatory_components_query_service

    # ACT
    mandatory_components_list_entity = query_service.get_mandatory_components_lists()

    # ASSERT
    assertpy.assert_that(mandatory_components_list_entity).is_equal_to([])
