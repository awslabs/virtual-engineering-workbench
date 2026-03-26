from unittest import mock

import assertpy
import boto3
import pytest

from app.provisioning.adapters.services import aws_parameter_service


def test_get_parameter_value_should_return_parameter_value_if_exists(mock_ssm_client):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ssm", region_name="us-east-1"))
    service = aws_parameter_service.AWSParameterService(
        ssm_boto_client_provider=client_provider, sm_boto_client_provider=mock.MagicMock()
    )
    mock_ssm_client.put_parameter(Name="test-param", Value="test-value", Type="String", Overwrite=True)

    # ACT
    param_value = service.get_parameter_value(
        parameter_name="test-param", aws_account_id="001234567890", region="us-east-1", user_id="T0011AA"
    )

    # ASSERT
    assertpy.assert_that(param_value).is_equal_to("test-value")


def test_get_parameter_value_should_raise_if_does_not_exist(mock_ssm_client):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ssm", region_name="us-east-1"))
    service = aws_parameter_service.AWSParameterService(
        ssm_boto_client_provider=client_provider, sm_boto_client_provider=mock.MagicMock()
    )

    # ACT & ASSERT
    with pytest.raises(mock_ssm_client.exceptions.ParameterNotFound):
        service.get_parameter_value(
            parameter_name="test-param", aws_account_id="001234567890", region="us-east-1", user_id="T0011AA"
        )


def test_get_secret_value_should_return_the_secret_if_exists(mock_secretsmanager_client):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("secretsmanager", region_name="us-east-1"))
    service = aws_parameter_service.AWSParameterService(
        ssm_boto_client_provider=mock.MagicMock(),
        sm_boto_client_provider=client_provider,
    )
    mock_secretsmanager_client.create_secret(Name="test-secret", SecretString="test-value")

    # ACT
    param_value = service.get_secret_value(
        secret_name="test-secret", aws_account_id="001234567890", region="us-east-1", user_id="T0011AA"
    )

    # ASSERT
    assertpy.assert_that(param_value).is_equal_to("test-value")
