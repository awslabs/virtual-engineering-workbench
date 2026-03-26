import json
import logging
import typing
from typing import List

from pydantic.json import pydantic_encoder

from app.shared.adapters.feature_toggling import feature, frontend_feature
from app.shared.api import parameter_service


class FrontendFeatureToggles:
    def __init__(
        self,
        logger: logging.Logger,
        parameter_service: parameter_service.ParameterService,
        parameter_name: str,
    ) -> None:
        self._logger = logger
        self._parameter_service = parameter_service
        self._parameter_name = parameter_name

    def get_single_feature_configuration(self, feature: str) -> List[feature.Feature]:
        features = self.get_feature_configuration()

        return [f for f in features if f.feature == feature]

    def get_feature_configuration(self) -> typing.List[feature.Feature]:
        try:
            feature_toggles_raw = json.loads(
                self._parameter_service.get_parameter_value(self._parameter_name)
            )
        except:
            self._logger.exception(
                "Unable to fetch feature toggles form parameter store."
            )
            feature_toggles_raw = []

        try:
            feature_toggles = [
                feature.Feature.parse_obj(f) for f in feature_toggles_raw
            ]
        except:
            self._logger.exception(
                "Feature toggle value in parameter store is malformed."
            )
            feature_toggles = []

        return feature_toggles

    def get_enabled_features_for_user(
        self, user_id: str
    ) -> typing.List[frontend_feature.FrontendFeature]:
        features = self.get_feature_configuration()

        return [
            frontend_feature.FrontendFeature(
                version=f.version,
                feature=f.feature,
                enabled=True,
            )
            for f in features
            if f.enabled or user_id.upper() in (f.userOverrides or [])
        ]

    def add_feature(self, feat: feature.Feature):
        feature_toggles = self.get_feature_configuration()
        feature_toggles = list(
            filter(lambda f: f.feature != feat.feature, feature_toggles)
        )
        feature_toggles.append(feat)

        self._parameter_service.create_string_parameter(
            parameter_name=self._parameter_name,
            parameter_value=json.dumps(feature_toggles, default=pydantic_encoder),
            is_overwrite=True,
        )
