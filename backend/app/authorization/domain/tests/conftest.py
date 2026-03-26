from datetime import datetime
from unittest import mock

import jwt
import pytest
from aws_lambda_powertools import Logger, Metrics
from cryptography.hazmat.primitives.asymmetric import rsa

from app.authorization.domain.ports import (
    authentication_service,
    authorization_service,
    projects_query_service,
)
from app.authorization.domain.read_models import project_assignment
from app.authorization.domain.services.auth import authorizer


@pytest.fixture
def mock_auth_step():
    return mock.Mock(spec=authorizer.AuthorizerStep)


@pytest.fixture
def mock_auth_service():
    return mock.Mock(spec=authentication_service.AuthenticationService)


@pytest.fixture
def mock_authz_service():
    m = mock.Mock(spec=authorization_service.AuthorizationService)
    m.is_action_allowed.return_value = True
    return m


@pytest.fixture
def mock_logger():
    return mock.Mock(spec=Logger)


@pytest.fixture
def mock_metrics():
    return mock.Mock(spec=Metrics)


@pytest.fixture
def mock_project_qry_service(mock_assignment):
    m = mock.Mock(spec=projects_query_service.ProjectsQueryService)
    m.get_user_assignments.return_value = [mock_assignment]
    return m


@pytest.fixture
def valid_bearer_token():
    return "Bearer valid.jwt.token"


@pytest.fixture
def invalid_bearer_token():
    return "Bearer invalid.jwt.token"


@pytest.fixture
def invalid_token_format():
    return "InvalidTokenFormat"


@pytest.fixture
def mock_user_info():
    return {"sub": "user123", "email": "user@example.com"}


@pytest.fixture
def sample_user():
    return "user123"


@pytest.fixture
def sample_project_id():
    return "project456"


@pytest.fixture
def mock_assignment():
    return project_assignment.Assignment(
        userId="user-id",
        projectId="project456",
        roles=["PLATFORM_USER"],
        activeDirectoryGroups=[{"domain": "domain1"}, {"domain": "domain2"}],
        userEmail="test@example.com",
        groupMemberships=["VEW_USERS"],
    )


@pytest.fixture
def mocked_policy_store_provider():
    def __inner(api_id: str = "rest-api-id"):
        return authorizer.APIAuthConfig.parse_obj(
            {
                "api_id": api_id,
                "policy_store_id": "policy-store-id",
                "bounded_context": "projects",
                "api_url": "",
            }
        )

    return __inner


@pytest.fixture
def mocked_policy_store_provider_project_assignment_feature():
    def __inner(api_id: str = "rest-api-id"):
        return authorizer.APIAuthConfig.parse_obj(
            {
                "api_id": api_id,
                "policy_store_id": "policy-store-id",
                "bounded_context": "projects",
                "api_url": "",
                "auth_features": [authorizer.AuthFeature.ProjectAssignments],
            }
        )

    return __inner


@pytest.fixture
def mocked_policy_store_provider_no_policy():
    def __inner(api_id):
        return authorizer.APIAuthConfig.parse_obj(
            {
                "api_id": api_id,
                "bounded_context": "projects",
                "api_url": "",
            }
        )

    return __inner


@pytest.fixture
def jwt_test_private_key():
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


@pytest.fixture
def jwt_test_private_key_wrong():
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


@pytest.fixture
def jwt_test_public_key(jwt_test_private_key):
    return jwt_test_private_key.public_key()


@pytest.fixture
def jwt_correct_kid():
    return "230498151c214b788dd97f22b85410a5"


@pytest.fixture
def jwt_issuer():
    return "https://cognito-idp.us-east-1.amazonaws.com/user_pool_id"


@pytest.fixture
def user_auth_jwt(jwt_test_private_key, jwt_correct_kid):
    def __inner(
        token_use: str = "access",
        exp: datetime = datetime.fromisoformat("2025-05-02 10:00:00+00:00"),
        iss: str = "https://cognito-idp.us-east-1.amazonaws.com/user_pool_id",
        aud: str = "audience-id",
    ):
        payload = {
            **({"exp": exp.timestamp()} if exp else {}),
            **({"iss": iss} if iss else {}),
            **({"token_use": token_use} if token_use else {}),
            **({"aud": aud} if aud else {}),
        }
        headers = {"kid": jwt_correct_kid}
        return "Bearer " + jwt.encode(payload, jwt_test_private_key, algorithm="RS256", headers=headers)

    return __inner


@pytest.fixture
def user_auth_jwt_wrong(jwt_test_private_key_wrong, jwt_correct_kid):
    payload = {}
    headers = {"kid": jwt_correct_kid}
    return "Bearer " + jwt.encode(payload, jwt_test_private_key_wrong, algorithm="RS256", headers=headers)


@pytest.fixture
def mocked_jwks_response(jwt_test_public_key, jwt_correct_kid):
    alg = jwt.algorithms.RSAAlgorithm(jwt.algorithms.RSAAlgorithm.SHA256)
    pub_key = alg.prepare_key(jwt_test_public_key)
    jwk = alg.to_jwk(pub_key, True)
    return jwt.api_jwk.PyJWK(
        jwk_data={**jwk, "kid": jwt_correct_kid},
    )
