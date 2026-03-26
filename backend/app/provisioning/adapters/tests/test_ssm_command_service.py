from unittest import mock

import assertpy
import boto3
from mypy_boto3_ssm import client

from app.provisioning.adapters.services import ssm_command_service
from app.provisioning.domain.model import additional_configuration

PROVISIONED_PRODUCT_CONFIGURATION_DOCUMENT_MAPPING = {
    "VVPL_PROVISIONED_PRODUCT_CONFIGURATION": "VVPLProvisionedProductDocument"
}


def test_run_document_runs_document(mock_ssm_client):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ssm", region_name="us-east-1"))
    service = ssm_command_service.SSMCommandService(
        ssm_boto_client_provider=client_provider,
        provisioned_product_configuration_document_mapping=PROVISIONED_PRODUCT_CONFIGURATION_DOCUMENT_MAPPING,
    )
    parameters = [
        additional_configuration.AdditionalConfigurationParameter(key="param-1", value="value-1"),
        additional_configuration.AdditionalConfigurationParameter(key="param-2", value="value-2"),
    ]

    # ACT
    command_id = service.run_document(
        aws_account_id="001234567890",
        region="us-east-1",
        user_id="T0011AA",
        provisioned_product_configuration_type=additional_configuration.ProvisionedProductConfigurationTypeEnum.VVPLProvisionedProductConfiguration,
        instance_id="i-01234567890abcdef",
        parameters=parameters,
    )

    # ASSERT
    assertpy.assert_that(command_id).is_not_empty()


def test_get_run_status_returns_correct_run_status(mock_ssm_client: client.SSMClient):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ssm", region_name="us-east-1"))
    service = ssm_command_service.SSMCommandService(
        ssm_boto_client_provider=client_provider,
        provisioned_product_configuration_document_mapping=PROVISIONED_PRODUCT_CONFIGURATION_DOCUMENT_MAPPING,
    )
    send_result = mock_ssm_client.send_command(
        CloudWatchOutputConfig={"CloudWatchOutputEnabled": True},
        DocumentName="test-doc",
        InstanceIds=["i-01234567890abcdef"],
    )
    command_id = send_result["Command"]["CommandId"]

    # ACT
    run_status, reason = service.get_run_status(
        aws_account_id="001234567890",
        region="us-east-1",
        user_id="T0011AA",
        instance_id="i-01234567890abcdef",
        run_id=command_id,
    )

    # ASSERT
    assertpy.assert_that(run_status).is_equal_to(additional_configuration.AdditionalConfigurationRunStatus.Success)
    assertpy.assert_that(reason).is_not_empty()


def test_is_instance_ready_returns_true_when_instance_is_ready(mock_moto_calls):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ssm", region_name="us-east-1"))
    service = ssm_command_service.SSMCommandService(
        ssm_boto_client_provider=client_provider,
        provisioned_product_configuration_document_mapping=PROVISIONED_PRODUCT_CONFIGURATION_DOCUMENT_MAPPING,
    )

    # ACT
    is_ready = service.is_instance_ready(
        aws_account_id="001234567890",
        region="us-east-1",
        user_id="T0011AA",
        instance_id="i-01234567890abcdef",
    )

    # ASSERT
    assertpy.assert_that(is_ready).is_true()


def test_is_instance_ready_returns_false_when_instance_is_not_ready(mock_moto_calls):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ssm", region_name="us-east-1"))
    service = ssm_command_service.SSMCommandService(
        ssm_boto_client_provider=client_provider,
        provisioned_product_configuration_document_mapping=PROVISIONED_PRODUCT_CONFIGURATION_DOCUMENT_MAPPING,
    )
    mock_moto_calls["GetConnectionStatus"] = mock.MagicMock(
        return_value={"Target": "i-01234567890abcdef", "Status": "notconnected"}
    )

    # ACT
    is_ready = service.is_instance_ready(
        aws_account_id="001234567890",
        region="us-east-1",
        user_id="T0011AA",
        instance_id="i-01234567890abcdef",
    )

    # ASSERT
    assertpy.assert_that(is_ready).is_false()
