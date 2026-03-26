import json

import constructs
from aws_cdk import CfnTag, aws_appconfig

from infra import config


class AppConfigFunction(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        parameter_name: str,
        parameter_content: dict,
    ) -> None:
        super().__init__(scope, id)

        self._application_name = app_config.format_resource_name("app-config")
        self._enviroment_name = app_config.format_resource_name("enviroment")
        self._profile_name = app_config.format_resource_name(parameter_name)
        self._deployment_strategy_name = app_config.format_resource_name("deployment-strategy")

        self._cfn_application = aws_appconfig.CfnApplication(
            self,
            "MyCfnApplication",
            name=self._application_name,
            description="description",
            tags=[CfnTag(key="env", value=self._enviroment_name)],
        )

        self._environment = aws_appconfig.CfnEnvironment(
            self,
            "MyCfnEnvironment",
            application_id=self._cfn_application.ref,
            name=self._enviroment_name,
            description="description",
            # monitors=[aws_cdk.appconfig.CfnEnvironment.MonitorsProperty(
            #     alarm_arn="alarmArn",
            #     alarm_role_arn="alarmRoleArn"
            # )],
            tags=[CfnTag(key="env", value=self._enviroment_name)],
        )

        self._configuration_profile = aws_appconfig.CfnConfigurationProfile(
            self,
            "MyCfnConfigurationProfile",
            application_id=self._cfn_application.ref,
            location_uri="hosted",
            name=self._profile_name,
            # the properties below are optional
            description="description",
            tags=[CfnTag(key="env", value=self._enviroment_name)],
            type="AWS.Freeform",
            # validators=[aws_appconfig.CfnConfigurationProfile.ValidatorsProperty(
            #     content="content",
            #     type="type"
            # )]
        )

        self._hosted_configuration_version = aws_appconfig.CfnHostedConfigurationVersion(
            self,
            "MyCfnHostedConfigurationVersion",
            application_id=self._cfn_application.ref,
            configuration_profile_id=self._configuration_profile.ref,
            content=json.dumps(parameter_content),
            content_type="text/plain",
            # the properties below are optional
            description="description",
            # latest_version_number=123
        )

        self._deployment_strategy = aws_appconfig.CfnDeploymentStrategy(
            self,
            "MyCfnDeploymentStrategy",
            deployment_duration_in_minutes=0,
            growth_factor=100,
            name=self._deployment_strategy_name,
            replicate_to="NONE",
            # the properties below are optional
            description="description",
            final_bake_time_in_minutes=5,
            growth_type="LINEAR",
            tags=[CfnTag(key="env", value=self._enviroment_name)],
        )

        self._deployment = aws_appconfig.CfnDeployment(
            self,
            "MyCfnDeployment",
            application_id=self._cfn_application.ref,
            configuration_profile_id=self._configuration_profile.ref,
            configuration_version=self._hosted_configuration_version.ref,
            deployment_strategy_id=self._deployment_strategy.ref,
            environment_id=self._environment.ref,
            # the properties below are optional
            description="description",
            tags=[CfnTag(key="env", value=self._enviroment_name)],
        )

    @property
    def get_application_id(self) -> str:
        return self._cfn_application.ref

    @property
    def get_enviroment_id(self) -> str:
        return self._environment.ref

    @property
    def get_appconfig_application_name(self) -> str:
        return self._application_name

    @property
    def get_appconfig_enviroment_name(self) -> str:
        return self._enviroment_name

    @property
    def get_appconfig_profile_name(self) -> str:
        return self._profile_name
