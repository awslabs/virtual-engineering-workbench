from app.publishing.domain.value_objects import (
    aws_account_id_value_object,
    product_id_value_object,
    project_id_value_object,
    user_id_value_object,
    version_id_value_object,
)
from app.shared.adapters.message_bus import command_bus


class RetryVersionCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    productId: product_id_value_object.ProductIdValueObject
    versionId: version_id_value_object.VersionIdValueObject
    awsAccountIds: list[aws_account_id_value_object.AWSAccountIDValueObject]
    lastUpdatedBy: user_id_value_object.UserIdValueObject
