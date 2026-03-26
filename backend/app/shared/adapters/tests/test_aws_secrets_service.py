import assertpy
import pytest

from app.shared.adapters.exceptions.adapter_exception import AdapterException
from app.shared.adapters.tests.conftest import GlobalVariables


def test_create_secret_should_create_retrievable_secret(mock_aws_secrets_service):
    # ARRANGE & ACT
    mock_aws_secrets_service.create_secret(
        secret_name=GlobalVariables.SECRET_NAME.value,
        secret_value=GlobalVariables.SECRET_VALUE.value,
        description=GlobalVariables.DESCRIPTION.value,
    )

    # ASSERT
    secret_value = mock_aws_secrets_service.get_secret_value(secret_name=GlobalVariables.SECRET_NAME.value)
    secret_name, description = mock_aws_secrets_service.describe_secret(secret_name=GlobalVariables.SECRET_NAME.value)

    assertpy.assert_that(secret_value).is_equal_to(GlobalVariables.SECRET_VALUE.value)
    assertpy.assert_that(secret_name).is_equal_to(GlobalVariables.SECRET_NAME.value)
    assertpy.assert_that(description).is_equal_to(GlobalVariables.DESCRIPTION.value)


def test_describe_secret_should_raise_exception_when_secret_does_not_exist(mock_aws_secrets_service):
    # ARRANGE & ACT
    with pytest.raises(AdapterException) as exc_info:
        mock_aws_secrets_service.describe_secret(secret_name=GlobalVariables.SECRET_NAME.value)

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f'Unable to get secret "{GlobalVariables.SECRET_NAME.value}".'
    )


def test_describe_secret_should_return_correct_name_and_description(
    mock_aws_secrets_service, mock_secretsmanager_client
):
    # ARRANGE
    mock_secretsmanager_client.create_secret(
        Description=GlobalVariables.DESCRIPTION.value,
        Name=GlobalVariables.SECRET_NAME.value,
        SecretString=GlobalVariables.SECRET_VALUE.value,
    )

    # ACT
    secret_name, description = mock_aws_secrets_service.describe_secret(secret_name=GlobalVariables.SECRET_NAME.value)

    # ASSERT
    assertpy.assert_that(secret_name).is_equal_to(GlobalVariables.SECRET_NAME.value)
    assertpy.assert_that(description).is_equal_to(GlobalVariables.DESCRIPTION.value)


def test_get_secret_value_should_raise_exception_when_secret_does_not_exist(mock_aws_secrets_service):
    # ARRANGE & ACT
    with pytest.raises(AdapterException) as exc_info:
        mock_aws_secrets_service.get_secret_value(secret_name=GlobalVariables.SECRET_NAME.value)

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f'Unable to get secret "{GlobalVariables.SECRET_NAME.value}".'
    )


def test_get_secret_value_should_return_correct_value(mock_aws_secrets_service, mock_secretsmanager_client):
    # ARRANGE
    mock_secretsmanager_client.create_secret(
        Description=GlobalVariables.DESCRIPTION.value,
        Name=GlobalVariables.SECRET_NAME.value,
        SecretString=GlobalVariables.SECRET_VALUE.value,
    )

    # ACT
    secret_value = mock_aws_secrets_service.get_secret_value(secret_name=GlobalVariables.SECRET_NAME.value)

    # ASSERT
    assertpy.assert_that(secret_value).is_not_none()
    assertpy.assert_that(secret_value).is_equal_to(GlobalVariables.SECRET_VALUE.value)


def test_get_secrets_ids_by_path_should_return_empty_list_when_no_secrets_exist(mock_aws_secrets_service):
    # ARRANGE & ACT
    secret_ids = mock_aws_secrets_service.get_secrets_ids_by_path(path=GlobalVariables.SECRET_PATH.value)

    # ASSERT
    assertpy.assert_that(secret_ids).is_empty()


def test_get_secrets_ids_by_path_should_handle_pagination(mock_aws_secrets_service, mock_secretsmanager_client):
    # ARRANGE
    for i in range(1, 101):
        mock_secretsmanager_client.create_secret(
            Name=f"{GlobalVariables.SECRET_PATH.value}/secret{i}", SecretString=f"test-value-{i}"
        )

    # ACT
    secret_ids = mock_aws_secrets_service.get_secrets_ids_by_path(path=GlobalVariables.SECRET_PATH.value)

    # ASSERT
    assertpy.assert_that(secret_ids).is_length(100)
    for i in range(1, 101):
        assertpy.assert_that(secret_ids).contains(f"{GlobalVariables.SECRET_PATH.value}/secret{i}")


def test_get_secrets_ids_by_path_should_return_matching_secrets(mock_aws_secrets_service, mock_secretsmanager_client):
    # ARRANGE
    mock_secretsmanager_client.create_secret(
        Name=f"{GlobalVariables.SECRET_PATH.value}/secret1", SecretString="test-value-1"
    )
    mock_secretsmanager_client.create_secret(
        Name=f"{GlobalVariables.SECRET_PATH.value}/secret2", SecretString="test-value-2"
    )
    mock_secretsmanager_client.create_secret(Name="/different/path/secret3", SecretString="test-value-3")

    # ACT
    secret_ids = mock_aws_secrets_service.get_secrets_ids_by_path(path=GlobalVariables.SECRET_PATH.value)

    # ASSERT
    assertpy.assert_that(secret_ids).is_length(2)
    assertpy.assert_that(secret_ids).contains(
        f"{GlobalVariables.SECRET_PATH.value}/secret1", f"{GlobalVariables.SECRET_PATH.value}/secret2"
    )


def test_update_secret_should_update_existing_secret(mock_aws_secrets_service, mock_secretsmanager_client):
    # ARRANGE
    mock_secretsmanager_client.create_secret(
        Description=GlobalVariables.DESCRIPTION.value,
        Name=GlobalVariables.SECRET_NAME.value,
        SecretString=GlobalVariables.SECRET_VALUE.value,
    )
    updated_secret_value = "updated-secret-value"

    # ACT
    mock_aws_secrets_service.update_secret(
        secret_name=GlobalVariables.SECRET_NAME.value, secret_value=updated_secret_value
    )
    secret_value = mock_aws_secrets_service.get_secret_value(secret_name=GlobalVariables.SECRET_NAME.value)

    # ASSERT
    assertpy.assert_that(secret_value).is_equal_to(updated_secret_value)


def test_upsert_secret_should_create_new_secret(mock_aws_secrets_service):
    # ARRANGE & ACT
    mock_aws_secrets_service.upsert_secret(
        secret_name=GlobalVariables.SECRET_NAME.value,
        secret_value=GlobalVariables.SECRET_VALUE.value,
        description=GlobalVariables.DESCRIPTION.value,
    )

    # ASSERT
    secret_value = mock_aws_secrets_service.get_secret_value(secret_name=GlobalVariables.SECRET_NAME.value)
    secret_name, description = mock_aws_secrets_service.describe_secret(secret_name=GlobalVariables.SECRET_NAME.value)

    assertpy.assert_that(secret_value).is_equal_to(GlobalVariables.SECRET_VALUE.value)
    assertpy.assert_that(secret_name).is_equal_to(GlobalVariables.SECRET_NAME.value)
    assertpy.assert_that(description).is_equal_to(GlobalVariables.DESCRIPTION.value)


def test_upsert_secret_should_update_existing_secret(mock_aws_secrets_service, mock_secretsmanager_client):
    # ARRANGE
    mock_secretsmanager_client.create_secret(
        Description=GlobalVariables.DESCRIPTION.value,
        Name=GlobalVariables.SECRET_NAME.value,
        SecretString=GlobalVariables.SECRET_VALUE.value,
    )
    updated_secret_value = "updated-secret-value"

    # ACT
    mock_aws_secrets_service.upsert_secret(
        secret_name=GlobalVariables.SECRET_NAME.value, secret_value=updated_secret_value
    )
    secret_value = mock_aws_secrets_service.get_secret_value(secret_name=GlobalVariables.SECRET_NAME.value)

    # ASSERT
    assertpy.assert_that(secret_value).is_equal_to(updated_secret_value)
