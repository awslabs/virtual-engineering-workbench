import json
import logging
import os
from typing import List
from unittest import mock

import assertpy

from app.shared.adapters.feature_toggling import backend_feature_toggles, feature, frontend_feature_toggles
from app.shared.api import parameter_service


class MockParameterService(parameter_service.ParameterService):
    def __init__(self):
        super().__init__()
        self._parameter_value = ""

    def create_string_parameter(self, parameter_name: str, parameter_value: str, is_overwrite: bool = False) -> None:
        self._parameter_value = parameter_value

    def get_list_parameter_value(self, parameter_name: str) -> List[str]:
        return json.loads(self._parameter_value)

    def get_parameter_value(self, parameter_name: str) -> str:
        return self._parameter_value


def test_get_feature_configuration_when_valid_should_return():
    # ARRANGE
    ps = mock.create_autospec(spec=parameter_service.ParameterService)
    ps.get_parameter_value.return_value = json.dumps(
        [{"version": "1.0.0", "feature": "HILDevicesList", "enabled": False, "userOverrides": ["T0011AA"]}]
    )

    ft = frontend_feature_toggles.FrontendFeatureToggles(
        logger=mock.create_autospec(spec=logging.Logger), parameter_service=ps, parameter_name="test"
    )
    # ACT
    features = ft.get_feature_configuration()

    # ASSERT
    assertpy.assert_that(features).is_length(1)
    assertpy.assert_that(features[0].feature).is_equal_to("HILDevicesList")
    assertpy.assert_that(features[0].enabled).is_equal_to(False)
    assertpy.assert_that(features[0].userOverrides).contains_only("T0011AA")


def test_get_feature_configuration_when_invalid_should_return_empty():
    # ARRANGE
    ps = mock.create_autospec(spec=parameter_service.ParameterService)
    ps.get_parameter_value.return_value = "random text"

    ft = frontend_feature_toggles.FrontendFeatureToggles(
        logger=mock.create_autospec(spec=logging.Logger), parameter_service=ps, parameter_name="test"
    )
    # ACT
    features = ft.get_feature_configuration()

    # ASSERT
    assertpy.assert_that(features).is_length(0)


def test_get_enabled_features_for_user_when_enabled_should_include():
    # ARRANGE
    ps = mock.create_autospec(spec=parameter_service.ParameterService)
    ps.get_parameter_value.return_value = json.dumps(
        [{"version": "1.0.0", "feature": "HILDevicesList", "enabled": True, "userOverrides": ["T0011AA"]}]
    )

    ft = frontend_feature_toggles.FrontendFeatureToggles(
        logger=mock.create_autospec(spec=logging.Logger), parameter_service=ps, parameter_name="test"
    )
    # ACT
    features = ft.get_enabled_features_for_user("T1100BB")

    # ASSERT
    assertpy.assert_that(features).is_length(1)
    assertpy.assert_that(features[0].feature).is_equal_to("HILDevicesList")
    assertpy.assert_that(features[0].enabled).is_equal_to(True)


def test_get_enabled_features_for_user_when_overriden_should_include():
    # ARRANGE
    ps = mock.create_autospec(spec=parameter_service.ParameterService)
    ps.get_parameter_value.return_value = json.dumps(
        [{"version": "1.0.0", "feature": "HILDevicesList", "enabled": False, "userOverrides": ["T0011AA"]}]
    )

    ft = frontend_feature_toggles.FrontendFeatureToggles(
        logger=mock.create_autospec(spec=logging.Logger), parameter_service=ps, parameter_name="test"
    )
    # ACT
    features = ft.get_enabled_features_for_user("T0011AA")

    # ASSERT
    assertpy.assert_that(features).is_length(1)
    assertpy.assert_that(features[0].feature).is_equal_to("HILDevicesList")
    assertpy.assert_that(features[0].enabled).is_equal_to(True)


def test_get_enabled_features_for_user_when_not_enabled_should_not_return():
    # ARRANGE
    ps = mock.create_autospec(spec=parameter_service.ParameterService)
    ps.get_parameter_value.return_value = json.dumps(
        [{"version": "1.0.0", "feature": "HILDevicesList", "enabled": False, "userOverrides": ["T0011AA"]}]
    )

    ft = frontend_feature_toggles.FrontendFeatureToggles(
        logger=mock.create_autospec(spec=logging.Logger), parameter_service=ps, parameter_name="test"
    )
    # ACT
    features = ft.get_enabled_features_for_user("T1100BB")

    # ASSERT
    assertpy.assert_that(features).is_length(0)


def test_can_add_feature_to_feature_toggle():
    # ARRANGE
    ps = MockParameterService()
    ps.create_string_parameter(
        parameter_name="fake",
        parameter_value=json.dumps(
            [{"version": "1.0.0", "feature": "WebAppAccess", "enabled": True, "userOverrides": []}]
        ),
    )
    ft = frontend_feature_toggles.FrontendFeatureToggles(
        logger=mock.create_autospec(spec=logging.Logger), parameter_service=ps, parameter_name="test"
    )

    feat = feature.Feature(version="1.0.0", feature="HILDevicesList", enabled=False, userOverrides=["T0011AA"])
    # ACT
    ft.add_feature(feat)
    # ASSERT
    assertpy.assert_that(ps.get_parameter_value("fake")).is_equal_to(
        json.dumps(
            [
                {"version": "1.0.0", "feature": "WebAppAccess", "enabled": True, "userOverrides": []},
                {"version": "1.0.0", "feature": "HILDevicesList", "enabled": False, "userOverrides": ["T0011AA"]},
            ]
        )
    )


def test_can_replace_feature_to_feature_toggle():
    # ARRANGE
    ps = MockParameterService()
    ps.create_string_parameter(
        parameter_name="fake",
        parameter_value=json.dumps(
            [
                {"version": "1.0.0", "feature": "WebAppAccess", "enabled": True, "userOverrides": []},
                {"version": "1.0.0", "feature": "HILDevicesList", "enabled": True, "userOverrides": ["T0011AA"]},
            ]
        ),
    )
    ft = frontend_feature_toggles.FrontendFeatureToggles(
        logger=mock.create_autospec(spec=logging.Logger), parameter_service=ps, parameter_name="test"
    )

    feat = feature.Feature(version="1.0.0", feature="HILDevicesList", enabled=False, userOverrides=["T0011AA"])
    # ACT
    ft.add_feature(feat)
    # ASSERT
    assertpy.assert_that(ps.get_parameter_value("fake")).is_equal_to(
        json.dumps(
            [
                {"version": "1.0.0", "feature": "WebAppAccess", "enabled": True, "userOverrides": []},
                {"version": "1.0.0", "feature": "HILDevicesList", "enabled": False, "userOverrides": ["T0011AA"]},
            ]
        )
    )


def test_backend_feature_toggles_when_exists_should_return_status():
    # ARRANGE
    os.environ["FEATURE_PHD_CHECK"] = "true"
    ft = backend_feature_toggles.from_environment_variables()

    # ACT
    is_enabled = ft.is_enabled(backend_feature_toggles.BackendFeature.ProvisionWorkbenchPHDCheck)

    # ASSERT
    assertpy.assert_that(is_enabled).is_true()


def test_backend_feature_when_not_exists_should_default_to_false():
    # ARRANGE
    if "FEATURE_PHD_CHECK" in os.environ:
        del os.environ["FEATURE_PHD_CHECK"]
    ft = backend_feature_toggles.from_environment_variables()

    # ACT
    is_enabled = ft.is_enabled(backend_feature_toggles.BackendFeature.ProvisionWorkbenchPHDCheck)

    # ASSERT
    assertpy.assert_that(is_enabled).is_false()
