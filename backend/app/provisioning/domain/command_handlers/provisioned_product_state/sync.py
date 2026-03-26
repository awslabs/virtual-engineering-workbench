import logging

from app.provisioning.domain.aggregates import provisioned_product_state_sync_aggregate
from app.provisioning.domain.aggregates.provisioned_product_state_sync_aggregate import (
    PROVISIONED_PRODUCT_SYNC_PROCESS_NAME,
)
from app.provisioning.domain.commands.provisioned_product_state import sync_provisioned_product_state_command
from app.provisioning.domain.ports import (
    instance_management_service,
    products_service,
    provisioned_products_query_service,
)
from app.shared.ddd import aggregate


def handle(
    command: sync_provisioned_product_state_command.SyncProvisionedProductStateCommand,
    publisher: aggregate.AggregatePublisher,
    logger: logging.Logger,
    pp_qry_srv: provisioned_products_query_service.ProvisionedProductsQueryService,
    products_srv: products_service.ProductsService,
    instance_mgmt_srv: instance_management_service.InstanceManagementService,
):
    for provisioned_product_ent in pp_qry_srv.get_all_provisioned_products():

        sync_aggregate = provisioned_product_state_sync_aggregate.ProvisionedProductStateSyncAggregate(
            logger=logger,
            pp_ent=provisioned_product_ent,
            sc_pp=(
                products_srv.get_provisioned_product_details(
                    provisioned_product_id=provisioned_product_ent.scProvisionedProductId,
                    user_id=PROVISIONED_PRODUCT_SYNC_PROCESS_NAME,
                    aws_account_id=provisioned_product_ent.awsAccountId,
                    region=provisioned_product_ent.region,
                )
                if provisioned_product_ent.scProvisionedProductId
                else None
            ),
        )

        sync_aggregate.sync(
            products_srv=products_srv,
            instance_mgmt_srv=instance_mgmt_srv,
        )

        publisher.publish(sync_aggregate)
