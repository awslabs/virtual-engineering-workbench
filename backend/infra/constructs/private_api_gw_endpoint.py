import aws_cdk
import cdk_nag
import constructs
from aws_cdk import aws_ec2, custom_resources

from infra import config


class PrivateApiGwEndpoint(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
    ) -> None:
        super().__init__(scope, id)

        # VPC
        vpc_name = app_config.environment_config["vpc-name"]
        vpc = aws_ec2.Vpc.from_lookup(self, "vpc", vpc_name=vpc_name)

        # VPC Endpoint for API Gateway
        vpc_endpoint_security_group = aws_ec2.SecurityGroup(
            self,
            "VPCEndpointSecurityGroup",
            allow_all_outbound=False,
            vpc=vpc,
        )

        vpc_endpoint_security_group.add_ingress_rule(
            connection=aws_ec2.Port.tcp(443),
            description="Allow HTTPS traffic from this VPC.",
            peer=aws_ec2.Peer.ipv4(vpc.vpc_cidr_block),
        )

        self._vpc_endpoint = vpc.add_interface_endpoint(
            "VPCEndpoint",
            security_groups=[vpc_endpoint_security_group],
            service=aws_ec2.InterfaceVpcEndpointAwsService.APIGATEWAY,
            subnets=aws_ec2.SubnetSelection(),
        )
        vpc_endpoint_ips = custom_resources.AwsCustomResource(
            self,
            "VPCEndpointIPs",
            on_update=custom_resources.AwsSdkCall(
                action="describeNetworkInterfaces",
                parameters={
                    "NetworkInterfaceIds": self._vpc_endpoint.vpc_endpoint_network_interface_ids,
                },
                # With no parameters the values returned from vpc.select_subnets().subnets
                # will be exactly equal to those returned from aws_ec2.SubnetSelection()
                output_paths=[
                    f"NetworkInterfaces.{i}.PrivateIpAddress" for i in range(len(vpc.select_subnets().subnets))
                ],
                physical_resource_id=custom_resources.PhysicalResourceId.of("EndpointNics"),
                service="EC2",
            ),
            policy=custom_resources.AwsCustomResourcePolicy.from_sdk_calls(
                resources=custom_resources.AwsCustomResourcePolicy.ANY_RESOURCE,
            ),
        )
        # With no parameters the values returned from vpc.select_subnets().subnets
        # will be exactly equal to those returned from aws_ec2.SubnetSelection()
        self._vpc_endpoint_ips = [
            vpc_endpoint_ips.get_response_field(f"NetworkInterfaces.{i}.PrivateIpAddress")
            for i in range(len(vpc.select_subnets().subnets))
        ]

        # cdk-nag suppressions
        cdk_nag.NagSuppressions.add_resource_suppressions_by_path(
            path=f"/{aws_cdk.Stack.of(self).node.path}/AWS679f53fac002430cb0da5b7982bd2287/Resource",
            stack=aws_cdk.Stack.of(self),
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="The Lambda function is managed by AWS CDK via the Custom Resources framework.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-LambdaInsideVPC",
                    reason="The Lambda function is managed by AWS CDK via the Custom Resources framework.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-LambdaConcurrency",
                    reason="The Lambda function is managed by AWS CDK via the Custom Resources framework.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-LambdaDLQ",
                    reason="The Lambda function is managed by AWS CDK via the Custom Resources framework.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-LambdaInsideVPC",
                    reason="The Lambda function is managed by AWS CDK via the Custom Resources framework.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-LambdaInsideVPC",
                    reason="The Lambda function is managed by AWS CDK via the Custom Resources framework.",
                ),
            ],
        )
        cdk_nag.NagSuppressions.add_resource_suppressions_by_path(
            path=f"/{vpc_endpoint_ips.node.path}/CustomResourcePolicy/Resource",
            stack=aws_cdk.Stack.of(self),
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="The API call `describeNetworkInterfaces` requires `*` permissions to work.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-IAMNoInlinePolicy",
                    reason="The inline policy is managed by AWS CDK via the Custom Resources framework.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-IAMNoInlinePolicy",
                    reason="The inline policy is managed by AWS CDK via the Custom Resources framework.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-IAMNoInlinePolicy",
                    reason="The inline policy is managed by AWS CDK via the Custom Resources framework.",
                ),
            ],
        )
        cdk_nag.NagSuppressions.add_stack_suppressions(
            stack=aws_cdk.Stack.of(self),
            suppressions=[
                cdk_nag.NagPackSuppression(
                    applies_to=[
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                    ],
                    id="AwsSolutions-IAM4",
                    reason="`AWSLambdaBasicExecutionRole` is managed by AWS CDK via the Custom Resources framework.",
                ),
            ],
        )

    @property
    def vpc_endpoint(self) -> aws_ec2.VpcEndpoint:
        return self._vpc_endpoint

    @property
    def vpc_endpoint_ips(self) -> aws_ec2.VpcEndpoint:
        return self._vpc_endpoint_ips
