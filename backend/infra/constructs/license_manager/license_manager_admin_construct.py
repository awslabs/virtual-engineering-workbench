import constructs
from aws_cdk import custom_resources

from infra import config


class LicenseManagerAdminConstruct(constructs.Construct):
    def __init__(self, scope: constructs.Construct, id: str, app_config: config.AppConfig, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        custom_resources.AwsCustomResource(
            self,
            "LicenseManagerSLR",
            on_create=custom_resources.AwsSdkCall(
                service="IAM",
                action="createServiceLinkedRole",
                parameters={"AWSServiceName": "license-manager.amazonaws.com"},
                physical_resource_id=custom_resources.PhysicalResourceId.of("license-manager-slr"),
                ignore_error_codes_matching="InvalidInput",
            ),
            policy=custom_resources.AwsCustomResourcePolicy.from_sdk_calls(resources=["*"]),
        )
