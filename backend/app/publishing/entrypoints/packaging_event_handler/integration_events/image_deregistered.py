from pydantic import BaseModel, Field


class ImageDeregistered(BaseModel):
    event_name: str = Field("ImageDeregistered", alias="eventName", const=True)
    ami_id: str = Field(..., alias="amiId")
