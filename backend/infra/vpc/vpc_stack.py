import aws_cdk
import constructs
from aws_cdk import Tags, aws_ec2

from infra import config


class VpcStack(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        subnet_count: int = 3,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        vpc_name = app_config.environment_config["vpc-name"]

        vpc = aws_ec2.Vpc(
            self,
            "Vpc",
            vpc_name=vpc_name,
            ip_addresses=aws_ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=subnet_count,
            nat_gateways=1,
            subnet_configuration=[
                aws_ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=aws_ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                aws_ec2.SubnetConfiguration(
                    name="private",
                    subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
            ],
        )

        subnet_names = app_config.component_specific.get("subnet-names", [])
        for i, subnet in enumerate(vpc.private_subnets):
            if i < len(subnet_names):
                Tags.of(subnet).add("Name", subnet_names[i])
