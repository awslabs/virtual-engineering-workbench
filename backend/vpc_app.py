#!/usr/bin/env python3
import aws_cdk

from infra import config
from infra.vpc import vpc_stack

app = aws_cdk.App()

environment = app.node.try_get_context("environment")
account = app.node.try_get_context("account")
region = app.node.try_get_context("region")

base_config = config.BaseConfig(
    environment=environment,
    account=account,
    region=region,
    web_app_account=account,
)

vpc_app_config = config.AppConfig(
    **base_config.dict(),
    component_name="vpc",
    environment_config=config.env_config[environment],
    component_specific=config.vpc_config[environment],
)

vpc_stack.VpcStack(
    app,
    "VpcStack",
    app_config=vpc_app_config,
    stack_name=base_config.format_base_resource_name("vpc"),
    env=aws_cdk.Environment(account=account, region=region),
)

app.synth()
