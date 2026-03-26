import enum
import json
import typing
from abc import ABC, abstractmethod

from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from pydantic import BaseModel, Field

from app.authorization.domain.read_models import project_assignment


class AuthFeature(enum.StrEnum):
    # Checks for a user role in a project assignment
    ProjectAssignments = "ProjectAssignments"


class APIAuthConfig(BaseModel):
    api_id: str = Field(None)
    api_url: str | None = Field(None)
    policy_store_id: str | None = Field(None)
    bounded_context: str | None = Field(None)
    auth_features: list[AuthFeature] = Field([])


class AuthorizationContext(BaseModel):
    user_name: str | None = Field(None)
    user_email: str | None = Field(None)
    stages: list[str] | None = Field(None)
    roles: list[str] | None = Field(None)
    domains: list[str] | None = Field(None)
    project_assignments: list[project_assignment.Assignment] = Field([])
    api_auth_cfg: APIAuthConfig = Field(...)
    project_scoped_bounded_contexts: list[str] = Field([])


class AuthorizationRequest(BaseModel):
    auth_token: str = Field(...)
    api_id: str = Field(...)
    operation_id: str = Field(...)
    resource_ids: dict[str, str] = Field(...)
    resource_path: str = Field(...)
    resource: str = Field(...)


class AuthorizerStep(ABC):

    @abstractmethod
    def invoke(self, request: AuthorizationRequest, context: AuthorizationContext) -> bool: ...


class AuthorizationDecision(enum.StrEnum):
    ALLOW = "Allow"
    DENY = "Deny"


class Authorizer:

    def __init__(
        self,
        logger: Logger,
        metrics: Metrics,
        api_config_provider: typing.Callable[[str], APIAuthConfig],
        project_scoped_bounded_contexts: list[str] = [],
        authorization_steps: list[AuthorizerStep] = [],
        stage_access_config: dict = {},
    ):
        self.__authorization_steps = authorization_steps
        self.__stage_access_config = stage_access_config
        self.__logger = logger
        self.__metrics = metrics
        self.__api_config_provider = api_config_provider
        self.__project_scoped_bounded_contexts = project_scoped_bounded_contexts

    def authorize(self, auth_req: AuthorizationRequest):

        if not (api_auth_cfg := self.__api_config_provider(auth_req.api_id)):
            return self.__generate_iam_policy(principalId="me", effect=AuthorizationDecision.DENY, resource="*")

        auth_context = AuthorizationContext(
            api_auth_cfg=api_auth_cfg,
            project_scoped_bounded_contexts=self.__project_scoped_bounded_contexts,
        )

        for authorization_step in self.__authorization_steps:
            try:
                if not authorization_step.invoke(request=auth_req, context=auth_context):
                    return self.__generate_iam_policy(principalId="me", effect=AuthorizationDecision.DENY, resource="*")
            except Exception:
                self.__logger.exception("Authorization step failed")
                return self.__generate_iam_policy(principalId="me", effect=AuthorizationDecision.DENY, resource="*")

        if not auth_context.user_name:
            return self.__generate_iam_policy(principalId="me", effect=AuthorizationDecision.DENY, resource="*")

        stages = set()
        if auth_context.roles and self.__stage_access_config:
            stages = {
                stage
                for role in auth_context.roles
                if role in self.__stage_access_config
                for stage in self.__stage_access_config[role]
            }

        return self.__generate_iam_policy(
            principalId=auth_context.user_name.upper(),
            effect=AuthorizationDecision.ALLOW,
            resource=auth_req.resource,
            context={
                "userName": auth_context.user_name.upper(),
                "userEmail": auth_context.user_email,
                "stages": json.dumps(sorted(list(stages))),
                "userRoles": json.dumps(sorted(auth_context.roles or [])),
                "userDomains": json.dumps(sorted(auth_context.domains or [])),
            },
        )

    def __generate_iam_policy(
        self, principalId: str, effect: AuthorizationDecision, resource: str, context: dict[str, str] | None = None
    ) -> dict:
        authResponse = {}
        authResponse["principalId"] = principalId
        if effect and resource:
            policyDocument = {}
            policyDocument["Version"] = "2012-10-17"  # default version
            policyDocument["Statement"] = []
            statementOne = {}
            statementOne["Action"] = "execute-api:Invoke"  # default action
            statementOne["Effect"] = effect
            statementOne["Resource"] = resource
            policyDocument["Statement"].append(statementOne)
            authResponse["policyDocument"] = policyDocument

        if context:
            authResponse["context"] = context

        self.__logger.debug(authResponse)
        self.__metrics.add_metric(
            name="UserAuthorized" if effect == AuthorizationDecision.ALLOW else "UserUnauthorized",
            unit=MetricUnit.Count,
            value=1,
        )
        return authResponse
