from pydantic import BaseModel

from app.publishing.domain.value_objects import ami_id_value_object, region_value_object


class CopyAmiCommand(BaseModel):
    originalAmiId: ami_id_value_object.AmiIdValueObject
    region: region_value_object.RegionValueObject

    class Config:
        arbitrary_types_allowed = True
