from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import session_credentials
from app.provisioning.domain.ports import provisioned_products_query_service, session_credentials_service
from app.provisioning.domain.value_objects import (
    project_id_value_object,
    provisioned_product_id_value_object,
    user_id_value_object,
)
from app.shared.adapters.feature_toggling import frontend_feature_toggles

SESSION_MANAGER_FEATURE = "SessionManagerConnectionOption"


class SessionCredentialsDomainQueryService:
    def __init__(
        self,
        provisioned_products_qry_srv: provisioned_products_query_service.ProvisionedProductsQueryService,
        session_credentials_srv: session_credentials_service.SessionCredentialsService,
        feature_toggles: frontend_feature_toggles.FrontendFeatureToggles,
    ) -> None:
        self._provisioned_products_qry_srv = provisioned_products_qry_srv
        self._session_credentials_srv = session_credentials_srv
        self._feature_toggles = feature_toggles

    def get_session_credentials(
        self,
        project_id: project_id_value_object.ProjectIdValueObject,
        provisioned_product_id: provisioned_product_id_value_object.ProvisionedProductIdValueObject,
        user_id: user_id_value_object.UserIdValueObject,
    ) -> session_credentials.SessionCredentials:
        enabled_features = self._feature_toggles.get_enabled_features_for_user(user_id=user_id.value)
        if not any(f.feature == SESSION_MANAGER_FEATURE for f in enabled_features):
            raise domain_exception.DomainException("Session Manager is not enabled.")

        pp = self._provisioned_products_qry_srv.get_provisioned_product(
            project_id=project_id.value,
            provisioned_product_id=provisioned_product_id.value,
        )

        if not pp:
            raise domain_exception.DomainException("Provisioned product does not exist")

        if pp.userId != user_id.value:
            raise domain_exception.DomainException(
                "You do not have permissions to fetch session credentials for the provisioned product"
            )

        if not pp.instanceId:
            raise domain_exception.DomainException("Provisioned product does not have an instance to connect to.")

        credentials = self._session_credentials_srv.get_session_credentials(
            aws_account_id=pp.awsAccountId,
            region=pp.region,
            user_id=user_id.value,
            instance_id=pp.instanceId,
        )

        if not credentials:
            raise domain_exception.DomainException(
                "Session Manager cannot reach the provisioned product: its SSM Agent is not connected."
            )

        return credentials
