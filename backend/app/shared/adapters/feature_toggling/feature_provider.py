import os
from abc import ABC, abstractmethod
from enum import StrEnum


class Feature(StrEnum):
    ProvisionWorkbenchPHDCheck = "ProvisionWorkbenchPHDCheck"


FEATURE_PREFIX = "FEATURE_"


class FeatureProvider(ABC):
    @abstractmethod
    def is_enabled(self, feature: Feature) -> bool | None: ...


class InMemoryFeatureProvider(FeatureProvider):
    def __init__(self, feature_config: dict[str, bool]):
        self._feature_config = feature_config

    def is_enabled(self, feature: Feature) -> bool | None:
        return self._feature_config.get(feature, None)


def from_environment_variables() -> FeatureProvider:
    feature_config: dict[str, bool] = {
        key: bool(value) for key, value in os.environ.items() if key.startswith(FEATURE_PREFIX)
    }

    return InMemoryFeatureProvider(feature_config=feature_config)
