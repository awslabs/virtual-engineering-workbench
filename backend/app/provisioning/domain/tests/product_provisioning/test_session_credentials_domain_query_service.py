from unittest import mock

import assertpy
import pytest

from app.provisioning.domain.exceptions.domain_exception import DomainException
from app.provisioning.domain.model import session_credentials
from app.provisioning.domain.ports import provisioned_products_query_service, session_credentials_service
from app.provisioning.domain.query_services import session_credentials_domain_query_service
from app.provisioning.domain.value_objects import (
    project_id_value_object,
    provisioned_product_id_value_object,
    user_id_value_object,
)
from app.shared.adapters.feature_toggling import frontend_feature, frontend_feature_toggles

CREDENTIALS = session_credentials.SessionCredentials(
    accessKeyId="AKIA",
    secretAccessKey="secret",
    sessionToken="token",
    instanceId="i-01234567890abcdef",
    region="us-east-1",
)


@pytest.fixture()
def session_credentials_srv_mock():
    srv = mock.create_autospec(spec=session_credentials_service.SessionCredentialsService)
    srv.get_session_credentials.return_value = CREDENTIALS
    return srv


@pytest.fixture()
def make_query_service(get_provisioned_product, session_credentials_srv_mock):
    def _make(enabled_features=("SessionManagerConnectionOption",), instance_id="i-01234567890abcdef", exists=True):
        provisioned_products_qry_srv = mock.create_autospec(
            spec=provisioned_products_query_service.ProvisionedProductsQueryService
        )
        provisioned_products_qry_srv.get_provisioned_product.return_value = (
            get_provisioned_product(instance_id=instance_id) if exists else None
        )
        feature_toggles = mock.create_autospec(spec=frontend_feature_toggles.FrontendFeatureToggles)
        feature_toggles.get_enabled_features_for_user.return_value = [
            frontend_feature.FrontendFeature(version="1.0.0", feature=feature, enabled=True)
            for feature in enabled_features
        ]
        return session_credentials_domain_query_service.SessionCredentialsDomainQueryService(
            provisioned_products_qry_srv=provisioned_products_qry_srv,
            session_credentials_srv=session_credentials_srv_mock,
            feature_toggles=feature_toggles,
        )

    return _make


def _get_session_credentials(query_service, user_id="T0011AA"):
    return query_service.get_session_credentials(
        project_id=project_id_value_object.from_str("proj-123"),
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_id=user_id_value_object.from_str(user_id),
    )


def test_get_session_credentials_returns_credentials_for_the_owners_instance(
    make_query_service, session_credentials_srv_mock
):
    # ACT
    credentials = _get_session_credentials(make_query_service())

    # ASSERT
    assertpy.assert_that(credentials).is_equal_to(CREDENTIALS)
    session_credentials_srv_mock.get_session_credentials.assert_called_once_with(
        aws_account_id="001234567890",
        region="us-east-1",
        user_id="T0011AA",
        instance_id="i-01234567890abcdef",
    )


@pytest.mark.parametrize(
    "service_kwargs,user_id,error",
    [
        ({"enabled_features": ()}, "T0011AA", "Session Manager is not enabled."),
        ({"exists": False}, "T0011AA", "Provisioned product does not exist"),
        ({}, "T0022BB", "You do not have permissions to fetch session credentials for the provisioned product"),
        ({"instance_id": None}, "T0011AA", "Provisioned product does not have an instance to connect to."),
    ],
)
def test_get_session_credentials_refuses_without_minting(
    make_query_service, session_credentials_srv_mock, service_kwargs, user_id, error
):
    # ACT
    with pytest.raises(DomainException) as e:
        _get_session_credentials(make_query_service(**service_kwargs), user_id=user_id)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(error)
    session_credentials_srv_mock.get_session_credentials.assert_not_called()


def test_get_session_credentials_raises_while_the_ssm_agent_is_not_connected(
    make_query_service, session_credentials_srv_mock
):
    # ARRANGE
    session_credentials_srv_mock.get_session_credentials.return_value = None

    # ACT
    with pytest.raises(DomainException) as e:
        _get_session_credentials(make_query_service())

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        "Session Manager cannot reach the provisioned product: its SSM Agent is not connected."
    )
