import os
from enum import StrEnum


class BackendFeature(StrEnum):
    ProvisionWorkbenchPHDCheck = "PHD_CHECK"
    PublishingContainerProducts = "PUBLISHING_CONTAINER_PRODUCTS"


FEATURE_PREFIX = "FEATURE_"


class BackendFeatureToggles:
    def __init__(self, feature_config: dict[str, bool]):
        self._feature_config = feature_config

    def is_enabled(self, feature: BackendFeature) -> bool | None:
        return self._feature_config.get(f"{FEATURE_PREFIX}{feature}", None)


def from_environment_variables() -> BackendFeatureToggles:
    feature_config: dict[str, bool] = {
        key: bool(value) for key, value in os.environ.items() if key.startswith(FEATURE_PREFIX)
    }

    return BackendFeatureToggles(feature_config=feature_config)
