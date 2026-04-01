from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.publishing.domain.value_objects import (
    ami_id_value_object,
    aws_account_id_value_object,
    event_name_value_object,
    product_id_value_object,
    product_type_value_object,
    version_id_value_object,
)


class SucceedAmiSharingCommand(BaseModel):
    productId: product_id_value_object.ProductIdValueObject
    versionId: version_id_value_object.VersionIdValueObject
    awsAccountId: aws_account_id_value_object.AWSAccountIDValueObject
    copiedAmiId: Optional[ami_id_value_object.AmiIdValueObject] = None
    previousEventName: event_name_value_object.EventNameValueObject
    oldVersionId: Optional[str] = None
    productType: product_type_value_object.ProductTypeValueObject
    model_config = ConfigDict(arbitrary_types_allowed=True)
