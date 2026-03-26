import assertpy
import boto3
import moto
import pytest

from app.shared.api import ssm_parameter_service

TEST_REGION = "us-east-1"


@pytest.fixture(autouse=True)
def mock_ssm():
    with moto.mock_aws():
        yield boto3.client(
            "ssm",
            region_name=TEST_REGION,
            aws_access_key_id="access-key-id",
            aws_secret_access_key="secret-access-key",
            aws_session_token="session-token",
        )


@pytest.fixture()
def mock_ssm_parameter():
    ssm_service = ssm_parameter_service.SSMApi(
        region=TEST_REGION,
        access_key_id="access_key_id",
        secret_access_key="secret_access_key",
        session_token="session_token",
    )

    def _mock_ssm_parameter(parameter_name: str, parameter_value: str):
        ssm_service.create_string_parameter(parameter_name=parameter_name, parameter_value=parameter_value)

    return _mock_ssm_parameter


def test_get_parameter_returns_correct_value(mock_ssm_parameter):
    # Arrange
    parameter_name = "param-name"
    parameter_value = "param-value"
    mock_ssm_parameter(parameter_name, parameter_value)
    ssm_api_instance = ssm_parameter_service.SSMApi(region=TEST_REGION)

    # Act
    returned_parameter_value = ssm_api_instance.get_parameter_value(parameter_name=parameter_name)

    # Assert
    assertpy.assert_that(returned_parameter_value).is_not_none()
    assertpy.assert_that(returned_parameter_value).is_equal_to(parameter_value)


def test_get_list_parameter_value_returns_correct_value(mock_ssm_parameter):
    # Arrange
    parameter_name = "param-name"
    parameter_value = "a,b"
    mock_ssm_parameter(parameter_name, parameter_value)
    ssm_api_instance = ssm_parameter_service.SSMApi(region=TEST_REGION)

    # Act
    returned_parameter_value = ssm_api_instance.get_list_parameter_value(parameter_name=parameter_name)

    # Assert
    assertpy.assert_that(returned_parameter_value).is_not_none()
    assertpy.assert_that(returned_parameter_value).is_iterable()
    assertpy.assert_that(returned_parameter_value).contains_only("a", "b")
