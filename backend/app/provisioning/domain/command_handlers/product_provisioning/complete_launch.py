import logging

from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.commands.product_provisioning import complete_product_launch_command
from app.provisioning.domain.ports import (
    container_management_service,
    instance_management_service,
    products_query_service,
    products_service,
    provisioned_products_query_service,
    versions_query_service,
)
from app.shared.ddd import aggregate


def handle(
    command: complete_product_launch_command.CompleteProductLaunchCommand,
    publisher: aggregate.AggregatePublisher,
    provisioned_products_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
    products_srv: products_service.ProductsService,
    products_qry_srv: products_query_service.ProductsQueryService,
    versions_qry_srv: versions_query_service.VersionsQueryService,
    instance_mgmt_srv: instance_management_service.InstanceManagementService,
    container_mgmt_srv: container_management_service.ContainerManagementService,
    logger: logging.Logger,
):
    provisioned_product_entity = provisioned_products_qs.get_by_id(command.provisioned_product_id.value)

    product_entity = products_qry_srv.get_product(
        project_id=provisioned_product_entity.projectId, product_id=provisioned_product_entity.productId
    )

    vt_provisioning = product_provisioning_aggregate.ProductProvisioningAggregate(
        logger=logger, provisioned_product_entity=provisioned_product_entity, product_entity=product_entity
    )

    vt_provisioning.complete_launch(
        command=command,
        products_srv=products_srv,
        instance_mgmt_srv=instance_mgmt_srv,
        container_mgmt_srv=container_mgmt_srv,
        versions_qs=versions_qry_srv,
    )

    publisher.publish(vt_provisioning)
