from pydantic import BaseModel

from app.publishing.domain.value_objects import (
    aws_account_id_value_object,
    product_id_value_object,
    version_id_value_object,
)


class FailAmiSharingCommand(BaseModel):
    productId: product_id_value_object.ProductIdValueObject
    versionId: version_id_value_object.VersionIdValueObject
    awsAccountId: aws_account_id_value_object.AWSAccountIDValueObject

    class Config:
        arbitrary_types_allowed = True
