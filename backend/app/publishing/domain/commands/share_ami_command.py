from pydantic import BaseModel

from app.publishing.domain.value_objects import ami_id_value_object, aws_account_id_value_object, region_value_object


class ShareAmiCommand(BaseModel):
    originalAmiId: ami_id_value_object.AmiIdValueObject
    copiedAmiId: ami_id_value_object.AmiIdValueObject
    region: region_value_object.RegionValueObject
    awsAccountId: aws_account_id_value_object.AWSAccountIDValueObject

    class Config:
        arbitrary_types_allowed = True
