import logging

import assertpy

from app.provisioning.entrypoints.provisioned_product_state_event_handler import bootstrapper, config
from app.shared.middleware import event_handler


def test_bootstrapper():
    # ARRANGE
    app_config = config.AppConfig()
    app = event_handler.EventBridgeEventResolver(logger=logging.getLogger())

    # ACT
    dependencies = bootstrapper.bootstrap(app_config=app_config, logger=logging.getLogger(), app=app)

    # ASSERT
    assertpy.assert_that(dependencies).is_not_none()
