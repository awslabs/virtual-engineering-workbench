import logging

from app.provisioning.domain.aggregates import provisioned_product_configuration_aggregate
from app.provisioning.domain.commands.provisioned_product_configuration import (
    start_provisioned_product_configuration_command,
)
from app.provisioning.domain.ports import provisioned_products_query_service, system_command_service
from app.shared.ddd import aggregate


def handle(
    command: start_provisioned_product_configuration_command.StartProvisionedProductConfigurationCommand,
    publisher: aggregate.AggregatePublisher,
    provisioned_products_qry_srv: provisioned_products_query_service.ProvisionedProductsQueryService,
    system_command_srv: system_command_service.SystemCommandService,
    logger: logging.Logger,
) -> None:

    provisioned_product_entity = provisioned_products_qry_srv.get_by_id(
        provisioned_product_id=command.provisioned_product_id.value,
    )

    configuration_aggregate = provisioned_product_configuration_aggregate.ProvisionedProductConfigurationAggregate(
        logger=logger, provisioned_product_entity=provisioned_product_entity
    )

    configuration_aggregate.start(command=command, system_command_srv=system_command_srv)

    publisher.publish(configuration_aggregate)
