import cdk_nag
import constructs
from aws_cdk import aws_certificatemanager, aws_ec2, aws_elasticloadbalancingv2, aws_elasticloadbalancingv2_targets

from infra import config


class PrivateApiGwAlb(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        certificate: aws_certificatemanager.ICertificate,
        vpc_endpoint_ips: list[str],
    ) -> None:
        super().__init__(scope, id)

        # VPC
        vpc_name = app_config.environment_config["vpc-name"]
        vpc = aws_ec2.Vpc.from_lookup(self, "vpc", vpc_name=vpc_name)

        # Application Load Balancer
        alb_security_group = aws_ec2.SecurityGroup(
            self,
            "ALBSecurityGroup",
            allow_all_outbound=False,
            vpc=vpc,
        )

        for cidr in app_config.environment_config["allowed-cidrs-for-private-api-endpoint"]:
            alb_security_group.add_ingress_rule(
                connection=aws_ec2.Port.tcp(443),
                description=f"Allow HTTPS traffic from {cidr}.",
                peer=aws_ec2.Peer.ipv4(cidr),
            )
        alb_security_group.add_egress_rule(
            connection=aws_ec2.Port.tcp(443),
            description="Allow HTTPS traffic to this VPC.",
            peer=aws_ec2.Peer.ipv4(vpc.vpc_cidr_block),
        )

        alb = aws_elasticloadbalancingv2.ApplicationLoadBalancer(
            self,
            "ALB",
            deletion_protection=True if app_config.environment_config["retain_resources"] else False,
            drop_invalid_header_fields=True,
            security_group=alb_security_group,
            vpc=vpc,
            vpc_subnets=aws_ec2.SubnetSelection(),
        )
        alb_listener = alb.add_listener(
            "ALBHTTPSListener",
            certificates=[certificate],
            open=False,
            port=443,
            protocol=aws_elasticloadbalancingv2.ApplicationProtocol.HTTPS,
        )

        # Application Load Balancer Target Group
        alb_target_ips = [aws_elasticloadbalancingv2_targets.IpTarget(ip) for ip in vpc_endpoint_ips]
        alb_target_group = aws_elasticloadbalancingv2.ApplicationTargetGroup(
            self,
            "ALBTargetGroup",
            health_check=aws_elasticloadbalancingv2.HealthCheck(
                healthy_http_codes="200",
                path="/ping",
                protocol=aws_elasticloadbalancingv2.Protocol.HTTPS,
            ),
            port=443,
            protocol=aws_elasticloadbalancingv2.ApplicationProtocol.HTTPS,
            target_type=aws_elasticloadbalancingv2.TargetType.IP,
            targets=alb_target_ips,
            vpc=vpc,
        )

        alb_listener.add_target_groups("AddALBTargetGroup", target_groups=[alb_target_group])

        # cdk-nag suppressions
        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=alb,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-ELB2",
                    reason="ALB acts as a reverse proxy to the REST APIs that have logging enabled.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-ELBDeletionProtectionEnabled",
                    reason="Deletion protection is enabled only in PROD environment.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-ELBDeletionProtectionEnabled",
                    reason="Deletion protection is enabled only in PROD environment.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-ALBWAFEnabled",
                    reason="WAF not required since this is an internal ALB.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-ELBLoggingEnabled",
                    reason="ALB acts as a reverse proxy to the REST APIs that have logging enabled.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-ALBWAFEnabled",
                    reason="WAF not required since this is an internal ALB.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-ELBLoggingEnabled",
                    reason="ALB acts as a reverse proxy to the REST APIs that have logging enabled.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-ALBWAFEnabled",
                    reason="WAF not required since this is an internal ALB.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-ELBLoggingEnabled",
                    reason="ALB acts as a reverse proxy to the REST APIs that have logging enabled.",
                ),
            ],
        )
