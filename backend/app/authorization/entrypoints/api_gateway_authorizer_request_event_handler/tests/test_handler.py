from unittest import mock

import assertpy
from freezegun import freeze_time


@mock.patch("urllib.request.urlopen")
@freeze_time("2025-05-02 09:00:00+00:00")
def test_authorizer_lambda_handler_successful_authorization(
    mock_urlopen,
    lambda_context,
    mock_user_info_endpoint,
    mocked_assignments_data,
    mock_auth_event,
    mocked_jwks_response,
    backend_app_dynamodb_table,
):
    """Test successful authorization scenario"""
    # ARRANGE
    mocked_assignments_data()

    mm = mock.MagicMock()
    mm.__enter__.return_value = mocked_jwks_response
    mock_urlopen.return_value = mm
    from app.authorization.entrypoints.api_gateway_authorizer_request_event_handler import (
        handler,
    )

    handler.dependencies.jwk_client.fetch_data()

    # Act
    result = handler.handler(mock_auth_event(), lambda_context)

    # Assert
    assertpy.assert_that(result).is_equal_to(
        {
            "context": {
                "userName": "T00112233",
                "userEmail": "test@test.com",
                "stages": '["prod"]',
                "userRoles": '["PLATFORM_USER"]',
                "userDomains": '["TEST_DOMAIN"]',
                "stages": '["prod"]',
            },
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "execute-api:Invoke",
                        "Effect": "Allow",
                        "Resource": "arn:aws:execute-api:us-east-1:123:abcdef/v1/GET/projects",
                    }
                ],
            },
            "principalId": "T00112233",
        }
    )


@mock.patch("urllib.request.urlopen")
@freeze_time("2025-05-02 09:00:00+00:00")
def test_authorizer_lambda_handler_invalid_token(
    mock_urlopen,
    lambda_context,
    mock_user_info_endpoint,
    mocked_assignments_data,
    mock_auth_event,
    mocked_jwks_response,
    backend_app_dynamodb_table,
):
    mocked_assignments_data()

    mm = mock.MagicMock()
    mm.__enter__.return_value = mocked_jwks_response
    mock_urlopen.return_value = mm

    from app.authorization.entrypoints.api_gateway_authorizer_request_event_handler import (
        handler,
    )

    handler.dependencies.jwk_client.fetch_data()

    # Act
    result = handler.handler(mock_auth_event(authorization="Bearer token"), lambda_context)

    # Assert
    assertpy.assert_that(result).is_equal_to(
        {
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [{"Action": "execute-api:Invoke", "Effect": "Deny", "Resource": "*"}],
            },
            "principalId": "me",
        }
    )


@mock.patch("urllib.request.urlopen")
@freeze_time("2025-05-02 09:00:00+00:00")
def test_authorizer_lambda_handler_bad_user_info_response(
    mock_urlopen,
    lambda_context,
    mock_user_info_endpoint_401,
    mocked_assignments_data,
    mock_auth_event,
    mocked_jwks_response,
    backend_app_dynamodb_table,
):
    mocked_assignments_data()

    mm = mock.MagicMock()
    mm.__enter__.return_value = mocked_jwks_response
    mock_urlopen.return_value = mm

    from app.authorization.entrypoints.api_gateway_authorizer_request_event_handler import (
        handler,
    )

    handler.dependencies.jwk_client.fetch_data()

    # Act
    result = handler.handler(mock_auth_event(), lambda_context)

    # Assert
    assertpy.assert_that(result).is_equal_to(
        {
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [{"Action": "execute-api:Invoke", "Effect": "Deny", "Resource": "*"}],
            },
            "principalId": "me",
        }
    )


@mock.patch("urllib.request.urlopen")
@freeze_time("2025-05-02 09:00:00+00:00")
def test_authorizer_lambda_handler_unauthorized_action(
    mock_urlopen,
    lambda_context,
    mock_user_info_endpoint,
    mocked_assignments_data,
    mock_auth_event,
    mocked_jwks_response,
    mock_avp_is_authorized_request,
    mock_is_authorized_denied_response,
    backend_app_dynamodb_table,
):
    # Arrange
    mocked_assignments_data()

    mock_avp_is_authorized_request.return_value = mock_is_authorized_denied_response
    mm = mock.MagicMock()
    mm.__enter__.return_value = mocked_jwks_response
    mock_urlopen.return_value = mm

    from app.authorization.entrypoints.api_gateway_authorizer_request_event_handler import (
        handler,
    )

    handler.dependencies.jwk_client.fetch_data()

    # Act
    result = handler.handler(mock_auth_event(), lambda_context)

    # Assert
    assertpy.assert_that(result).is_equal_to(
        {
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [{"Action": "execute-api:Invoke", "Effect": "Deny", "Resource": "*"}],
            },
            "principalId": "me",
        }
    )


@mock.patch("urllib.request.urlopen")
@freeze_time("2025-05-02 09:00:00+00:00")
def test_authorizer_lambda_handler_multiple_roles_and_domains(
    mock_urlopen,
    lambda_context,
    mock_user_info_endpoint,
    mocked_assignments_data,
    mock_auth_event,
    mocked_jwks_response,
    backend_app_dynamodb_table,
):
    mocked_assignments_data(
        roles=["PLATFORM_USER", "ADMIN"], active_directory_groups=[{"domain": "domain1"}, {"domain": "domain2"}]
    )

    mm = mock.MagicMock()
    mm.__enter__.return_value = mocked_jwks_response
    mock_urlopen.return_value = mm

    from app.authorization.entrypoints.api_gateway_authorizer_request_event_handler import (
        handler,
    )

    handler.dependencies.jwk_client.fetch_data()

    # Act
    result = handler.handler(mock_auth_event(), lambda_context)

    # Assert
    assertpy.assert_that(result).is_equal_to(
        {
            "context": {
                "userName": "T00112233",
                "userEmail": "test@test.com",
                "stages": '["dev", "prod", "qa"]',
                "userRoles": '["ADMIN", "PLATFORM_USER"]',
                "userDomains": '["domain1", "domain2"]',
            },
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "execute-api:Invoke",
                        "Effect": "Allow",
                        "Resource": "arn:aws:execute-api:us-east-1:123:abcdef/v1/GET/projects",
                    }
                ],
            },
            "principalId": "T00112233",
        }
    )


@mock.patch("urllib.request.urlopen")
@freeze_time("2025-05-02 09:00:00+00:00")
def test_authorizer_lambda_handler_when_no_assignments(
    mock_urlopen,
    lambda_context,
    mock_user_info_endpoint,
    mock_auth_event,
    mocked_jwks_response,
    backend_app_dynamodb_table,
):
    mm = mock.MagicMock()
    mm.__enter__.return_value = mocked_jwks_response
    mock_urlopen.return_value = mm

    from app.authorization.entrypoints.api_gateway_authorizer_request_event_handler import (
        handler,
    )

    handler.dependencies.jwk_client.fetch_data()

    # Act
    result = handler.handler(mock_auth_event(), lambda_context)

    # Assert
    assertpy.assert_that(result).is_equal_to(
        {
            "context": {
                "userName": "T00112233",
                "userEmail": "test@test.com",
                "stages": "[]",
                "userRoles": "[]",
                "userDomains": "[]",
            },
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "execute-api:Invoke",
                        "Effect": "Allow",
                        "Resource": "arn:aws:execute-api:us-east-1:123:abcdef/v1/GET/projects",
                    }
                ],
            },
            "principalId": "T00112233",
        }
    )


@mock.patch("urllib.request.urlopen")
@freeze_time("2025-05-02 09:00:00+00:00")
def test_authorizer_lambda_handler_when_not_in_a_project_scope(
    mock_urlopen,
    lambda_context,
    mock_user_info_endpoint,
    mocked_assignments_data,
    mock_auth_event,
    mocked_jwks_response,
    backend_app_dynamodb_table,
):
    mocked_assignments_data()

    mm = mock.MagicMock()
    mm.__enter__.return_value = mocked_jwks_response
    mock_urlopen.return_value = mm

    from app.authorization.entrypoints.api_gateway_authorizer_request_event_handler import (
        handler,
    )

    handler.dependencies.jwk_client.fetch_data()

    # Act
    result = handler.handler(mock_auth_event(path_parameters={}), lambda_context)

    # Assert
    assertpy.assert_that(result).is_equal_to(
        {
            "context": {
                "userName": "T00112233",
                "userEmail": "test@test.com",
                "stages": "[]",
                "userRoles": "[]",
                "userDomains": "[]",
            },
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "execute-api:Invoke",
                        "Effect": "Allow",
                        "Resource": "arn:aws:execute-api:us-east-1:123:abcdef/v1/GET/projects",
                    }
                ],
            },
            "principalId": "T00112233",
        }
    )
