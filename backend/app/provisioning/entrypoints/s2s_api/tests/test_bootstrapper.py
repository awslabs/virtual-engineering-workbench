import logging

import assertpy
from aws_lambda_powertools.event_handler import api_gateway

from app.provisioning.entrypoints.s2s_api import bootstrapper, config


def test_bootstrapper():
    # ARRANGE
    app_config = config.AppConfig(**config.config)
    app = api_gateway.APIGatewayRestResolver()

    # ACT
    dependencies = bootstrapper.bootstrap(app_config=app_config, logger=logging.getLogger(), app=app)

    # ASSERT
    assertpy.assert_that(dependencies).is_not_none()
