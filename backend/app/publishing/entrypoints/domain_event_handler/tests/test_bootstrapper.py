import logging

import assertpy

from app.publishing.entrypoints.domain_event_handler import bootstrapper, config


def test_bootstrapper():
    # ARRANGE
    app_config = config.AppConfig()

    # ACT
    dependencies = bootstrapper.bootstrap(app_config=app_config, logger=logging.getLogger())

    # ASSERT
    assertpy.assert_that(dependencies).is_not_none()
