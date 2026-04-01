import enum
import typing
from abc import ABC, abstractmethod

import jwt
import pydantic
from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from pydantic import ConfigDict

from app.authorization.domain.ports import (
    assignments_query_service,
    authentication_service,
    authorization_service,
)
from app.authorization.domain.read_models import project_assignment
from app.authorization.domain.services.auth import authorizer

USER_ID_CLAIM_NAME = "custom:user_tid"


class JWTAuthorizer(authorizer.AuthorizerStep):

    def __init__(
        self,
        auth_srv: authentication_service.AuthenticationService,
        logger: Logger,
        metrics: Metrics,
        issuer: str,
        audiences: list[str] = [],
    ):
        self.__auth_srv = auth_srv
        self.__logger = logger
        self.__metrics = metrics
        self.__issuer = issuer
        self.__audiences = audiences

    def invoke(self, request: authorizer.AuthorizationRequest, context: authorizer.AuthorizationContext) -> bool:

        auth_token_jwt, signing_key = self.__get_auth_token_with_signing_key(request)

        if not auth_token_jwt or not signing_key:
            return False

        try:
            token = jwt.decode(
                auth_token_jwt,
                signing_key.key,
                algorithms=["RS256"],
                options={
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": False,
                    "require": ["exp", "iss", "token_use"],
                },
                issuer=self.__issuer,
            )

            self.__logger.debug(
                {
                    "message": "JWT token decoded successfully",
                    "jwt_kid": signing_key.key_id,
                }
            )

            self.__validate_audience(token)
            self.__validate_token_use(token)

            return True

        except jwt.exceptions.InvalidSignatureError:
            self.__logger.exception("The JWT token has an invalid signature")
            self.__metrics.add_metric(name="CognitoInvalidToken", unit=MetricUnit.Count, value=1)
        except jwt.exceptions.ExpiredSignatureError:
            self.__logger.exception("The JWT token has expired")
            self.__metrics.add_metric(name="CognitoInvalidToken", unit=MetricUnit.Count, value=1)
        except jwt.exceptions.DecodeError:
            self.__logger.exception("The JWT token could not be decoded")
            self.__metrics.add_metric(name="TokenDecodeError", unit=MetricUnit.Count, value=1)
        except Exception:
            self.__logger.exception("Unexpected error while validating JWT")
            self.__metrics.add_metric(name="UnexpectedUserProfileError", unit=MetricUnit.Count, value=1)

        return False

    def __validate_audience(self, token: dict):
        if self.__audiences:
            token_client_id = token.get("aud") or token.get("client_id")
            if token_client_id not in self.__audiences:
                self.__logger.error("The JWT token has an invalid audience")
                raise jwt.exceptions.InvalidAudienceError("Invalid client ID")

    def __validate_token_use(self, token: dict):
        if token.get("token_use") not in ["id", "access"]:
            self.__logger.error("JWT is neither ID nor Access token.")
            raise jwt.exceptions.InvalidTokenError("JWT is neither ID nor Access token.")

    def __get_auth_token_with_signing_key(
        self, request: authorizer.AuthorizationRequest
    ) -> tuple[str | None, jwt.PyJWK | None]:
        if not request.auth_token.startswith("Bearer "):
            return (None, None)

        auth_token_jwt = request.auth_token.split("Bearer ")[1]
        success, signing_key = self.__auth_srv.get_signing_key_from_jwt(auth_token_jwt)
        if not success or not signing_key:
            return (None, None)

        return (auth_token_jwt, signing_key)


class CognitoAuthorizer(authorizer.AuthorizerStep):

    def __init__(
        self,
        auth_srv: authentication_service.AuthenticationService,
        logger: Logger,
        metrics: Metrics,
    ):
        self.__auth_srv = auth_srv
        self.__logger = logger
        self.__metrics = metrics

    def invoke(self, request: authorizer.AuthorizationRequest, context: authorizer.AuthorizationContext) -> bool:

        if not request.auth_token.startswith("Bearer "):
            return False

        if user_profile := self.__auth_srv.get_user_info(request.auth_token):
            self.__logger.debug(
                {
                    "message": "User profile retrieved",
                    "response": user_profile,
                }
            )
            context.user_name = (
                self.__sanitize_user_name(user_profile[USER_ID_CLAIM_NAME])
                if USER_ID_CLAIM_NAME in user_profile
                else None
            )
            context.user_email = user_profile["email"]
            return True

        self.__logger.debug(
            {
                "message": "User Profile could not be retrieved",
            }
        )
        self.__metrics.add_metric(name="UserInvalid", unit=MetricUnit.Count, value=1)
        return False

    def __sanitize_user_name(self, user_name: str) -> str:
        username = user_name.split("@")[0] if "@" in user_name else user_name
        return username.upper()


class ProjectsBCContextEnricher(authorizer.AuthorizerStep):

    def __init__(
        self,
        assignments_query_service: assignments_query_service.AssignmentsQueryService,
    ):
        self.__assignments_query_service = assignments_query_service

    def invoke(self, request: authorizer.AuthorizationRequest, context: authorizer.AuthorizationContext) -> bool:

        if not context.user_name:
            return False

        if (
            context.api_auth_cfg.bounded_context not in context.project_scoped_bounded_contexts
            and authorizer.AuthFeature.ProjectAssignments not in context.api_auth_cfg.auth_features
        ):
            return True

        context.roles = []
        context.domains = []

        project_assignment = None

        context.project_assignments = self.__assignments_query_service.get_user_assignments(user_id=context.user_name)

        if request.resource_path.startswith("/projects/") and (
            project_id := request.resource_ids.get("projectId", None)
        ):
            project_assignment = next(
                (assignment for assignment in context.project_assignments if assignment.projectId == project_id),
                None,
            )

            context.roles = project_assignment.roles if project_assignment and project_assignment.roles else []
            context.domains = (
                list({g.get("domain") for g in project_assignment.activeDirectoryGroups if "domain" in g})
                if project_assignment and project_assignment.activeDirectoryGroups
                else []
            )

        return True


class AVPEntityType(enum.StrEnum):
    PROJECT = "VEW::Project"
    PROJECT_ASSIGNMENT = "VEW::ProjectAssignment"
    USER = "VEW::User"


class AVPEntityIdentifier(pydantic.BaseModel):
    entity_id: str = pydantic.Field(alias="entityId")
    entity_type: str = pydantic.Field(alias="entityType")
    model_config = ConfigDict(populate_by_name=True)


class AVPEntity(pydantic.BaseModel):
    identifier: AVPEntityIdentifier = pydantic.Field(..., alias="identifier")
    attributes: dict = pydantic.Field({}, alias="attributes")
    parents: list[AVPEntityIdentifier] = pydantic.Field([], alias="parents")


class AVPEntityResolutionContext(pydantic.BaseModel):
    resource: AVPEntityIdentifier | None = pydantic.Field(None)
    entities: list[AVPEntity] = pydantic.Field([], alias="entities")


class AVPEntityResolver(ABC):

    @abstractmethod
    def resolve(
        self,
        request: authorizer.AuthorizationRequest,
        context: authorizer.AuthorizationContext,
        avp_entities: AVPEntityResolutionContext,
    ): ...


class VEWProjectAssignmentEntityResolver(AVPEntityResolver):
    def resolve(
        self,
        request: authorizer.AuthorizationRequest,
        context: authorizer.AuthorizationContext,
        avp_entities: AVPEntityResolutionContext,
    ):
        if (
            context.api_auth_cfg.bounded_context not in context.project_scoped_bounded_contexts
            and authorizer.AuthFeature.ProjectAssignments not in context.api_auth_cfg.auth_features
        ):
            return

        if request.resource_path.startswith("/projects/") and (
            project_id := request.resource_ids.get("projectId", None)
        ):
            avp_entities.resource = AVPEntityIdentifier(
                entity_id=project_id,
                entity_type=AVPEntityType.PROJECT,
            )
            avp_entities.entities.append(self.__generate_project_entity(project_id=project_id))
            avp_entities.entities.extend(self.__generate_project_assignment_inheritace_scheme(project_id=project_id))
            avp_entities.entities.extend(
                self.__generate_project_assignment_group_based_inheritace_scheme(project_id=project_id)
            )

        if not context.user_name:
            return

        user_entity = next(
            (
                e
                for e in avp_entities.entities
                if e.identifier.entity_type == AVPEntityType.USER and e.identifier.entity_id == context.user_name
            ),
            AVPEntity(
                identifier=AVPEntityIdentifier(
                    entityId=context.user_name,
                    entityType=AVPEntityType.USER,
                ),
            ),
        )

        user_parents = [
            AVPEntityIdentifier(
                entityId=self.__generate_assignment_id(assignment.projectId, role),
                entityType=AVPEntityType.PROJECT_ASSIGNMENT,
            )
            for assignment in context.project_assignments
            for role in assignment.roles
        ]

        user_parents_group = [
            AVPEntityIdentifier(
                entityId=self.__generate_group_assignment_id(assignment.projectId, group),
                entityType=AVPEntityType.PROJECT_ASSIGNMENT,
            )
            for assignment in context.project_assignments
            for group in assignment.groupMemberships
        ]

        total_admin_assignments = len(
            [a for a in (context.project_assignments or []) if project_assignment.Role.ADMIN in a.roles]
        )

        if not user_entity.parents:
            user_entity.parents = user_parents + user_parents_group
        else:
            user_entity.parents.extend(user_parents)
            user_entity.parents.extend(user_parents_group)

        user_entity.attributes["totalAdminAssignments"] = {"long": total_admin_assignments}

    def __generate_project_entity(self, project_id: str) -> dict:

        role_based_attributes = {
            groupName: {"entityIdentifier": identifier}
            for groupName, identifier in self.__generate_assignment_entity_set(project_id=project_id)
        }

        group_based_attributed = {
            groupName: {"entityIdentifier": identifier}
            for groupName, identifier in self.__generate_group_based_assignment_entity_set(project_id=project_id)
        }

        combined_attributes = {**role_based_attributes, **group_based_attributed}

        return AVPEntity(
            identifier=AVPEntityIdentifier(
                entityId=project_id,
                entityType=AVPEntityType.PROJECT,
            ),
            attributes=combined_attributes,
        )

    def __generate_project_assignment_inheritace_scheme(self, project_id: str):
        assignmentIds = self.__generate_assignment_entity_set(project_id=project_id)

        return [
            AVPEntity(
                identifier=assignmentId, parents=[assignmentIds[idx + 1][1]] if idx + 1 < len(assignmentIds) else []
            )
            for idx, (_, assignmentId) in enumerate(assignmentIds)
        ]

    def __generate_project_assignment_group_based_inheritace_scheme(self, project_id: str):
        assignmentIds = self.__generate_group_based_assignment_entity_set(project_id=project_id)

        return [AVPEntity(identifier=assignmentId, parents=[]) for _, (_, assignmentId) in enumerate(assignmentIds)]

    def __generate_assignment_id(self, project_id: str, role: str):
        return f"{project_id}#{role}"

    def __generate_assignment_entity_set(self, project_id: str) -> typing.Iterable[AVPEntityIdentifier]:

        return [
            (
                projectGroupName,
                AVPEntityIdentifier(
                    entityType=AVPEntityType.PROJECT_ASSIGNMENT,
                    entityId=self.__generate_assignment_id(project_id, role),
                ),
            )
            for projectGroupName, role in [
                ("admins", "ADMIN"),
                ("programOwners", "PROGRAM_OWNER"),
                ("powerUsers", "POWER_USER"),
                ("productContributors", "PRODUCT_CONTRIBUTOR"),
                ("betaUsers", "BETA_USER"),
                ("platformUsers", "PLATFORM_USER"),
            ]
        ]

    def __generate_group_assignment_id(self, project_id: str, group: str):
        return f"{project_id}#GROUP#{group}"

    def __generate_group_based_assignment_entity_set(self, project_id: str) -> typing.Iterable[AVPEntityIdentifier]:

        return [
            (
                projectGroupName,
                AVPEntityIdentifier(
                    entityType=AVPEntityType.PROJECT_ASSIGNMENT,
                    entityId=self.__generate_group_assignment_id(project_id, group),
                ),
            )
            for projectGroupName, group in [
                ("vewUsers", "VEW_USERS"),
                ("hilUsers", "HIL_USERS"),
                ("vvplUsers", "VVPL_USERS"),
            ]
        ]


class AmazonVerifiedPermissionsAuthorizer(authorizer.AuthorizerStep):

    def __init__(
        self,
        authz_service: authorization_service.AuthorizationService,
        logger: Logger,
        entity_resolvers: list[AVPEntityResolver] = [],
    ):
        self.__authz_service = authz_service
        self.__logger = logger
        self.__entity_resolvers = entity_resolvers

    def invoke(self, request: authorizer.AuthorizationRequest, context: authorizer.AuthorizationContext) -> bool:
        if not context.user_name:
            return False

        if context.api_auth_cfg.policy_store_id is None:
            return False

        principal = AVPEntityIdentifier(entityType=AVPEntityType.USER, entityId=context.user_name)

        action = {
            "actionId": request.operation_id,
            "actionType": "VEW::Action",
        }

        entity_ctx = AVPEntityResolutionContext(
            entities=[AVPEntity(identifier=principal.model_copy())],
        )

        for entity_resolver in self.__entity_resolvers:
            entity_resolver.resolve(request=request, context=context, avp_entities=entity_ctx)

        try:
            if self.__authz_service.is_action_allowed(
                policy_store_id=context.api_auth_cfg.policy_store_id,
                principal=principal.model_dump(exclude_none=True, by_alias=True),
                action=action,
                resource=(
                    entity_ctx.resource.model_dump(exclude_none=True, by_alias=True) if entity_ctx.resource else None
                ),
                entities={"entityList": [e.model_dump(exclude_none=True, by_alias=True) for e in entity_ctx.entities]},
            ):
                return True

        except Exception:
            self.__logger.exception("Error invoking Amazon Verified Permissions")

        return False
