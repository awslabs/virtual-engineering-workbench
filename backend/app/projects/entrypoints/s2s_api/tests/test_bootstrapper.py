import logging

import assertpy

from app.projects.entrypoints.s2s_api import bootstrapper, config


def test_bootstrapper():
    # ARRANGE
    app_config = config.AppConfig(cors_config=config.config.get("cors_config"))

    # ACT
    dependencies = bootstrapper.bootstrap(app_config=app_config, logger=logging.getLogger())

    # ASSERT
    assertpy.assert_that(dependencies).is_not_none()
