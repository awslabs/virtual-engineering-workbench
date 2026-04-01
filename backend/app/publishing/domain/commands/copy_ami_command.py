from pydantic import BaseModel, ConfigDict

from app.publishing.domain.value_objects import ami_id_value_object, region_value_object


class CopyAmiCommand(BaseModel):
    originalAmiId: ami_id_value_object.AmiIdValueObject
    region: region_value_object.RegionValueObject
    model_config = ConfigDict(arbitrary_types_allowed=True)
