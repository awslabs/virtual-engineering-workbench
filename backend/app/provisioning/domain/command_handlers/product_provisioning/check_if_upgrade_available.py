import logging

from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.commands.product_provisioning import check_if_upgrade_available_command
from app.provisioning.domain.ports import provisioned_products_query_service
from app.shared.ddd import aggregate


def handle(
    command: check_if_upgrade_available_command.CheckIfUpgradeAvailableCommand,
    publisher: aggregate.AggregatePublisher,
    logger: logging.Logger,
    pp_qry_srv: provisioned_products_query_service.ProvisionedProductsQueryService,
):
    for provisioned_product_ent in pp_qry_srv.get_all_provisioned_products_by_product_id(
        product_id=command.product_id.value,
        region=command.region.value,
        stage=command.stage.value,
    ):

        prov_aggregate = product_provisioning_aggregate.ProductProvisioningAggregate(
            logger=logger,
            provisioned_product_entity=provisioned_product_ent,
        )

        prov_aggregate.check_if_upgrade_available(command)

        publisher.publish(prov_aggregate)
