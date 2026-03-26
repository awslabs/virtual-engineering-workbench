import abc
import logging
from datetime import datetime, timezone

from app.provisioning.domain.aggregates.internal import provisioning_helpers
from app.provisioning.domain.aggregates.state import handler
from app.provisioning.domain.events.provisioned_product_state import (
    provisioned_product_start_failed,
    provisioned_product_started,
)
from app.provisioning.domain.model import product_status, provisioned_product
from app.provisioning.domain.ports import (
    container_management_service,
    instance_management_service,
)
from app.shared.adapters.message_bus import message_bus


class BaseInstanceHandler(handler.Handler, abc.ABC):

    def __init__(self, logger: logging.Logger):
        self.__logger = logger

    def process(self, provisioned_product: provisioned_product.ProvisionedProduct) -> message_bus.Message | None:
        active_product_statuses = self._get_active_product_statuses()

        if provisioned_product.status not in active_product_statuses:
            self.__logger.warning(
                {
                    "provisionedProductId": provisioned_product.provisionedProductId,
                    "provisionedProductStatus": provisioned_product.status,
                    "message": f"Provisioned product can only be started when it is in one of the {active_product_statuses} statuses.",
                }
            )
            return

        self._process_inner(provisioned_product=provisioned_product)

        if provisioned_product.status == product_status.ProductStatus.Running:
            provisioned_product.startDate = datetime.now(timezone.utc).isoformat()

            return provisioned_product_started.ProvisionedProductStarted(
                provisionedProductId=provisioned_product.provisionedProductId
            )

        self.__logger.error(
            {
                "expectedRealStatus": product_status.ProductStatus.Running,
                "realStatus": provisioned_product.status,
            }
        )
        return provisioned_product_start_failed.ProvisionedProductStartFailed(
            projectId=provisioned_product.projectId,
            provisionedProductId=provisioned_product.provisionedProductId,
            productName=provisioned_product.productName,
            productType=provisioned_product.provisionedProductType,
            owner=provisioned_product.userId,
        )

    @abc.abstractmethod
    def _get_active_product_statuses(self) -> set[product_status.ProductStatus]: ...

    @abc.abstractmethod
    def _process_inner(self, provisioned_product: provisioned_product.ProvisionedProduct): ...


class ContainerHandler(BaseInstanceHandler):

    def __init__(
        self, container_mgmt_srv: container_management_service.ContainerManagementService, logger: logging.Logger
    ):
        super().__init__(logger=logger)

        self.__container_mgmt_srv = container_mgmt_srv

    def _get_active_product_statuses(self):
        return {*product_status.ACTIVE_PRODUCT_STATUSES, product_status.ProductStatus.Provisioning}

    def _process_inner(self, provisioned_product):
        container_details = self.__container_mgmt_srv.get_container_details(
            aws_account_id=provisioned_product.awsAccountId,
            cluster_name=provisioned_product.containerClusterName,
            service_name=provisioned_product.containerServiceName,
            region=provisioned_product.region,
            user_id=provisioned_product.userId,
        )
        provisioned_product.status = provisioning_helpers.map_provisioned_product_container_type_status(
            container_details
        )
        provisioned_product.privateIp = container_details.private_ip_address
        provisioned_product.containerName = container_details.name
        provisioned_product.containerTaskArn = container_details.task_arn


class InstanceHandler(BaseInstanceHandler):

    def __init__(
        self, instance_mgmt_srv: instance_management_service.InstanceManagementService, logger: logging.Logger
    ):
        super().__init__(logger=logger)

        self.__instance_mgmt_srv = instance_mgmt_srv

    def _get_active_product_statuses(self):
        return product_status.ACTIVE_PRODUCT_STATUSES

    def _process_inner(self, provisioned_product: provisioned_product.ProvisionedProduct):
        inst_details = self.__instance_mgmt_srv.get_instance_details(
            user_id=provisioned_product.createdBy,
            aws_account_id=provisioned_product.awsAccountId,
            instance_id=provisioned_product.instanceId,
            region=provisioned_product.region,
        )
        provisioned_product.status = provisioning_helpers.map_provisioned_product_instance_type_status(inst_details)
        provisioned_product.privateIp = inst_details.private_ip_address
        provisioned_product.publicIp = inst_details.public_ip_address
