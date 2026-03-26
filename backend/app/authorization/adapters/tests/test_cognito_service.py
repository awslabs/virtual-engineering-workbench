from unittest import mock

import jwt
import requests
from aws_lambda_powertools.metrics import MetricUnit


def test_get_signing_key_from_jwt_returns_success_for_valid_token(
    mock_cognito_service, valid_jwt_token, mock_jwk_client, mock_logger
):
    # Arrange
    mock_signing_key = mock.MagicMock()
    mock_signing_key.key = "test_key"
    mock_signing_key.key_id = "test_kid"
    mock_jwk_client.get_signing_key_from_jwt.return_value = mock_signing_key

    # Act
    success, signing_key = mock_cognito_service.get_signing_key_from_jwt(valid_jwt_token)

    # Assert
    assert success is True
    assert signing_key == mock_signing_key
    mock_jwk_client.get_signing_key_from_jwt.assert_called_once_with(valid_jwt_token)
    mock_logger.debug.assert_called_once_with("Getting signing key from JWT token.")
    mock_logger.exception.assert_not_called()


def test_get_signing_key_from_jwt_returns_failure_for_jwk_client_error(
    mock_cognito_service, valid_jwt_token, mock_jwk_client, mock_metrics
):
    # Arrange
    mock_jwk_client.get_signing_key_from_jwt.side_effect = jwt.exceptions.PyJWKClientError("Error")

    # Act
    success, signing_key = mock_cognito_service.get_signing_key_from_jwt(valid_jwt_token)

    # Assert
    assert success is False
    assert signing_key is None
    mock_metrics.add_metric.assert_called_with(name="SigningKeyError", unit=MetricUnit.Count, value=1)


def test_get_signing_key_from_jwt_returns_failure_for_unexpected_error(
    mock_cognito_service, valid_jwt_token, mock_jwk_client, mock_logger, mock_metrics
):
    # Arrange
    mock_jwk_client.get_signing_key_from_jwt.side_effect = Exception("Unexpected error")

    # Act
    success, signing_key = mock_cognito_service.get_signing_key_from_jwt(valid_jwt_token)

    # Assert
    assert success is False
    assert signing_key is None
    mock_logger.exception.assert_called_once_with("Unexpected error while getting signing key")
    mock_metrics.add_metric.assert_called_with(name="UnexpectedSigningKeyError", unit=MetricUnit.Count, value=1)


def test_get_user_info_returns_user_data_for_valid_token(
    mock_cognito_service, mock_requests_get, mock_user_info_response
):
    # Arrange
    mock_response = mock.MagicMock()
    mock_response.json.return_value = mock_user_info_response
    mock_requests_get.return_value = mock_response

    # Act
    result = mock_cognito_service.get_user_info("Bearer valid_token")

    # Assert
    assert result == mock_user_info_response
    mock_requests_get.assert_called_once_with(
        url=mock_cognito_service._cognito_user_info_uri, headers={"Authorization": "Bearer valid_token"}, timeout=3
    )


def test_get_user_info_returns_empty_dict_for_invalid_token(
    mock_cognito_service, mock_requests_get, mock_metrics, mock_logger
):
    # Arrange
    mock_response = mock.Mock()
    mock_response.status_code = 401
    mock_requests_get.side_effect = requests.exceptions.HTTPError(response=mock_response)

    # Act
    result = mock_cognito_service.get_user_info("Bearer invalid_token")

    # Assert
    assert result == {}
    mock_metrics.add_metric.assert_called_with(name="CognitoInvalidToken", unit=MetricUnit.Count, value=1)
    mock_logger.exception.assert_called_once()
    assert "Cognito response code: 401" in mock_logger.exception.call_args[0][0]


def test_get_jwks_cache_returns_none_when_no_cache(mock_cognito_service, mock_jwk_client):
    # Arrange
    mock_jwk_client.jwk_set_cache = None

    # Act
    result = mock_cognito_service._get_jwks_cache()

    # Assert
    assert result is None


def test_get_jwks_cache_returns_cache_when_available(mock_cognito_service, mock_jwk_client):
    # Arrange
    mock_jwk_set = {"keys": [{"kid": "key1"}]}
    mock_jwk_client.jwk_set_cache = mock.MagicMock()
    mock_jwk_client.jwk_set_cache.jwk_set_with_timestamp.jwk_set = mock_jwk_set

    # Act
    result = mock_cognito_service._get_jwks_cache()

    # Assert
    assert result == mock_jwk_set
