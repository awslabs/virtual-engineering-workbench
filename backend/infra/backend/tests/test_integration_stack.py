import aws_cdk
import pytest
from aws_cdk import aws_apigateway
from aws_cdk.assertions import Template

from infra import config
from infra.backend import integration_stack

DOMAIN_NAME = "api.vew.example.internal"
CERT_ARN = "arn:aws:acm:eu-north-1:111111111111:certificate/00000000-0000-0000-0000-000000000000"
PRIVATE_CA_ARN = "arn:aws:acm-pca:eu-north-1:222222222222:certificate-authority/11111111-1111-1111-1111-111111111111"
ENV = aws_cdk.Environment(account="111111111111", region="eu-north-1")


def _integration_stack(cert_arn=None, private_ca_arn=None):
    app = aws_cdk.App()
    api_stack = aws_cdk.Stack(app, "ApiStack", env=ENV)
    api = aws_apigateway.RestApi(api_stack, "Api")
    api.root.add_method("GET")
    app_config = config.AppConfig(
        account=ENV.account,
        region=ENV.region,
        environment="dev",
        web_app_account=ENV.account,
        image_service_account=ENV.account,
        catalog_service_account=ENV.account,
        component_name="api-integration",
        environment_config=config.env_config["dev"],
        component_specific=dict(),
    )
    return integration_stack.ApiIntegrationStack(
        app,
        "ApiIntegrationStack",
        app_config=app_config,
        api_integration_mapping=integration_stack.ApiIntegrationMapping(
            domain_name=DOMAIN_NAME,
            cert_arn=cert_arn,
            mappings=[integration_stack.ApiToPathMapping(api=api, base_path="projects")],
            private_ca_arn=private_ca_arn,
        ),
        provision_private_endpoint=True,
        vpc_endpoint_ips=["10.0.0.10"],
        env=ENV,
    )


def test_private_ca_certificate_is_requested_for_the_api_domain():
    template = Template.from_stack(_integration_stack(private_ca_arn=PRIVATE_CA_ARN))

    template.resource_count_is("AWS::CertificateManager::Certificate", 1)
    template.has_resource_properties(
        "AWS::CertificateManager::Certificate",
        {
            "DomainName": DOMAIN_NAME,
            "CertificateAuthorityArn": PRIVATE_CA_ARN,
            "KeyAlgorithm": "RSA_2048",
        },
    )


def test_private_ca_certificate_is_served_on_the_api_domain_and_alb():
    template = Template.from_stack(_integration_stack(private_ca_arn=PRIVATE_CA_ARN))
    [certificate_id] = template.find_resources("AWS::CertificateManager::Certificate")

    template.has_resource_properties(
        "AWS::ApiGateway::DomainName",
        {"DomainName": DOMAIN_NAME, "RegionalCertificateArn": {"Ref": certificate_id}},
    )
    template.has_resource_properties(
        "AWS::ElasticLoadBalancingV2::Listener",
        {"Certificates": [{"CertificateArn": {"Ref": certificate_id}}]},
    )


def test_given_certificate_is_served_without_requesting_one():
    template = Template.from_stack(_integration_stack(cert_arn=CERT_ARN))

    template.resource_count_is("AWS::CertificateManager::Certificate", 0)
    template.has_resource_properties("AWS::ApiGateway::DomainName", {"RegionalCertificateArn": CERT_ARN})
    template.has_resource_properties(
        "AWS::ElasticLoadBalancingV2::Listener",
        {"Certificates": [{"CertificateArn": CERT_ARN}]},
    )


def test_certificate_or_private_ca_is_required():
    with pytest.raises(ValueError, match="Neither a certificate ARN nor a private CA ARN is given"):
        _integration_stack()


def test_certificate_and_private_ca_are_not_both_accepted():
    with pytest.raises(ValueError, match="not both"):
        _integration_stack(cert_arn=CERT_ARN, private_ca_arn=PRIVATE_CA_ARN)
