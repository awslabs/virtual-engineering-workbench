from unittest import mock

import assertpy
from mypy_boto3_ecs import client

from app.provisioning.adapters.services import ecs_container_management_service
from app.provisioning.domain.model import container_details


def test_start_container_should_start_container(mock_ecs_client: client.ECSClient, mock_logger):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=mock_ecs_client)
    service = ecs_container_management_service.ECSContainerManagementService(
        ecs_boto_client_provider=client_provider, logger=mock_logger
    )

    # ACT
    service.start_container(
        aws_account_id="001234567890",
        region="us-east-1",
        cluster_name="test-cluster",
        service_name="test-service",
        user_id="T0011AA",
    )

    # ASSERT
    describe_services_response = mock_ecs_client.describe_services(cluster="test-cluster", services=["test-service"])
    assertpy.assert_that(describe_services_response.get("services")[0].get("desiredCount")).is_equal_to(1)


def test_stop_container_should_stop_container(mock_ecs_client: client.ECSClient, mock_logger):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=mock_ecs_client)
    service = ecs_container_management_service.ECSContainerManagementService(
        ecs_boto_client_provider=client_provider, logger=mock_logger
    )

    # ACT
    service.stop_container(
        aws_account_id="001234567890",
        region="us-east-1",
        cluster_name="test-cluster",
        service_name="test-service",
        user_id="T0011AA",
    )

    # ASSERT
    describe_services_response = mock_ecs_client.describe_services(cluster="test-cluster", services=["test-service"])
    assertpy.assert_that(describe_services_response.get("services")[0].get("desiredCount")).is_equal_to(0)


def test_get_container_status_should_return_running_when_running(mock_ecs_client: client.ECSClient, mock_logger):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=mock_ecs_client)
    service = ecs_container_management_service.ECSContainerManagementService(
        ecs_boto_client_provider=client_provider, logger=mock_logger
    )

    # ACT
    container_state = service.get_container_status(
        aws_account_id="001234567890",
        region="us-east-1",
        cluster_name="test-cluster",
        service_name="test-service",
        user_id="T0011AA",
    )

    # ASSERT
    assertpy.assert_that(container_state).is_equal_to(container_details.ContainerState(Name="RUNNING"))


def test_get_container_status_should_return_stopped_when_service_does_not_exist(
    mock_ecs_client: client.ECSClient, mock_logger
):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=mock_ecs_client)
    service = ecs_container_management_service.ECSContainerManagementService(
        ecs_boto_client_provider=client_provider, logger=mock_logger
    )
    mock_ecs_client.update_service(service="test-service", cluster="test-cluster", desiredCount=0)
    mock_ecs_client.delete_service(service="test-service", cluster="test-cluster")

    # ACT
    container_state = service.get_container_status(
        aws_account_id="001234567890",
        region="us-east-1",
        cluster_name="test-cluster",
        service_name="test-service",
        user_id="T0011AA",
    )

    # ASSERT
    assertpy.assert_that(container_state).is_equal_to(container_details.ContainerState(Name="STOPPED"))


def test_get_container_details_should_return_container_details_when_exists(
    mock_ecs_client: client.ECSClient, mock_logger
):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=mock_ecs_client)
    service = ecs_container_management_service.ECSContainerManagementService(
        ecs_boto_client_provider=client_provider, logger=mock_logger
    )

    # ACT
    container_details = service.get_container_details(
        aws_account_id="001234567890",
        region="us-east-1",
        cluster_name="test-cluster",
        service_name="test-service",
        user_id="T0011AA",
    )

    # ASSERT
    assertpy.assert_that(container_details).is_not_none()
