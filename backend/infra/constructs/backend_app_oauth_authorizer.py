import constructs
from aws_cdk import aws_apigateway, aws_cognito


class BackendAppOauth2Authorizer(constructs.Construct):
    def __init__(self, scope: constructs.Construct, id: str, user_pool_id: str) -> None:
        super().__init__(scope, id)

        # import user pool
        pool = aws_cognito.UserPool.from_user_pool_id(self, "BackendAppUserPool", user_pool_id)

        # create cognito user pool authorizer
        self._auth = aws_apigateway.CognitoUserPoolsAuthorizer(self, "OauthAuthorizer", cognito_user_pools=[pool])

    @property
    def authorizer(self) -> aws_apigateway.CognitoUserPoolsAuthorizer:
        return self._auth
