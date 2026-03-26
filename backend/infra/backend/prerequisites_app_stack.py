import aws_cdk
import constructs
from aws_cdk import aws_ec2

from infra import config
from infra.constructs import private_api_gw_endpoint


class PrerequisitesAppStack(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        api_gw_endpoint = private_api_gw_endpoint.PrivateApiGwEndpoint(
            self,
            "PrivateApiGwEndpoint",
            app_config=app_config,
        )
        self._vpc_endpoint = api_gw_endpoint.vpc_endpoint
        self._vpc_endpoint_ips = api_gw_endpoint.vpc_endpoint_ips

    @property
    def vpc_endpoint(self) -> aws_ec2.VpcEndpoint:
        return self._vpc_endpoint

    @property
    def vpc_endpoint_ips(self) -> aws_ec2.VpcEndpoint:
        return self._vpc_endpoint_ips
