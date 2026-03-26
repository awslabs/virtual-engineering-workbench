import json
from enum import StrEnum
from typing import Optional, Set

from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response
from aws_lambda_powertools.event_handler.middlewares import NextMiddleware
from aws_lambda_powertools.utilities.parser import BaseModel, Field
from aws_lambda_powertools.utilities.parser.models import APIGatewayProxyEventModel


class VirtualWorkbenchRoles(StrEnum):
    Admin = "ADMIN"
    PowerUser = "POWER_USER"
    ProgramOwner = "PROGRAM_OWNER"
    PlatformUser = "PLATFORM_USER"
    BetaUser = "BETA_USER"
    ProductContributor = "PRODUCT_CONTRIBUTOR"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, VirtualWorkbenchRoles))


class AuthType(StrEnum):
    CognitoUserJWT = "CognitoUserJWT"
    CognitoServiceJWT = "CognitoServiceJWT"
    ServiceIAM = "ServiceIAM"


class Principal(BaseModel):
    """
    Contains details about logged in user.
    """

    user_name: str = Field(alias="userName")
    auth_type: AuthType = Field(alias="authType")
    user_email: Optional[str] = Field(alias="userEmail")
    user_groups: Optional[Set[str]] = Field(alias="userGroups")
    stages: Optional[set[str]] = Field(alias="stages")
    user_roles: Optional[list[VirtualWorkbenchRoles]] = Field(alias="userRoles")
    user_domains: Optional[list[str]] = Field(alias="userDomains")
    account_id: Optional[str] = Field(alias="accountId")


class APIGatewayProxyEventWithPrincipal(APIGatewayProxyEventModel):
    """
    Extends API Gateway proxy payload with user principal object.
    """

    user_principal: Optional[Principal] = Field(alias="userPrincipal")


class AuthException(Exception):
    pass


def require_auth_context(app: APIGatewayRestResolver, next_middleware: NextMiddleware) -> Response:

    principal: Principal | None = None

    if authorizer_auth_context := app.current_event.get("requestContext", {}).get("authorizer", None):
        # user request
        if "userName" in authorizer_auth_context:
            principal = Principal(
                authType=AuthType.CognitoUserJWT,
                userName=authorizer_auth_context["userName"],
                userEmail=authorizer_auth_context["userEmail"],
                stages=set(json.loads(authorizer_auth_context["stages"])),
                userRoles=list(json.loads(authorizer_auth_context["userRoles"])),
                userDomains=list(json.loads(authorizer_auth_context["userDomains"])),
            )
        # service to service OAuth API request
        elif "claims" in authorizer_auth_context:
            principal = Principal(
                authType=AuthType.CognitoServiceJWT,
                userName=authorizer_auth_context.get("claims").get("client_id"),
            )
    elif identity := app.current_event.get("requestContext", {}).get("identity", None):

        if not (identity_user := identity.get("user")) or ":" not in identity_user:
            raise AuthException()

        user_name = identity_user.split(":")[-1].upper()

        principal = Principal(
            authType=AuthType.ServiceIAM,
            userName=user_name,
            accountId=identity.get("accountId"),
        )

    if not principal:
        raise AuthException()

    app.append_context(user_principal=principal)

    return next_middleware(app)
