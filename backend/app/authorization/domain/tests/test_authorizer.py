import assertpy

from app.authorization.domain.services.auth import authorizer


def test_authorize_when_all_steps_succeed_should_return_allow_policy(
    mock_logger,
    mock_metrics,
    mock_auth_step,
    mocked_policy_store_provider,
):
    # ARRANGE
    def __auth_step(request: authorizer.AuthorizationRequest, context: authorizer.AuthorizationContext):
        context.user_name = "test_user"
        return True

    mock_auth_step.invoke.side_effect = __auth_step

    auth = authorizer.Authorizer(
        logger=mock_logger,
        metrics=mock_metrics,
        authorization_steps=[mock_auth_step],
        stage_access_config={},
        api_config_provider=mocked_policy_store_provider,
        project_scoped_bounded_contexts=[],
    )
    # ACT
    resp = auth.authorize(
        authorizer.AuthorizationRequest(
            auth_token="token",
            api_id="api-id",
            operation_id="operation",
            resource_ids={},
            resource="test",
            resource_path="/some/path",
        )
    )

    assertpy.assert_that(resp).is_equal_to(
        {
            "context": {
                "userName": "TEST_USER",
                "userEmail": None,
                "stages": "[]",
                "userRoles": "[]",
                "userDomains": "[]",
            },
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [{"Action": "execute-api:Invoke", "Effect": "Allow", "Resource": "test"}],
            },
            "principalId": "TEST_USER",
        }
    )


def test_authorize_when_all_steps_succeed_but_user_name_not_resolved_should_deny(
    mock_logger,
    mock_metrics,
    mock_auth_step,
    mocked_policy_store_provider,
):
    # ARRANGE
    mock_auth_step.invoke.return_value = True

    auth = authorizer.Authorizer(
        logger=mock_logger,
        metrics=mock_metrics,
        authorization_steps=[mock_auth_step],
        stage_access_config={},
        api_config_provider=mocked_policy_store_provider,
        project_scoped_bounded_contexts=[],
    )
    # ACT
    resp = auth.authorize(
        authorizer.AuthorizationRequest(
            auth_token="token",
            api_id="api-id",
            operation_id="operation",
            resource_ids={},
            resource="test",
            resource_path="/some/path",
        )
    )

    assertpy.assert_that(resp).is_equal_to(
        {
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [{"Action": "execute-api:Invoke", "Effect": "Deny", "Resource": "*"}],
            },
            "principalId": "me",
        }
    )


def test_authorize_when_step_fails_should_return_deny_policy(
    mock_logger,
    mock_metrics,
    mock_auth_step,
    mocked_policy_store_provider,
):
    # ARRANGE
    mock_auth_step.invoke.return_value = False

    auth = authorizer.Authorizer(
        logger=mock_logger,
        metrics=mock_metrics,
        authorization_steps=[mock_auth_step],
        stage_access_config={},
        api_config_provider=mocked_policy_store_provider,
        project_scoped_bounded_contexts=[],
    )
    # ACT
    resp = auth.authorize(
        authorizer.AuthorizationRequest(
            auth_token="token",
            api_id="api-id",
            operation_id="operation",
            resource_ids={},
            resource="test",
            resource_path="/some/path",
        )
    )

    assertpy.assert_that(resp).is_equal_to(
        {
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [{"Action": "execute-api:Invoke", "Effect": "Deny", "Resource": "*"}],
            },
            "principalId": "me",
        }
    )


def test_authorize_when_step_raises_exception_should_return_deny_policy(
    mock_logger,
    mock_metrics,
    mock_auth_step,
    mocked_policy_store_provider,
):
    # ARRANGE
    mock_auth_step.invoke.side_effect = Exception("error")

    auth = authorizer.Authorizer(
        logger=mock_logger,
        metrics=mock_metrics,
        authorization_steps=[mock_auth_step],
        stage_access_config={},
        api_config_provider=mocked_policy_store_provider,
        project_scoped_bounded_contexts=[],
    )
    # ACT
    resp = auth.authorize(
        authorizer.AuthorizationRequest(
            auth_token="token",
            api_id="api-id",
            operation_id="operation",
            resource_ids={},
            resource="test",
            resource_path="/some/path",
        )
    )

    assertpy.assert_that(resp).is_equal_to(
        {
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [{"Action": "execute-api:Invoke", "Effect": "Deny", "Resource": "*"}],
            },
            "principalId": "me",
        }
    )
