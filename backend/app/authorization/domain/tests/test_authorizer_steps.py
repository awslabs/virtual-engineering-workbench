import assertpy
import pytest
from freezegun import freeze_time

from app.authorization.domain.read_models import project_assignment
from app.authorization.domain.services.auth import authorizer, authorizer_steps


def test_amazon_verified_permissions_when_api_id_not_in_map_should_deny(
    mock_logger, mock_authz_service, mocked_policy_store_provider_no_policy
):
    # ARRANGE
    step = authorizer_steps.AmazonVerifiedPermissionsAuthorizer(
        authz_service=mock_authz_service,
        logger=mock_logger,
        entity_resolvers=[],
    )
    # ACT

    resp = step.invoke(
        request=authorizer.AuthorizationRequest(
            auth_token="token",
            api_id="api-id",
            operation_id="operation",
            resource_ids={},
            resource="test",
            resource_path="/some/path",
        ),
        context=authorizer.AuthorizationContext(
            user_name="test",
            api_auth_cfg=mocked_policy_store_provider_no_policy("api-id"),
            project_scoped_bounded_contexts=[],
        ),
    )

    # ASSERT
    assertpy.assert_that(resp).is_false()


def test_amazon_verified_permissions_when_project_scoped_and_has_assignments(
    mock_logger, mock_authz_service, mocked_policy_store_provider
):
    # ARRANGE
    step = authorizer_steps.AmazonVerifiedPermissionsAuthorizer(
        authz_service=mock_authz_service,
        logger=mock_logger,
        entity_resolvers=[authorizer_steps.VEWProjectAssignmentEntityResolver()],
    )
    # ACT

    auth_result = step.invoke(
        request=authorizer.AuthorizationRequest(
            auth_token="token",
            api_id="api-id",
            operation_id="UpdateProject",
            resource_ids={"projectId": "project456"},
            resource="test",
            resource_path="/projects/{projectId}",
        ),
        context=authorizer.AuthorizationContext(
            user_name="test-user",
            project_assignments=[
                project_assignment.Assignment(
                    userId="", projectId="project456", roles=["PLATFORM_USER"], groupMemberships=["VEW_USERS"]
                )
            ],
            api_auth_cfg=mocked_policy_store_provider("api-id"),
            project_scoped_bounded_contexts=["projects"],
        ),
    )

    # ASSERT
    assertpy.assert_that(auth_result).is_true()
    mock_authz_service.is_action_allowed.assert_called_once_with(
        policy_store_id="policy-store-id",
        principal={"entityId": "test-user", "entityType": "VEW::User"},
        action={"actionId": "UpdateProject", "actionType": "VEW::Action"},
        resource={"entityId": "project456", "entityType": "VEW::Project"},
        entities={
            "entityList": [
                {
                    "identifier": {"entityId": "test-user", "entityType": "VEW::User"},
                    "attributes": {"totalAdminAssignments": {"long": 0}},
                    "parents": [
                        {"entityId": "project456#PLATFORM_USER", "entityType": "VEW::ProjectAssignment"},
                        {"entityId": "project456#GROUP#VEW_USERS", "entityType": "VEW::ProjectAssignment"},
                    ],
                },
                {
                    "identifier": {"entityId": "project456", "entityType": "VEW::Project"},
                    "attributes": {
                        "admins": {
                            "entityIdentifier": {"entityId": "project456#ADMIN", "entityType": "VEW::ProjectAssignment"}
                        },
                        "programOwners": {
                            "entityIdentifier": {
                                "entityId": "project456#PROGRAM_OWNER",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "powerUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#POWER_USER",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "productContributors": {
                            "entityIdentifier": {
                                "entityId": "project456#PRODUCT_CONTRIBUTOR",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "betaUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#BETA_USER",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "platformUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#PLATFORM_USER",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "vewUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#GROUP#VEW_USERS",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "hilUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#GROUP#HIL_USERS",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "vvplUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#GROUP#VVPL_USERS",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                    },
                    "parents": [],
                },
                {
                    "identifier": {"entityId": "project456#ADMIN", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [{"entityId": "project456#PROGRAM_OWNER", "entityType": "VEW::ProjectAssignment"}],
                },
                {
                    "identifier": {"entityId": "project456#PROGRAM_OWNER", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [{"entityId": "project456#POWER_USER", "entityType": "VEW::ProjectAssignment"}],
                },
                {
                    "identifier": {"entityId": "project456#POWER_USER", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [{"entityId": "project456#PRODUCT_CONTRIBUTOR", "entityType": "VEW::ProjectAssignment"}],
                },
                {
                    "identifier": {
                        "entityId": "project456#PRODUCT_CONTRIBUTOR",
                        "entityType": "VEW::ProjectAssignment",
                    },
                    "attributes": {},
                    "parents": [{"entityId": "project456#BETA_USER", "entityType": "VEW::ProjectAssignment"}],
                },
                {
                    "identifier": {"entityId": "project456#BETA_USER", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [{"entityId": "project456#PLATFORM_USER", "entityType": "VEW::ProjectAssignment"}],
                },
                {
                    "identifier": {"entityId": "project456#PLATFORM_USER", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [],
                },
                {
                    "identifier": {"entityId": "project456#GROUP#VEW_USERS", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [],
                },
                {
                    "identifier": {"entityId": "project456#GROUP#HIL_USERS", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [],
                },
                {
                    "identifier": {"entityId": "project456#GROUP#VVPL_USERS", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [],
                },
            ]
        },
    )


def test_amazon_verified_permissions_when_project_assignment_feature_enabled_and_has_assignments(
    mock_logger, mock_authz_service, mocked_policy_store_provider_project_assignment_feature
):
    # ARRANGE
    step = authorizer_steps.AmazonVerifiedPermissionsAuthorizer(
        authz_service=mock_authz_service,
        logger=mock_logger,
        entity_resolvers=[authorizer_steps.VEWProjectAssignmentEntityResolver()],
    )
    # ACT
    auth_result = step.invoke(
        request=authorizer.AuthorizationRequest(
            auth_token="token",
            api_id="api-id",
            operation_id="UpdateProject",
            resource_ids={"projectId": "project456"},
            resource="test",
            resource_path="/projects/{projectId}",
        ),
        context=authorizer.AuthorizationContext(
            user_name="test-user",
            project_assignments=[
                project_assignment.Assignment(
                    userId="", projectId="project456", roles=["PLATFORM_USER"], groupMemberships=["VEW_USERS"]
                )
            ],
            api_auth_cfg=mocked_policy_store_provider_project_assignment_feature("api-id"),
        ),
    )

    # ASSERT
    assertpy.assert_that(auth_result).is_true()
    mock_authz_service.is_action_allowed.assert_called_once_with(
        policy_store_id="policy-store-id",
        principal={"entityId": "test-user", "entityType": "VEW::User"},
        action={"actionId": "UpdateProject", "actionType": "VEW::Action"},
        resource={"entityId": "project456", "entityType": "VEW::Project"},
        entities={
            "entityList": [
                {
                    "identifier": {"entityId": "test-user", "entityType": "VEW::User"},
                    "attributes": {
                        "totalAdminAssignments": {
                            "long": 0,
                        }
                    },
                    "parents": [
                        {"entityId": "project456#PLATFORM_USER", "entityType": "VEW::ProjectAssignment"},
                        {"entityId": "project456#GROUP#VEW_USERS", "entityType": "VEW::ProjectAssignment"},
                    ],
                },
                {
                    "identifier": {"entityId": "project456", "entityType": "VEW::Project"},
                    "attributes": {
                        "admins": {
                            "entityIdentifier": {"entityId": "project456#ADMIN", "entityType": "VEW::ProjectAssignment"}
                        },
                        "programOwners": {
                            "entityIdentifier": {
                                "entityId": "project456#PROGRAM_OWNER",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "powerUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#POWER_USER",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "productContributors": {
                            "entityIdentifier": {
                                "entityId": "project456#PRODUCT_CONTRIBUTOR",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "betaUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#BETA_USER",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "platformUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#PLATFORM_USER",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "vewUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#GROUP#VEW_USERS",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "hilUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#GROUP#HIL_USERS",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "vvplUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#GROUP#VVPL_USERS",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                    },
                    "parents": [],
                },
                {
                    "identifier": {"entityId": "project456#ADMIN", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [{"entityId": "project456#PROGRAM_OWNER", "entityType": "VEW::ProjectAssignment"}],
                },
                {
                    "identifier": {"entityId": "project456#PROGRAM_OWNER", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [{"entityId": "project456#POWER_USER", "entityType": "VEW::ProjectAssignment"}],
                },
                {
                    "identifier": {"entityId": "project456#POWER_USER", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [{"entityId": "project456#PRODUCT_CONTRIBUTOR", "entityType": "VEW::ProjectAssignment"}],
                },
                {
                    "identifier": {
                        "entityId": "project456#PRODUCT_CONTRIBUTOR",
                        "entityType": "VEW::ProjectAssignment",
                    },
                    "attributes": {},
                    "parents": [{"entityId": "project456#BETA_USER", "entityType": "VEW::ProjectAssignment"}],
                },
                {
                    "identifier": {"entityId": "project456#BETA_USER", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [{"entityId": "project456#PLATFORM_USER", "entityType": "VEW::ProjectAssignment"}],
                },
                {
                    "identifier": {"entityId": "project456#PLATFORM_USER", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [],
                },
                {
                    "identifier": {"entityId": "project456#GROUP#VEW_USERS", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [],
                },
                {
                    "identifier": {"entityId": "project456#GROUP#HIL_USERS", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [],
                },
                {
                    "identifier": {"entityId": "project456#GROUP#VVPL_USERS", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [],
                },
            ]
        },
    )


def test_amazon_verified_permissions_when_has_assignments_should_set_total_admin_assignments(
    mock_logger, mock_authz_service, mocked_policy_store_provider
):
    # ARRANGE
    step = authorizer_steps.AmazonVerifiedPermissionsAuthorizer(
        authz_service=mock_authz_service,
        logger=mock_logger,
        entity_resolvers=[authorizer_steps.VEWProjectAssignmentEntityResolver()],
    )
    # ACT

    step.invoke(
        request=authorizer.AuthorizationRequest(
            auth_token="token",
            api_id="api-id",
            operation_id="UpdateProject",
            resource_ids={},
            resource="test",
            resource_path="/smth",
        ),
        context=authorizer.AuthorizationContext(
            user_name="test-user",
            project_assignments=[
                project_assignment.Assignment(
                    userId="", projectId="project456", roles=["PLATFORM_USER"], groupMemberships=["VEW_USERS"]
                ),
                project_assignment.Assignment(
                    userId="", projectId="project123", roles=["ADMIN"], groupMemberships=["VEW_USERS"]
                ),
            ],
            api_auth_cfg=mocked_policy_store_provider("api-id"),
            project_scoped_bounded_contexts=["projects"],
        ),
    )

    # ASSERT
    mock_authz_service.is_action_allowed.assert_called_once_with(
        policy_store_id="policy-store-id",
        principal={"entityId": "test-user", "entityType": "VEW::User"},
        action={"actionId": "UpdateProject", "actionType": "VEW::Action"},
        resource=None,
        entities={
            "entityList": [
                {
                    "identifier": {"entityId": "test-user", "entityType": "VEW::User"},
                    "attributes": {
                        "totalAdminAssignments": {
                            "long": 1,
                        }
                    },
                    "parents": [
                        {"entityId": "project456#PLATFORM_USER", "entityType": "VEW::ProjectAssignment"},
                        {"entityId": "project123#ADMIN", "entityType": "VEW::ProjectAssignment"},
                        {"entityId": "project456#GROUP#VEW_USERS", "entityType": "VEW::ProjectAssignment"},
                        {"entityId": "project123#GROUP#VEW_USERS", "entityType": "VEW::ProjectAssignment"},
                    ],
                },
            ]
        },
    )


def test_amazon_verified_permissions_when_project_id_but_no_assignments(
    mock_logger, mock_authz_service, mocked_policy_store_provider
):
    # ARRANGE
    step = authorizer_steps.AmazonVerifiedPermissionsAuthorizer(
        authz_service=mock_authz_service,
        logger=mock_logger,
        entity_resolvers=[authorizer_steps.VEWProjectAssignmentEntityResolver()],
    )
    # ACT

    step.invoke(
        request=authorizer.AuthorizationRequest(
            auth_token="token",
            api_id="api-id",
            operation_id="UpdateProject",
            resource_ids={"projectId": "project456"},
            resource="test",
            resource_path="/projects/{projectId}",
        ),
        context=authorizer.AuthorizationContext(
            user_name="test-user",
            roles=[],
            project_assignments=[],
            api_auth_cfg=mocked_policy_store_provider("api-id"),
            project_scoped_bounded_contexts=["projects"],
        ),
    )

    # ASSERT
    mock_authz_service.is_action_allowed.assert_called_once_with(
        policy_store_id="policy-store-id",
        principal={"entityId": "test-user", "entityType": "VEW::User"},
        action={"actionId": "UpdateProject", "actionType": "VEW::Action"},
        resource={"entityId": "project456", "entityType": "VEW::Project"},
        entities={
            "entityList": [
                {
                    "identifier": {"entityId": "test-user", "entityType": "VEW::User"},
                    "attributes": {
                        "totalAdminAssignments": {
                            "long": 0,
                        }
                    },
                    "parents": [],
                },
                {
                    "identifier": {"entityId": "project456", "entityType": "VEW::Project"},
                    "attributes": {
                        "admins": {
                            "entityIdentifier": {"entityId": "project456#ADMIN", "entityType": "VEW::ProjectAssignment"}
                        },
                        "programOwners": {
                            "entityIdentifier": {
                                "entityId": "project456#PROGRAM_OWNER",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "powerUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#POWER_USER",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "productContributors": {
                            "entityIdentifier": {
                                "entityId": "project456#PRODUCT_CONTRIBUTOR",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "betaUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#BETA_USER",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "platformUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#PLATFORM_USER",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "vewUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#GROUP#VEW_USERS",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "hilUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#GROUP#HIL_USERS",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                        "vvplUsers": {
                            "entityIdentifier": {
                                "entityId": "project456#GROUP#VVPL_USERS",
                                "entityType": "VEW::ProjectAssignment",
                            }
                        },
                    },
                    "parents": [],
                },
                {
                    "identifier": {"entityId": "project456#ADMIN", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [{"entityId": "project456#PROGRAM_OWNER", "entityType": "VEW::ProjectAssignment"}],
                },
                {
                    "identifier": {"entityId": "project456#PROGRAM_OWNER", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [{"entityId": "project456#POWER_USER", "entityType": "VEW::ProjectAssignment"}],
                },
                {
                    "identifier": {"entityId": "project456#POWER_USER", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [{"entityId": "project456#PRODUCT_CONTRIBUTOR", "entityType": "VEW::ProjectAssignment"}],
                },
                {
                    "identifier": {
                        "entityId": "project456#PRODUCT_CONTRIBUTOR",
                        "entityType": "VEW::ProjectAssignment",
                    },
                    "attributes": {},
                    "parents": [{"entityId": "project456#BETA_USER", "entityType": "VEW::ProjectAssignment"}],
                },
                {
                    "identifier": {"entityId": "project456#BETA_USER", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [{"entityId": "project456#PLATFORM_USER", "entityType": "VEW::ProjectAssignment"}],
                },
                {
                    "identifier": {"entityId": "project456#PLATFORM_USER", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [],
                },
                {
                    "identifier": {"entityId": "project456#GROUP#VEW_USERS", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [],
                },
                {
                    "identifier": {"entityId": "project456#GROUP#HIL_USERS", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [],
                },
                {
                    "identifier": {"entityId": "project456#GROUP#VVPL_USERS", "entityType": "VEW::ProjectAssignment"},
                    "attributes": {},
                    "parents": [],
                },
            ]
        },
    )


def test_amazon_verified_permissions_when_has_no_project_id_should_set_resource_to_none(
    mock_logger, mock_authz_service, mocked_policy_store_provider
):
    # ARRANGE
    step = authorizer_steps.AmazonVerifiedPermissionsAuthorizer(
        authz_service=mock_authz_service,
        logger=mock_logger,
        entity_resolvers=[authorizer_steps.VEWProjectAssignmentEntityResolver()],
    )
    # ACT

    step.invoke(
        request=authorizer.AuthorizationRequest(
            auth_token="token",
            api_id="api-id",
            operation_id="UpdateProject",
            resource_ids={},
            resource="test",
            resource_path="/projects/{projectId}",
        ),
        context=authorizer.AuthorizationContext(
            user_name="test-user",
            roles=[],
            api_auth_cfg=mocked_policy_store_provider("api-id"),
            project_scoped_bounded_contexts=["projects"],
        ),
    )

    # ASSERT
    mock_authz_service.is_action_allowed.assert_called_once_with(
        policy_store_id="policy-store-id",
        principal={"entityId": "test-user", "entityType": "VEW::User"},
        action={"actionId": "UpdateProject", "actionType": "VEW::Action"},
        resource=None,
        entities={
            "entityList": [
                {
                    "identifier": {"entityId": "test-user", "entityType": "VEW::User"},
                    "attributes": {
                        "totalAdminAssignments": {
                            "long": 0,
                        }
                    },
                    "parents": [],
                },
            ]
        },
    )


def test_jwt_authorizer_when_no_signing_key_in_jwks_should_deny(
    mock_logger, mock_metrics, mock_auth_service, user_auth_jwt, jwt_issuer
):
    # ARRANGE
    mock_auth_service.get_signing_key_from_jwt.return_value = (False, None)

    verify_jwt = authorizer_steps.JWTAuthorizer(
        auth_srv=mock_auth_service, metrics=mock_metrics, logger=mock_logger, issuer=jwt_issuer
    )

    # ACT
    auth_result = verify_jwt.invoke(
        request=authorizer.AuthorizationRequest(
            auth_token=user_auth_jwt(),
            api_id="api-id",
            operation_id="UpdateProject",
            resource_ids={},
            resource="test",
            resource_path="/path",
        ),
        context=authorizer.AuthorizationContext(
            user_name="test-user",
            api_auth_cfg={},
        ),
    )

    # ASSERT
    assertpy.assert_that(auth_result).is_false()


@freeze_time("2025-05-02 09:00:00+00:00")
def test_jwt_authorizer_when_invalid_signature_should_deny(
    mock_logger, mock_metrics, mock_auth_service, mocked_jwks_response, user_auth_jwt_wrong, jwt_issuer
):
    # ARRANGE
    mock_auth_service.get_signing_key_from_jwt.return_value = (True, mocked_jwks_response)

    verify_jwt = authorizer_steps.JWTAuthorizer(
        auth_srv=mock_auth_service, metrics=mock_metrics, logger=mock_logger, issuer=jwt_issuer
    )

    # ACT
    auth_result = verify_jwt.invoke(
        request=authorizer.AuthorizationRequest(
            auth_token=user_auth_jwt_wrong,
            api_id="api-id",
            operation_id="UpdateProject",
            resource_ids={},
            resource="test",
            resource_path="/path",
        ),
        context=authorizer.AuthorizationContext(
            user_name="test-user",
            api_auth_cfg={},
        ),
    )

    # ASSERT
    assertpy.assert_that(auth_result).is_false()
    mock_logger.exception.assert_called_once_with("The JWT token has an invalid signature")


@freeze_time("2025-05-02 11:00:00")
def test_jwt_authorizer_when_expired_should_deny(
    mock_logger, mock_metrics, mock_auth_service, mocked_jwks_response, user_auth_jwt, jwt_issuer
):
    # ARRANGE
    mock_auth_service.get_signing_key_from_jwt.return_value = (True, mocked_jwks_response)

    verify_jwt = authorizer_steps.JWTAuthorizer(
        auth_srv=mock_auth_service,
        metrics=mock_metrics,
        logger=mock_logger,
        issuer=jwt_issuer,
    )

    # ACT
    auth_result = verify_jwt.invoke(
        request=authorizer.AuthorizationRequest(
            auth_token=user_auth_jwt(),
            api_id="api-id",
            operation_id="UpdateProject",
            resource_ids={},
            resource="test",
            resource_path="/path",
        ),
        context=authorizer.AuthorizationContext(
            user_name="test-user",
            api_auth_cfg={},
        ),
    )

    # ASSERT
    assertpy.assert_that(auth_result).is_false()
    mock_logger.exception.assert_called_once_with("The JWT token has expired")


@freeze_time("2025-05-02 09:00:00+00:00")
def test_jwt_authorizer_when_wrong_issuer_should_deny(
    mock_logger, mock_metrics, mock_auth_service, mocked_jwks_response, user_auth_jwt
):
    # ARRANGE
    mock_auth_service.get_signing_key_from_jwt.return_value = (True, mocked_jwks_response)

    verify_jwt = authorizer_steps.JWTAuthorizer(
        auth_srv=mock_auth_service,
        metrics=mock_metrics,
        logger=mock_logger,
        issuer="wrong-issuer",
    )

    # ACT
    auth_result = verify_jwt.invoke(
        request=authorizer.AuthorizationRequest(
            auth_token=user_auth_jwt(),
            api_id="api-id",
            operation_id="UpdateProject",
            resource_ids={},
            resource="test",
            resource_path="/path",
        ),
        context=authorizer.AuthorizationContext(
            user_name="test-user",
            api_auth_cfg={},
        ),
    )

    # ASSERT
    assertpy.assert_that(auth_result).is_false()
    mock_logger.exception.assert_called_once_with("Unexpected error while validating JWT")


@freeze_time("2025-05-02 09:00:00+00:00")
def test_jwt_authorizer_when_wrong_audience_should_deny(
    mock_logger, mock_metrics, mock_auth_service, mocked_jwks_response, user_auth_jwt, jwt_issuer
):
    # ARRANGE
    mock_auth_service.get_signing_key_from_jwt.return_value = (True, mocked_jwks_response)

    verify_jwt = authorizer_steps.JWTAuthorizer(
        auth_srv=mock_auth_service,
        metrics=mock_metrics,
        logger=mock_logger,
        issuer=jwt_issuer,
        audiences=["wrong-audience"],
    )

    # ACT
    auth_result = verify_jwt.invoke(
        request=authorizer.AuthorizationRequest(
            auth_token=user_auth_jwt(),
            api_id="api-id",
            operation_id="UpdateProject",
            resource_ids={},
            resource="test",
            resource_path="/path",
        ),
        context=authorizer.AuthorizationContext(
            user_name="test-user",
            api_auth_cfg={},
        ),
    )

    # ASSERT
    assertpy.assert_that(auth_result).is_false()
    mock_logger.error.assert_called_once_with("The JWT token has an invalid audience")


@freeze_time("2025-05-02 09:00:00+00:00")
def test_jwt_authorizer_when_jwt_has_wrong_use_should_deny(
    mock_logger, mock_metrics, mock_auth_service, mocked_jwks_response, user_auth_jwt, jwt_issuer
):
    # ARRANGE
    mock_auth_service.get_signing_key_from_jwt.return_value = (True, mocked_jwks_response)

    verify_jwt = authorizer_steps.JWTAuthorizer(
        auth_srv=mock_auth_service,
        metrics=mock_metrics,
        logger=mock_logger,
        issuer=jwt_issuer,
    )

    # ACT
    auth_result = verify_jwt.invoke(
        request=authorizer.AuthorizationRequest(
            auth_token=user_auth_jwt(token_use="wwrong"),
            api_id="api-id",
            operation_id="UpdateProject",
            resource_ids={},
            resource="test",
            resource_path="/path",
        ),
        context=authorizer.AuthorizationContext(
            user_name="test-user",
            api_auth_cfg={},
        ),
    )

    # ASSERT
    assertpy.assert_that(auth_result).is_false()
    mock_logger.error.assert_called_once_with("JWT is neither ID nor Access token.")


@freeze_time("2025-05-02 09:00:00+00:00")
def test_jwt_authorizer_when_jwt_has_no_exp_claim_should_deny(
    mock_logger, mock_metrics, mock_auth_service, mocked_jwks_response, user_auth_jwt, jwt_issuer
):
    # ARRANGE
    mock_auth_service.get_signing_key_from_jwt.return_value = (True, mocked_jwks_response)

    verify_jwt = authorizer_steps.JWTAuthorizer(
        auth_srv=mock_auth_service,
        metrics=mock_metrics,
        logger=mock_logger,
        issuer=jwt_issuer,
    )

    # ACT
    auth_result = verify_jwt.invoke(
        request=authorizer.AuthorizationRequest(
            auth_token=user_auth_jwt(exp=None),
            api_id="api-id",
            operation_id="UpdateProject",
            resource_ids={},
            resource="test",
            resource_path="/path",
        ),
        context=authorizer.AuthorizationContext(
            user_name="test-user",
            api_auth_cfg={},
        ),
    )

    # ASSERT
    assertpy.assert_that(auth_result).is_false()
    mock_logger.exception.assert_called_once_with("Unexpected error while validating JWT")


@freeze_time("2025-05-02 09:00:00+00:00")
def test_jwt_authorizer_when_jwt_has_no_iss_claim_should_deny(
    mock_logger, mock_metrics, mock_auth_service, mocked_jwks_response, user_auth_jwt, jwt_issuer
):
    # ARRANGE
    mock_auth_service.get_signing_key_from_jwt.return_value = (True, mocked_jwks_response)

    verify_jwt = authorizer_steps.JWTAuthorizer(
        auth_srv=mock_auth_service,
        metrics=mock_metrics,
        logger=mock_logger,
        issuer=jwt_issuer,
    )

    # ACT
    auth_result = verify_jwt.invoke(
        request=authorizer.AuthorizationRequest(
            auth_token=user_auth_jwt(iss=None),
            api_id="api-id",
            operation_id="UpdateProject",
            resource_ids={},
            resource="test",
            resource_path="/path",
        ),
        context=authorizer.AuthorizationContext(
            user_name="test-user",
            api_auth_cfg={},
        ),
    )

    # ASSERT
    assertpy.assert_that(auth_result).is_false()
    mock_logger.exception.assert_called_once_with("Unexpected error while validating JWT")


@freeze_time("2025-05-02 09:00:00+00:00")
def test_jwt_authorizer_when_jwt_has_no_token_use_claim_should_deny(
    mock_logger, mock_metrics, mock_auth_service, mocked_jwks_response, user_auth_jwt, jwt_issuer
):
    # ARRANGE
    mock_auth_service.get_signing_key_from_jwt.return_value = (True, mocked_jwks_response)

    verify_jwt = authorizer_steps.JWTAuthorizer(
        auth_srv=mock_auth_service,
        metrics=mock_metrics,
        logger=mock_logger,
        issuer=jwt_issuer,
    )

    # ACT
    auth_result = verify_jwt.invoke(
        request=authorizer.AuthorizationRequest(
            auth_token=user_auth_jwt(token_use=None),
            api_id="api-id",
            operation_id="UpdateProject",
            resource_ids={},
            resource="test",
            resource_path="/path",
        ),
        context=authorizer.AuthorizationContext(
            user_name="test-user",
            api_auth_cfg={},
        ),
    )

    # ASSERT
    assertpy.assert_that(auth_result).is_false()
    mock_logger.exception.assert_called_once_with("Unexpected error while validating JWT")


@freeze_time("2025-05-02 09:00:00+00:00")
@pytest.mark.parametrize(
    "token_use,audiences", [("id", []), ("access", []), ("id", ["audience-id"]), ("access", ["audience-id"])]
)
def test_jwt_authorizer_when_jwt_correct_should_allow(
    mock_logger, mock_metrics, mock_auth_service, mocked_jwks_response, user_auth_jwt, jwt_issuer, token_use, audiences
):
    # ARRANGE
    mock_auth_service.get_signing_key_from_jwt.return_value = (True, mocked_jwks_response)

    verify_jwt = authorizer_steps.JWTAuthorizer(
        auth_srv=mock_auth_service,
        metrics=mock_metrics,
        logger=mock_logger,
        issuer=jwt_issuer,
        audiences=audiences,
    )

    # ACT
    auth_result = verify_jwt.invoke(
        request=authorizer.AuthorizationRequest(
            auth_token=user_auth_jwt(token_use=token_use),
            api_id="api-id",
            operation_id="UpdateProject",
            resource_ids={},
            resource="test",
            resource_path="/path",
        ),
        context=authorizer.AuthorizationContext(
            user_name="test-user",
            api_auth_cfg={},
        ),
    )

    # ASSERT
    assertpy.assert_that(auth_result).is_true()


def test_cognito_authorizer_should_sanitize_username(
    mock_logger, mock_metrics, mock_auth_service, mocked_policy_store_provider_no_policy
):
    # ARRANGE
    step = authorizer_steps.CognitoAuthorizer(
        auth_srv=mock_auth_service,
        metrics=mock_metrics,
        logger=mock_logger,
    )

    ctx = authorizer.AuthorizationContext(
        api_auth_cfg=mocked_policy_store_provider_no_policy("api-id"),
        project_scoped_bounded_contexts=[],
    )

    mock_auth_service.get_user_info.return_value = {
        "custom:user_tid": "test.user@example.nonexisting",
        "email": "test.user@example.nonexisting",
    }

    # ACT

    step.invoke(
        request=authorizer.AuthorizationRequest(
            auth_token="Bearer token",
            api_id="api-id",
            operation_id="operation",
            resource_ids={},
            resource="test",
            resource_path="/some/path",
        ),
        context=ctx,
    )

    # ASSERT
    assertpy.assert_that(ctx.user_name).is_equal_to("TEST.USER")
