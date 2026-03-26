import logging
from unittest import mock

import pytest
from attr import dataclass

from app.provisioning.domain.commands.product_provisioning import (
    complete_product_launch_command,
    complete_provisioned_product_removal_command,
    complete_provisioned_product_update,
    deprovision_provisioned_product_command,
    fail_product_launch_command,
    fail_provisioned_product_removal_command,
    fail_provisioned_product_update,
    provision_product_command,
    start_provisioned_product_update_command,
    stop_provisioned_product_after_update_complete_command,
    stop_provisioned_product_for_update_command,
    update_provisioned_product_command,
)
from app.provisioning.domain.commands.provisioned_product_configuration import (
    fail_provisioned_product_configuration_command,
)
from app.provisioning.domain.commands.provisioned_product_state import (
    complete_provisioned_product_start_command,
    complete_provisioned_product_stop_command,
    start_provisioned_product_command,
    stop_provisioned_product_command,
)
from app.provisioning.entrypoints.domain_event_handler import bootstrapper
from app.shared.adapters.message_bus import in_memory_command_bus

TEST_TABLE_NAME = "TEST"


@pytest.fixture(autouse=True)
def disable_migrations():
    with mock.patch(
        "app.provisioning.entrypoints.domain_event_handler.bootstrapper.migrations_config",
        return_value=[],
    ):
        yield


@pytest.fixture
def lambda_context():
    @dataclass
    class context:
        function_name = "test"
        memory_limit_in_mb = 128
        invoked_function_arn = "arn:aws:lambda:eu-west-1:000000000:function:test"
        aws_request_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

    return context


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCOUNT", "123456789012")
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "Test")
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "ProjectsEvents")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv(
        "DOMAIN_EVENT_BUS_ARN",
        "arn:aws:events:us-east-1:001234567890:event-bus/projects-events",
    )
    monkeypatch.setenv("BOUNDED_CONTEXT", "products")
    monkeypatch.setenv("SPOKE_ACCOUNT_VPC_ID_PARAM_NAME", "/workbench/vpc/vpc-id")
    monkeypatch.setenv("PROVISIONING_SUBNET_SELECTOR", "PrivateSubnetWithTransitGateway")


@pytest.fixture
def generate_event():
    def _generate_event(detail_type: str, detail: dict):
        return {
            "version": "0",
            "id": "162fc80d-b43c-09da-bae4-54471eebcf0f",
            "detail-type": detail_type,
            "source": "org.workbench.provisioning.dev",
            "account": "123456789012",
            "time": "2022-11-14T17:15:50Z",
            "region": "us-east-1",
            "resources": [],
            "detail": detail,
        }

    return _generate_event


@pytest.fixture
def product_launch_started_event():
    return {
        "eventName": "ProductLaunchStarted",
        "provisionedProductId": "vt-123",
        "userIpAddress": "127.0.0.1",
    }


@pytest.fixture
def provisioned_product_updated_event():
    return {
        "projectId": "proj-1",
        "owner": "SF44410",
        "productType": "WORKBENCH",
        "productName": "TEST",
        "provisionedProductId": "vt-123",
    }


@pytest.fixture
def insufficient_capacity_reached_event():
    return {
        "eventName": "InsufficientCapacityReached",
        "projectId": "proj-1",
        "provisionedProductId": "vt-123",
        "owner": "SF44410",
        "productType": "WORKBENCH",
        "productName": "TEST",
        "userIpAddress": "127.0.0.1",
    }


@pytest.fixture
def product_stopped_for_upgrade_event():
    return {
        "eventName": "ProvisionedProductStoppedForUpgrade",
        "provisionedProductId": "vt-123",
    }


@pytest.fixture
def product_stopped_for_update_event():
    return {
        "eventName": "ProvisionedProductStoppedForUpdate",
        "provisionedProductId": "vt-123",
    }


@pytest.fixture
def product_stop_for_upgrade_failed_event():
    return {
        "eventName": "ProvisionedProductStopForUpgradeFailed",
        "provisionedProductId": "vt-123",
    }


@pytest.fixture
def product_update_initialized_event():
    return {
        "eventName": "ProvisionedProductUpdateInitialized",
        "provisionedProductId": "vt-123",
        "userIpAddress": "127.0.0.1",
        "versionId": "vers-123",
    }


@pytest.fixture
def provisioned_product_stopped_event():
    return {
        "eventName": "ProvisionedProductStopped",
        "provisionedProductId": "vt-123",
    }


@pytest.fixture
def provisioned_product_removal_started_event():
    return {
        "eventName": "ProvisionedProductRemovalStarted",
        "provisionedProductId": "vt-123",
    }


@pytest.fixture
def provisioned_product_removal_retried_event():
    return {
        "eventName": "ProvisionedProductRemovalRetried",
        "provisionedProductId": "vt-123",
    }


@pytest.fixture
def provisioned_product_start_initiated_event():
    return {
        "eventName": "ProvisionedProductStartInitiated",
        "provisionedProductId": "vt-123",
        "userIpAddress": "127.0.0.1",
    }


@pytest.fixture
def provisioned_product_stop_initiated_event():
    return {
        "eventName": "ProvisionedProductStopInitiated",
        "provisionedProductId": "vt-123",
    }


@pytest.fixture
def provisioned_product_status_out_of_sync_running_payload():
    return {
        "eventName": "ProvisionedProductStatusOutOfSync",
        "provisionedProductId": "pp-123",
        "oldStatus": "STARTING",
        "newStatus": "RUNNING",
    }


@pytest.fixture
def provisioned_product_status_out_of_sync_stopped_payload():
    return {
        "eventName": "ProvisionedProductStatusOutOfSync",
        "provisionedProductId": "pp-123",
        "oldStatus": "STOPPING",
        "newStatus": "STOPPED",
    }


@pytest.fixture
def provisioned_product_status_out_of_sync_provisioned_payload():
    return {
        "eventName": "ProvisionedProductStatusOutOfSync",
        "provisionedProductId": "pp-123",
        "oldStatus": "PROVISIONING",
        "newStatus": "RUNNING",
    }


@pytest.fixture
def provisioned_product_status_out_of_sync_provisioning_failed_payload():
    return {
        "eventName": "ProvisionedProductStatusOutOfSync",
        "provisionedProductId": "pp-123",
        "oldStatus": "PROVISIONING",
        "newStatus": "PROVISIONING_ERROR",
    }


@pytest.fixture
def provisioned_product_status_out_of_sync_updated_payload():
    return {
        "eventName": "ProvisionedProductStatusOutOfSync",
        "provisionedProductId": "pp-123",
        "oldStatus": "UPDATING",
        "newStatus": "RUNNING",
    }


@pytest.fixture
def provisioned_product_status_out_of_sync_updating_failed_payload():
    return {
        "eventName": "ProvisionedProductStatusOutOfSync",
        "provisionedProductId": "pp-123",
        "oldStatus": "UPDATING",
        "newStatus": "PROVISIONING_ERROR",
    }


@pytest.fixture
def provisioned_product_status_out_of_sync_terminated_payload():
    return {
        "eventName": "ProvisionedProductStatusOutOfSync",
        "provisionedProductId": "pp-123",
        "oldStatus": "DEPROVISIONING",
        "newStatus": "TERMINATED",
    }


@pytest.fixture
def provisioned_product_status_out_of_sync_terminate_failed_payload():
    return {
        "eventName": "ProvisionedProductStatusOutOfSync",
        "provisionedProductId": "pp-123",
        "oldStatus": "DEPROVISIONING",
        "newStatus": "PROVISIONING_ERROR",
    }


@pytest.fixture
def provisioned_product_status_out_of_sync_configuration_failed_payload():
    return {
        "eventName": "ProvisionedProductStatusOutOfSync",
        "provisionedProductId": "pp-123",
        "oldStatus": "CONFIGURATION_IN_PROGRESS",
        "newStatus": "CONFIGURATION_FAILED",
    }


@pytest.fixture()
def mock_logger():
    yield mock.create_autospec(spec=logging.Logger, instance=True)


@pytest.fixture
def provision_product_command_handler():
    return mock.Mock()


@pytest.fixture
def stop_provision_product_after_update_complete_handler():
    return mock.Mock()


@pytest.fixture
def stop_for_upgrade_command_handler():
    return mock.Mock()


@pytest.fixture
def update_provisioned_product_command_handler():
    return mock.Mock()


@pytest.fixture
def deprovision_provisioned_product_command_handler():
    return mock.Mock()


@pytest.fixture
def start_provisioned_product_command_handler():
    return mock.Mock()


@pytest.fixture
def stop_provisioned_product_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_complete_provisioned_product_removal_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_fail_provisioned_product_removal_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_complete_provisioned_product_start_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_complete_provisioned_product_stop_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_complete_provisioned_product_launch_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_fail_provisioned_product_launch_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_complete_provisioned_product_update_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_fail_provisioned_product_update_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_fail_provisioned_product_configuration_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_start_provisioned_product_update_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_dependencies(
    provision_product_command_handler,
    deprovision_provisioned_product_command_handler,
    start_provisioned_product_command_handler,
    stop_provisioned_product_command_handler,
    mock_complete_provisioned_product_removal_command_handler,
    mock_fail_provisioned_product_removal_command_handler,
    mock_complete_provisioned_product_start_command_handler,
    mock_complete_provisioned_product_stop_command_handler,
    mock_complete_provisioned_product_launch_command_handler,
    mock_fail_provisioned_product_launch_command_handler,
    stop_for_upgrade_command_handler,
    update_provisioned_product_command_handler,
    mock_complete_provisioned_product_update_command_handler,
    mock_fail_provisioned_product_update_command_handler,
    mock_fail_provisioned_product_configuration_command_handler,
    mock_logger,
    stop_provision_product_after_update_complete_handler,
    mock_start_provisioned_product_update_command_handler,
):
    return bootstrapper.Dependencies(
        command_bus=in_memory_command_bus.InMemoryCommandBus(
            logger=mock_logger,
        )
        .register_handler(
            provision_product_command.ProvisionProductCommand,
            provision_product_command_handler,
        )
        .register_handler(
            stop_provisioned_product_for_update_command.StopProvisionedProductForUpdateCommand,
            stop_for_upgrade_command_handler,
        )
        .register_handler(
            update_provisioned_product_command.UpdateProvisionedProductCommand,
            update_provisioned_product_command_handler,
        )
        .register_handler(
            deprovision_provisioned_product_command.DeprovisionProvisionedProductCommand,
            deprovision_provisioned_product_command_handler,
        )
        .register_handler(
            start_provisioned_product_command.StartProvisionedProductCommand,
            start_provisioned_product_command_handler,
        )
        .register_handler(
            stop_provisioned_product_command.StopProvisionedProductCommand,
            stop_provisioned_product_command_handler,
        )
        .register_handler(
            complete_provisioned_product_removal_command.CompleteProvisionedProductRemovalCommand,
            mock_complete_provisioned_product_removal_command_handler,
        )
        .register_handler(
            fail_provisioned_product_removal_command.FailProvisionedProductRemovalCommand,
            mock_fail_provisioned_product_removal_command_handler,
        )
        .register_handler(
            complete_product_launch_command.CompleteProductLaunchCommand,
            mock_complete_provisioned_product_launch_command_handler,
        )
        .register_handler(
            fail_product_launch_command.FailProductLaunchCommand,
            mock_fail_provisioned_product_launch_command_handler,
        )
        .register_handler(
            complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand,
            mock_complete_provisioned_product_start_command_handler,
        )
        .register_handler(
            complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand,
            mock_complete_provisioned_product_stop_command_handler,
        )
        .register_handler(
            complete_provisioned_product_update.CompleteProvisionedProductUpdateCommand,
            mock_complete_provisioned_product_update_command_handler,
        )
        .register_handler(
            fail_provisioned_product_update.FailProvisionedProductUpdateCommand,
            mock_fail_provisioned_product_update_command_handler,
        )
        .register_handler(
            fail_provisioned_product_configuration_command.FailProvisionedProductConfigurationCommand,
            mock_fail_provisioned_product_configuration_command_handler,
        )
        .register_handler(
            stop_provisioned_product_after_update_complete_command.StopProvisionedProductAfterUpdateCompleteCommand,
            stop_provision_product_after_update_complete_handler,
        )
        .register_handler(
            start_provisioned_product_update_command.StartProvisionedProductUpdateCommand,
            mock_start_provisioned_product_update_command_handler,
        )
    )
