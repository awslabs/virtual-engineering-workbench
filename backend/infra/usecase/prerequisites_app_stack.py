import aws_cdk
import cdk_nag
import constructs
from aws_cdk import ArnFormat, aws_iam

from infra import config, constants
from infra.constructs.iam import role


class PrerequisitesAppStack(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        web_application_account: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.__dynamic_bootstrap_role = role.Role(
            self,
            "DynamicBootstrapRole",
            assumed_by=aws_iam.AccountPrincipal(account_id=web_application_account)
            .with_conditions(
                {
                    "ForAllValues:StringLike": {
                        "aws:PrincipalArn": self.format_arn(
                            account=web_application_account,
                            partition=self.partition,
                            region="",
                            resource="role",
                            resource_name=app_config.format_resource_name_with_component("projects", "*"),
                            service="iam",
                        ),
                        "aws:RequestTag/UserId": "*",
                    }
                }
            )
            .with_session_tags(),
            description="Role used to setup the dynamic resources during bootstrapping.",
            permissions=[
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ec2:DescribeVpcs",
                            "ec2:DescribeSubnets",
                            "route53:CreateHostedZone",
                            "route53:ListHostedZonesByName",
                            "route53:ListHostedZonesByVPC",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            "*",
                        ],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "route53:AssociateVPCWithHostedZone",
                            "route53:ChangeResourceRecordSets",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            self.format_arn(
                                account="",
                                partition=self.partition,
                                region="",
                                resource="hostedzone",
                                resource_name="*",
                                service="route53",
                            ),
                        ],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "secretsmanager:CreateSecret",
                            "secretsmanager:UpdateSecret",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            self.format_arn(
                                account=self.account,
                                arn_format=ArnFormat.COLON_RESOURCE_NAME,
                                partition=self.partition,
                                region=self.region,
                                resource="secret",
                                resource_name="*",
                                service="secretsmanager",
                            ),
                        ],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "secretsmanager:ListSecrets",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            "*",
                        ],
                    )
                ),
                lambda rl: rl.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ssm:GetParameter",
                            "ssm:GetParameters",
                            "ssm:GetParametersByPath",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            self.format_arn(
                                account=self.account,
                                partition=self.partition,
                                region=self.region,
                                resource="parameter",
                                resource_name=app_config.format_ssm_parameter_name(
                                    component_name=constants.PROJECTS_SPOKE_ACCOUNT_SSM_PARAMETER_SCOPE,
                                    name=None,
                                    include_environment=False,
                                )[1:],
                                service="ssm",
                            ),
                        ],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=["ssm:PutParameter", "ssm:GetParameter"],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            self.format_arn(
                                account=self.account,
                                partition=self.partition,
                                region=self.region,
                                resource="parameter",
                                resource_name=app_config.environment_config["spoke-account-vpc-id-param-name"][1:],
                                service="ssm",
                            ),
                            self.format_arn(
                                account=self.account,
                                partition=self.partition,
                                region=self.region,
                                resource="parameter",
                                resource_name=app_config.environment_config[
                                    "spoke-account-backend-subnet-ids-param-name"
                                ][1:],
                                service="ssm",
                            ),
                            self.format_arn(
                                account=self.account,
                                partition=self.partition,
                                region=self.region,
                                resource="parameter",
                                resource_name=app_config.environment_config[
                                    "spoke-account-backend-subnet-cidrs-param-name"
                                ][1:],
                                service="ssm",
                            ),
                        ],
                    )
                ),
            ],
            role_name=constants.PROJECTS_DYNAMIC_BOOTSTRAP_ROLE,
        )

        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=self.__dynamic_bootstrap_role,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Role gives permission to fetch all SSM parameters from a specific path.",
                ),
            ],
            apply_to_children=True,
        )

    @property
    def dynamic_bootstrap_role(self) -> role.Role:
        return self.__dynamic_bootstrap_role
