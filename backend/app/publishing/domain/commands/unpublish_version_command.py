from app.publishing.domain.value_objects import (
    aws_account_id_value_object,
    product_id_value_object,
    version_id_value_object,
)
from app.shared.adapters.message_bus import command_bus


class UnpublishVersionCommand(command_bus.Command):
    productId: product_id_value_object.ProductIdValueObject
    versionId: version_id_value_object.VersionIdValueObject
    awsAccountId: aws_account_id_value_object.AWSAccountIDValueObject
