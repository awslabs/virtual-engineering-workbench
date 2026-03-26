import typing

from mypy_boto3_dynamodb import service_resource, type_defs

from app.provisioning.adapters.repository import dynamo_entity_config
from app.provisioning.domain.ports import provisioned_products_query_service
from app.shared.adapters.unit_of_work_v2 import unit_of_work

MAX_TRANSACT_WRITE_ITEM_SIZE = 100


def migrations_config(provisioned_products_qs: provisioned_products_query_service.ProvisionedProductsQueryService):

    def provisioned_product_new_attributes_qpk_4_and_sequence_no(table: service_resource.Table):
        """001.ProvisionedProduct_set_QPK_4_and_SequenceNo

        Adds QPK_4 and sequenceNo attributes to all provisioned_product entities.
        Has a condition to ensure that the status and QPK_4 stay in a consistent state.
        If the condition fails, Lambda function (async) or CloudFormation (provisioned concurrency) will retry.
        """

        for transaction in __provisioned_product_new_attributes_qpk_4_and_sequence_no_transactions(
            table_name=table.table_name
        ):
            table.meta.client.transact_write_items(
                TransactItems=transaction,
            )

    def __provisioned_product_new_attributes_qpk_4_and_sequence_no_transactions(
        table_name: str,
    ) -> typing.Iterator[list[type_defs.TransactWriteItemTypeDef]]:
        transaction: list[type_defs.TransactWriteItemTypeDef] = []
        for provisioned_product in provisioned_products_qs.get_all_provisioned_products():
            transaction.append(
                {
                    "Update": {
                        "TableName": table_name,
                        "Key": {
                            "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{provisioned_product.projectId}",
                            "SK": f"{dynamo_entity_config.DBPrefix.PROVISIONED_PRODUCT}#{provisioned_product.provisionedProductId}",
                        },
                        "UpdateExpression": "SET #qpk4 = :qpk4, #seqNo = :seqNo",
                        "ExpressionAttributeNames": {
                            "#qpk4": "QPK_4",
                            "#seqNo": unit_of_work.ATTRIBUTE_NAME_SEQUENCE_NO,
                            "#status": "status",
                        },
                        "ExpressionAttributeValues": {
                            ":qpk4": f"{dynamo_entity_config.DBPrefix.PROVISIONED_PRODUCT}#{provisioned_product.status}",
                            ":seqNo": 0,
                            ":status": provisioned_product.status,
                        },
                        "ConditionExpression": "#status = :status",
                    }
                }
            )

            if len(transaction) == MAX_TRANSACT_WRITE_ITEM_SIZE:
                yield transaction
                transaction = []

        if len(transaction) > 0:
            yield transaction
            transaction = []

    return [
        (
            "001.ProvisionedProduct_set_QPK_4_and_SequenceNo",
            provisioned_product_new_attributes_qpk_4_and_sequence_no,
        ),
    ]
