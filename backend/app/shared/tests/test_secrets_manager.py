import assertpy
import boto3
import moto
import pytest

from app.shared.api import secrets_manager_api

TEST_REGION = "us-east-1"
TEST_ACCOUNT_ID = "123456789012"
TEST_TARGET_ROLE = "TestIAMRole"
TEST_USER = "T00123122"


@pytest.fixture(autouse=True)
def mock_secrets_manager():
    with moto.mock_aws():
        yield boto3.client(
            "secretsmanager",
            region_name=TEST_REGION,
            aws_access_key_id="access-key-id",
            aws_secret_access_key="secret-access-key",
            aws_session_token="session-token",
        )


@pytest.fixture(autouse=True)
def mock_sts():
    with moto.mock_aws():
        yield boto3.client("sts", region_name=TEST_REGION)


def test_get_secret_value_returns_correct_value():
    # Arrange
    secrets_manager = secrets_manager_api.SecretsManagerAPI(
        region=TEST_REGION,
        access_key_id="access_key_id",
        secret_access_key="secret_access_key",
        session_token="session_token",
    )
    secret_name = "secret-name"
    secret_value = "secret-value"
    secret_arn = secrets_manager.create_secret(name=secret_name, value=secret_value)

    # Act
    returned_secret_value = secrets_manager.get_secret_value(secret_id=secret_arn)

    # Assert
    assertpy.assert_that(returned_secret_value).is_not_none()
    assertpy.assert_that(returned_secret_value).is_equal_to(secret_value)
