import json

import boto3
from aws_lambda_powertools import Metrics, logging
from aws_lambda_powertools.utilities import parameters
from jwt import PyJWKClient
from pydantic import BaseModel, ConfigDict

from app.authorization.adapters.query_services import assignments_dynamodb_query_service
from app.authorization.adapters.services import (
    cognito_service,
    verified_permissions_service,
)
from app.authorization.domain.services.auth import authorizer, authorizer_steps
from app.authorization.entrypoints.api_gateway_authorizer_request_event_handler import (
    config,
)
from app.shared.logging import boto_logger


class Dependencies(BaseModel):
    authorizer: authorizer.Authorizer
    jwk_client: PyJWKClient
    model_config = ConfigDict(arbitrary_types_allowed=True)


def bootstrap(  # noqa: C901
    app_config: config.AppConfig,
    logger: logging.Logger,
) -> Dependencies:
    metrics_client = Metrics()
    session = boto_logger.loggable_session(boto3.session.Session(), logger)
    jwk_client = PyJWKClient(uri=app_config.get_jwks_uri(), timeout=app_config.get_jwk_timeout())

    verified_permissions_client = session.client("verifiedpermissions", region_name=app_config.get_default_region())

    cognito_srv = cognito_service.CognitoService(
        jwk_client=jwk_client,
        cognito_user_info_uri=f"{app_config.get_user_pool_url()}/oauth2/userInfo",
        logger=logger,
        metrics=metrics_client,
    )

    stage_access_cfg = json.loads(parameters.get_parameter(app_config.get_user_role_stage_access_ssm_param()))
    verified_permissions_srv = verified_permissions_service.VerifiedPermissionsService(
        verified_permissions_client=verified_permissions_client,
    )

    dynamodb = session.resource("dynamodb", region_name=app_config.get_default_region())

    assignments_qs = assignments_dynamodb_query_service.AssignmentsDynamoDBQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_inverted_pk=app_config.get_gsi_name_inverted_pk(),
    )

    api_policy_stores: dict[str, authorizer.APIAuthConfig] = {}

    def __reload_config_params():
        api_policy_stores_params = parameters.get_parameters(
            path=app_config.get_policy_store_ssm_param_prefix(), force_fetch=True
        )
        for _, val in api_policy_stores_params.items():
            api_cfg_item = authorizer.APIAuthConfig.model_validate_json(val)
            api_policy_stores[api_cfg_item.api_id] = api_cfg_item

    __reload_config_params()

    def __api_config_provider(api_id: str) -> authorizer.APIAuthConfig | None:
        if api_id not in api_policy_stores:
            __reload_config_params()
        return api_policy_stores.get(api_id, None)

    return Dependencies(
        authorizer=authorizer.Authorizer(
            api_config_provider=__api_config_provider,
            logger=logger,
            metrics=metrics_client,
            authorization_steps=[
                authorizer_steps.JWTAuthorizer(
                    auth_srv=cognito_srv,
                    logger=logger,
                    metrics=metrics_client,
                    issuer=f"https://cognito-idp.{app_config.get_user_pool_region()}.amazonaws.com/{app_config.get_user_pool_id()}",
                    audiences=app_config.get_user_pool_client_ids(),
                ),
                authorizer_steps.CognitoAuthorizer(auth_srv=cognito_srv, logger=logger, metrics=metrics_client),
                authorizer_steps.ProjectsBCContextEnricher(
                    assignments_query_service=assignments_qs,
                ),
                authorizer_steps.AmazonVerifiedPermissionsAuthorizer(
                    authz_service=verified_permissions_srv,
                    logger=logger,
                    entity_resolvers=[
                        authorizer_steps.VEWProjectAssignmentEntityResolver(),
                    ],
                ),
            ],
            stage_access_config=stage_access_cfg,
        ),
        jwk_client=jwk_client,
    )
