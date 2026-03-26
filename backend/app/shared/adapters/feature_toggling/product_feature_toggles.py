import json
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field

# Work with processing feature toggles set in product templates
# Example:
# FeatureToggles:
#     Description: Enabled features for this workbench
#     Value: '[{ "feature": "DCVConnectionOptions", "enabled": true }, { "feature": "WorkbenchWorkingDirectoryEnabled", "enabled": true }]'


class ProductFeature(StrEnum):
    DCVConnectionOptions = "DCVConnectionOptions"
    DCVPublicEndpoint = "DCVPublicEndpoint"
    WorkbenchWorkingDirectoryEnabled = "WorkbenchWorkingDirectoryEnabled"
    AutoStopProtection = "AutoStopProtection"


class Output(BaseModel):
    outputKey: str = Field(..., title="OutputKey")
    outputValue: str = Field(..., title="OutputValue")
    description: Optional[str] = Field(None, title="Description")


class Feature(BaseModel):
    feature: str = Field(..., title="Feature")
    enabled: bool = Field(..., title="Enabled")  # noqa: F821 (false positive


class ProductFeatureToggles:
    def __init__(self, outputs: list[Output]):
        self.__feature_toggles = None
        if outputs:
            feature_toggles_json = next(
                (json.loads(output.outputValue) for output in outputs if output.outputKey == "FeatureToggles"), None
            )
            if feature_toggles_json:
                self.__feature_toggles: list[Feature] = [Feature(**item) for item in feature_toggles_json]

    def is_enabled(self, feature: ProductFeature) -> bool:
        is_enabled = False
        if self.__feature_toggles:
            is_enabled = next((item.enabled for item in self.__feature_toggles if item.feature == feature), False)
        return is_enabled
