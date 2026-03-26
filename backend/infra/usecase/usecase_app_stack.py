import aws_cdk
import constructs

from infra import config


class UsecaseAppStack(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)
