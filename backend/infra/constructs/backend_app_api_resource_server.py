from dataclasses import dataclass

import constructs
from aws_cdk import aws_cognito


@dataclass
class ResourceServer:
    identifier: str
    scopes: dict[str, str]


class BackendAppApiResourceServer(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        user_pool: aws_cognito.IUserPool,
        resource_server: ResourceServer,
    ) -> None:
        super().__init__(scope, id)

        self.__scopes: list[aws_cognito.ResourceServerScope] = []

        for scope_name, scope_description in resource_server.scopes.items():
            self.__scopes.append(
                aws_cognito.ResourceServerScope(scope_name=scope_name, scope_description=scope_description)
            )

        self.__resource_server = user_pool.add_resource_server(
            id=f"BackendAppResourceServer{resource_server.identifier.replace("/", "")}",
            identifier=resource_server.identifier,
            scopes=self.__scopes,
            user_pool_resource_server_name=resource_server.identifier.replace("/", "."),
        )

    @property
    def scopes(self) -> list[aws_cognito.ResourceServerScope]:
        return self.__scopes

    @property
    def resource_server(self) -> aws_cognito.UserPoolResourceServer:
        return self.__resource_server
