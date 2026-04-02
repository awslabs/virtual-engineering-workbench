from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.publishing.domain.value_objects import (
    aws_account_id_value_object,
    event_name_value_object,
    product_id_value_object,
    version_id_value_object,
)


class PublishVersionCommand(BaseModel):
    productId: product_id_value_object.ProductIdValueObject
    versionId: version_id_value_object.VersionIdValueObject
    awsAccountId: aws_account_id_value_object.AWSAccountIDValueObject
    previousEventName: event_name_value_object.EventNameValueObject
    oldVersionId: Optional[str] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)
