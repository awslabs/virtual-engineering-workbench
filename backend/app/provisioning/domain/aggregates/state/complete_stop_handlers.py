import abc
import logging

from app.provisioning.domain.aggregates.state import handler
from app.provisioning.domain.events.product_provisioning import (
    provisioned_product_stop_for_upgrade_failed,
    provisioned_product_stopped_for_upgrade,
)
from app.provisioning.domain.events.provisioned_product_state import (
    provisioned_product_stop_failed,
    provisioned_product_stopped,
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
        stop_allowed_statuses = {
            product_status.ProductStatus.Running,
            product_status.ProductStatus.Stopped,
            product_status.ProductStatus.Starting,
            product_status.ProductStatus.Stopping,
            product_status.ProductStatus.Updating,
        }

        if provisioned_product.status not in stop_allowed_statuses:
            self.__logger.warning(
                {
                    "provisionedProductId": provisioned_product.provisionedProductId,
                    "provisionedProductStatus": provisioned_product.status,
                    "message": f"Provisioned product can only be stopped when it is in one of the {stop_allowed_statuses} statuses.",
                }
            )
            return

        return self._process_inner(provisioned_product=provisioned_product)

    @abc.abstractmethod
    def _process_inner(
        self, provisioned_product: provisioned_product.ProvisionedProduct
    ) -> message_bus.Message | None: ...


class ContainerHandler(BaseInstanceHandler):

    def __init__(
        self, container_mgmt_srv: container_management_service.ContainerManagementService, logger: logging.Logger
    ):
        super().__init__(logger=logger)

        self.__container_mgmt_srv = container_mgmt_srv

    def _process_inner(self, provisioned_product: provisioned_product.ProvisionedProduct) -> message_bus.Message | None:
        status = self.__container_mgmt_srv.get_container_details(
            aws_account_id=provisioned_product.awsAccountId,
            cluster_name=provisioned_product.containerClusterName,
            region=provisioned_product.region,
            service_name=provisioned_product.containerServiceName,
            user_id=provisioned_product.userId,
        )
        # if the task doesn't exist anymore lets mark it as stopped
        container_state = product_status.TaskState(status.state.name) if status else product_status.TaskState.Stopped
        provisioned_product.status = product_status.CONTAINER_TO_PRODUCT_STATE_MAP.get(container_state)

        if container_state == product_status.TaskState.Stopped:
            return provisioned_product_stopped.ProvisionedProductStopped(
                provisionedProductId=provisioned_product.provisionedProductId
            )

        if container_state in [
            product_status.TaskState.Stopping,
            product_status.TaskState.Deprovisioning,
        ]:
            return

        return provisioned_product_stop_failed.ProvisionedProductStopFailed(
            provisionedProductId=provisioned_product.provisionedProductId
        )


class InstanceHandler(BaseInstanceHandler):

    def __init__(
        self, instance_mgmt_srv: instance_management_service.InstanceManagementService, logger: logging.Logger
    ):
        super().__init__(logger=logger)

        self.__instance_mgmt_srv = instance_mgmt_srv

    def _process_inner(self, provisioned_product: provisioned_product.ProvisionedProduct) -> message_bus.Message | None:

        status = self.__instance_mgmt_srv.get_instance_state(
            user_id=provisioned_product.createdBy,
            aws_account_id=provisioned_product.awsAccountId,
            instance_id=provisioned_product.instanceId,
            region=provisioned_product.region,
        )

        ec2_instance_state = product_status.EC2InstanceState(status)

        if (
            provisioned_product.status == product_status.ProductStatus.Updating
            and ec2_instance_state == product_status.EC2InstanceState.Stopped
        ):
            return provisioned_product_stopped_for_upgrade.ProvisionedProductStoppedForUpgrade(
                provisionedProductId=provisioned_product.provisionedProductId
            )

        if (
            provisioned_product.status == product_status.ProductStatus.Updating
            and ec2_instance_state != product_status.EC2InstanceState.Stopped
        ):
            return provisioned_product_stop_for_upgrade_failed.ProvisionedProductStopForUpgradeFailed(
                provisionedProductId=provisioned_product.provisionedProductId
            )

        if ec2_instance_state == product_status.EC2InstanceState.Stopped:
            provisioned_product.status = product_status.EC2_TO_PRODUCT_STATE_MAP.get(ec2_instance_state)
            return provisioned_product_stopped.ProvisionedProductStopped(
                provisionedProductId=provisioned_product.provisionedProductId
            )

        return provisioned_product_stop_failed.ProvisionedProductStopFailed(
            provisionedProductId=provisioned_product.provisionedProductId
        )
