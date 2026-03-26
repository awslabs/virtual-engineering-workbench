import cdk_nag
from aws_cdk import (
    Stack,
    aws_ec2,
    aws_events,
    aws_events_targets,
    aws_iam,
    aws_ssm,
)
from constructs import Construct

from infra import config, constants


class ProvisioningEnablementStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        app_config: config.AppConfig,
        web_application_account: str,
        web_application_region: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # EC2 events forwarder rule
        aws_events.Rule(
            self,
            "ec2-events-forwarder-rule",
            rule_name=app_config.format_resource_name("ec2-evt-fw-rule"),
            event_pattern=aws_events.EventPattern(
                source=aws_events.Match.exact_string("aws.ec2"),
                detail_type=aws_events.Match.exact_string("EC2 Instance State-change Notification"),
                account=aws_events.Match.exact_string(self.account),
            ),
            targets=[
                aws_events_targets.EventBus(
                    aws_events.EventBus.from_event_bus_arn(
                        self,
                        "provisioning-ec2-event-bus",
                        self.format_arn(
                            resource="event-bus",
                            service="events",
                            account=web_application_account,
                            partition=self.partition,
                            region=web_application_region,
                            resource_name=app_config.format_resource_name_with_component(
                                "provisioning", "ec2-event-bus"
                            ),
                        ),
                    )
                )
            ],
        )

        # ECS events forwarder rule
        aws_events.Rule(
            self,
            "ecs-events-forwarder-rule",
            rule_name=app_config.format_resource_name("ecs-evt-fw-rule"),
            event_pattern=aws_events.EventPattern(
                source=aws_events.Match.exact_string("aws.ecs"),
                detail_type=aws_events.Match.exact_string("ECS Task State Change"),
                account=aws_events.Match.exact_string(self.account),
            ),
            targets=[
                aws_events_targets.EventBus(
                    aws_events.EventBus.from_event_bus_arn(
                        self,
                        "provisioning-ecs-event-bus",
                        self.format_arn(
                            resource="event-bus",
                            service="events",
                            account=web_application_account,
                            partition=self.partition,
                            region=web_application_region,
                            resource_name=app_config.format_resource_name_with_component(
                                "provisioning", "ecs-event-bus"
                            ),
                        ),
                    )
                )
            ],
        )

        # Provisioned product task role managed policy
        aws_iam.ManagedPolicy(
            self,
            "ProvisionedProductTaskRolePermissionsPolicy",
            managed_policy_name=constants.PROVISIONED_PRODUCT_TASK_ROLE_POLICY,
            description="This managed policy contains centrally managed IAM permissions for all VEW Containers.",
            statements=[
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=["s3:Get*", "s3:List*"],
                    resources=[
                        "arn:aws:s3:::*-repository.vew",
                        "arn:aws:s3:::*-repository.vew/*",
                    ],
                )
            ],
        )

        # Provisioned product instance profile managed policy
        instance_profile_statements = [
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=[
                    "ec2:ModifyInstanceMetadataOptions",
                    "ec2:DescribeInstances",
                ],
                resources=["*"],
            ),
        ]

        aws_iam.ManagedPolicy(
            self,
            "ProvisionedProductInstanceProfilePermissionsPolicy",
            managed_policy_name=constants.PROVISIONED_PRODUCT_INSTANCE_PROFILE_POLICY,
            description="This managed policy contains centrally managed IAM permissions for all VEW Workbench and Virtual Target instances.",
            statements=instance_profile_statements,
        )

        # Provisioned product security group
        vpc_id = aws_ssm.StringParameter.value_from_lookup(
            self, app_config.environment_config["spoke-account-vpc-id-param-name"]
        )
        vpc = aws_ec2.Vpc.from_lookup(self, "Vpc", vpc_id=vpc_id)

        provisioned_product_sg = aws_ec2.SecurityGroup(
            self,
            "ProvisionedProductSecutiryGroup",
            vpc=vpc,
            allow_all_outbound=False,
            security_group_name=app_config.format_resource_name("pp-sg"),
            description="Contains centrally managed security group rules for all workbenches and virtual targets",
        )

        aws_ssm.StringParameter(
            self,
            "ProvisionedProductSG",
            description="Security Group ID for all provisioned products",
            parameter_name=app_config.format_ssm_parameter_name(name="pp-sg", include_environment=False),
            string_value=provisioned_product_sg.security_group_id,
        )

        # Stack based suppressions
        cdk_nag.NagSuppressions.add_stack_suppressions(
            stack=Stack.of(self),
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-IAMNoInlinePolicy",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-IAMNoInlinePolicy",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-IAMNoInlinePolicy",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
            ],
        )
