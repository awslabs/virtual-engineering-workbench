from typing import Literal

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class RecommendedVersionSet(message_bus.Message):
    event_name: Literal["RecommendedVersionSet"] = Field("RecommendedVersionSet", alias="eventName")
    project_id: str = Field(..., alias="projectId")
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    model_config = ConfigDict(populate_by_name=True)
