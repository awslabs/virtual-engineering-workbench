import logging

from app.provisioning.domain.aggregates import provisioned_product_configuration_aggregate
from app.provisioning.domain.commands.provisioned_product_configuration import (
    complete_provisioned_product_configuration_command,
)
from app.provisioning.domain.ports import (
    container_management_service,
    instance_management_service,
    provisioned_products_query_service,
)
from app.shared.ddd import aggregate


def handle(
    command: complete_provisioned_product_configuration_command.CompleteProvisionedProductConfigurationCommand,
    publisher: aggregate.AggregatePublisher,
    provisioned_products_qry_srv: provisioned_products_query_service.ProvisionedProductsQueryService,
    instance_mgmt_srv: instance_management_service.InstanceManagementService,
    container_mgmt_srv: container_management_service.ContainerManagementService,
    logger: logging.Logger,
) -> None:

    provisioned_product_entity = provisioned_products_qry_srv.get_by_id(
        provisioned_product_id=command.provisioned_product_id.value,
    )

    configuration_aggregate = provisioned_product_configuration_aggregate.ProvisionedProductConfigurationAggregate(
        logger=logger, provisioned_product_entity=provisioned_product_entity
    )

    configuration_aggregate.complete(
        command=command, instance_mgmt_srv=instance_mgmt_srv, container_mgmt_srv=container_mgmt_srv
    )

    publisher.publish(configuration_aggregate)
