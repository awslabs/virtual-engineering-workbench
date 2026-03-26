from typing import List

from pydantic import BaseModel, Field


class GetPublishedAmisResponse(BaseModel):
    amis: List[str] = Field(..., title="Amis")
