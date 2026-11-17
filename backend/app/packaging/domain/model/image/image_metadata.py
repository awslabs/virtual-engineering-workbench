from pydantic import BaseModel, Field


class ImageMetadata(BaseModel):
    imageBuildVersionArn: str = Field(..., title="ImageBuildVersionArn")
    snapshotIds: list[str] = Field(default_factory=list, title="SnapshotIds")
