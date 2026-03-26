import assertpy
import boto3
import moto
import pytest

from app.shared.adapters.boto import aws_parameter_service
from app.shared.adapters.exceptions.adapter_exception import AdapterException

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
def mock_ssm_parameter(provider):
    ssm_api_instance = aws_parameter_service.AWSParameterService(ssm_provider=provider.client("ssm"))

    def _mock_ssm_parameter(parameter_name: str, parameter_value: str):
        ssm_api_instance.create_string_parameter(parameter_name=parameter_name, parameter_value=parameter_value)

    return _mock_ssm_parameter


def test_get_parameter_returns_correct_value(mock_ssm_parameter, provider):
    # Arrange
    parameter_name = "param-name"
    parameter_value = "param-value"
    mock_ssm_parameter(parameter_name, parameter_value)
    ssm_api_instance = aws_parameter_service.AWSParameterService(ssm_provider=provider.client("ssm"))

    # Act
    returned_parameter_value = ssm_api_instance.get_parameter_value(parameter_name=parameter_name)

    # Assert
    assertpy.assert_that(returned_parameter_value).is_not_none()
    assertpy.assert_that(returned_parameter_value).is_equal_to(parameter_value)


def test_get_list_parameter_value_returns_correct_value(provider, mock_ssm_parameter):
    # Arrange
    parameter_name = "param-name"
    parameter_value = "a,b"
    mock_ssm_parameter(parameter_name, parameter_value)
    ssm_api_instance = aws_parameter_service.AWSParameterService(ssm_provider=provider.client("ssm"))

    # Act
    returned_parameter_value = ssm_api_instance.get_list_parameter_value(parameter_name=parameter_name)

    # Assert
    assertpy.assert_that(returned_parameter_value).is_not_none()
    assertpy.assert_that(returned_parameter_value).is_iterable()
    assertpy.assert_that(returned_parameter_value).contains_only("a", "b")


def test_set_read_list_parameter_value_returns_correct_value(provider, mock_ssm_parameter):
    # Arrange
    parameter_name = "param-name"
    parameter_value = "a,b"
    ssm_api_instance = aws_parameter_service.AWSParameterService(ssm_provider=provider.client("ssm"))

    # Act
    ssm_api_instance.create_string_parameter(parameter_name=parameter_name, parameter_value=parameter_value)
    returned_parameter_value = ssm_api_instance.get_list_parameter_value(parameter_name=parameter_name)

    # Assert
    assertpy.assert_that(returned_parameter_value).is_not_none()
    assertpy.assert_that(returned_parameter_value).is_iterable()
    assertpy.assert_that(returned_parameter_value).contains_only("a", "b")


def test_read_undefined_parameter_raises(provider, mock_ssm_parameter):
    # Arrange
    parameter_name = "param-name"
    ssm_api_instance = aws_parameter_service.AWSParameterService(ssm_provider=provider.client("ssm"))

    # Act & Assert
    with pytest.raises(AdapterException) as excinfo:
        ssm_api_instance.get_list_parameter_value(parameter_name=parameter_name)
    assert 'Unable to get parameter "param-name"' in str(excinfo.value)


def test_delete_parameter_deletes_ssm_parameter(provider, mock_ssm_parameter):
    # Arrange
    parameter_name = "param-name"
    parameter_value = "a,b"
    mock_ssm_parameter(parameter_name, parameter_value)
    ssm_api_instance = aws_parameter_service.AWSParameterService(ssm_provider=provider.client("ssm"))

    # Act
    ssm_api_instance.delete_parameter(parameter_name=parameter_name)

    # Assert
    with pytest.raises(AdapterException) as excinfo:
        ssm_api_instance.get_parameter_value(parameter_name=parameter_name)

    assertpy.assert_that(str(excinfo.value)).is_equal_to('Unable to get parameter "param-name"')


def test_get_parameters_by_path_returns_dict_with_values(provider):
    # Arrange
    ssm_api_instance = aws_parameter_service.AWSParameterService(ssm_provider=provider.client("ssm"))
    ssm_api_instance.create_string_parameter(parameter_name="/path/to/param1", parameter_value="value1")
    ssm_api_instance.create_string_parameter(parameter_name="/path/to/param2", parameter_value="value2")
    ssm_api_instance.create_string_parameter(parameter_name="/path/to_3/param3", parameter_value="value3")

    # Act
    resp = ssm_api_instance.get_parameters_by_path(path="/path/to")

    # Assert
    assertpy.assert_that(resp).is_equal_to(
        {
            "/path/to/param1": "value1",
            "/path/to/param2": "value2",
        }
    )
