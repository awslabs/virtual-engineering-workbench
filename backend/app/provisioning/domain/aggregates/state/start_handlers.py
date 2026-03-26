import logging

from app.provisioning.domain.aggregates.state import handler
from app.provisioning.domain.events.provisioned_product_state import (
    provisioned_product_instance_started,
    provisioned_product_start_failed,
    provisioned_product_started,
)
from app.provisioning.domain.exceptions import insufficient_capacity_exception
from app.provisioning.domain.model import product_status, provisioned_product
from app.provisioning.domain.ports import (
    container_management_service,
    instance_management_service,
)
from app.shared.adapters.message_bus import message_bus


class ContainerHandler(handler.Handler):

    def __init__(
        self, container_mgmt_srv: container_management_service.ContainerManagementService, logger: logging.Logger
    ):
        self.__container_mgmt_srv = container_mgmt_srv
        self.__logger = logger

    def process(self, provisioned_product: provisioned_product.ProvisionedProduct) -> message_bus.Message | None:
        self.__logger.debug(
            {
                "message": "Starting container",
                "provisionedProductId": provisioned_product.provisionedProductId,
                "provisionedProductType": provisioned_product.provisionedProductType,
            }
        )
        status = self.__container_mgmt_srv.get_container_status(
            aws_account_id=provisioned_product.awsAccountId,
            cluster_name=provisioned_product.containerClusterName,
            service_name=provisioned_product.provisionedProductId,
            region=provisioned_product.region,
            user_id=provisioned_product.userId,
        )
        self.__logger.debug(
            {
                "message": "Container status",
                "provisionedProductId": provisioned_product.provisionedProductId,
                "provisionedProductType": provisioned_product.provisionedProductType,
                "status": status,
            }
        )
        if product_status.CONTAINER_TO_PRODUCT_STATE_MAP.get(status.name) == product_status.ProductStatus.Stopped:
            try:
                self.__container_mgmt_srv.start_container(
                    aws_account_id=provisioned_product.awsAccountId,
                    service_name=provisioned_product.containerServiceName,
                    cluster_name=provisioned_product.containerClusterName,
                    region=provisioned_product.region,
                    user_id=provisioned_product.userId,
                )
            except insufficient_capacity_exception.InsufficientCapacityException:
                current_state = product_status.TaskState.Stopped
                provisioned_product.status = product_status.CONTAINER_TO_PRODUCT_STATE_MAP.get(current_state)
                self.__logger.exception(provisioned_product_start_failed.StartFailedReason.InsufficientClusterCapacity)

                return provisioned_product_start_failed.ProvisionedProductStartFailed(
                    projectId=provisioned_product.projectId,
                    provisionedProductId=provisioned_product.provisionedProductId,
                    productName=provisioned_product.productName,
                    productType=provisioned_product.provisionedProductType,
                    owner=provisioned_product.userId,
                    reason=provisioned_product_start_failed.StartFailedReason.InsufficientClusterCapacity,
                )

            current_state = self.__container_mgmt_srv.get_container_details(
                aws_account_id=provisioned_product.awsAccountId,
                cluster_name=provisioned_product.containerClusterName,
                service_name=provisioned_product.containerServiceName,
                region=provisioned_product.region,
                user_id=provisioned_product.userId,
            )
            if current_state:
                ecs_instance_state = product_status.TaskState(current_state.state.name)
            else:
                self.__logger.info("No running task found for the specified service.")
                return

            self.__logger.debug(
                {
                    "message": "Container status",
                    "provisionedProductId": provisioned_product.provisionedProductId,
                    "provisionedProductType": provisioned_product.provisionedProductType,
                    "status": ecs_instance_state,
                }
            )

            provisioned_product.status = product_status.CONTAINER_TO_PRODUCT_STATE_MAP.get(ecs_instance_state)
            self.__logger.debug(
                {
                    "message": "Container status",
                    "provisionedProductId": provisioned_product.provisionedProductId,
                    "provisionedProductType": provisioned_product.provisionedProductType,
                    "status": provisioned_product.status,
                }
            )
            return provisioned_product_started.ProvisionedProductStarted(
                provisionedProductId=provisioned_product.provisionedProductId
            )


class InstanceHandler(handler.Handler):

    def __init__(
        self, instance_mgmt_srv: instance_management_service.InstanceManagementService, logger: logging.Logger
    ):
        self.__instance_mgmt_srv = instance_mgmt_srv
        self.__logger = logger

    def process(self, provisioned_product: provisioned_product.ProvisionedProduct) -> message_bus.Message | None:
        status = self.__instance_mgmt_srv.get_instance_state(
            user_id=provisioned_product.createdBy,
            aws_account_id=provisioned_product.awsAccountId,
            instance_id=provisioned_product.instanceId,
            region=provisioned_product.region,
        )
        ec2_instance_state = product_status.EC2InstanceState(status)

        if ec2_instance_state == product_status.EC2InstanceState.Running:
            provisioned_product.status = product_status.EC2_TO_PRODUCT_STATE_MAP.get(ec2_instance_state)
            return provisioned_product_started.ProvisionedProductStarted(
                provisionedProductId=provisioned_product.provisionedProductId
            )

        reason = None

        try:
            current_state = self.__instance_mgmt_srv.start_instance(
                user_id=provisioned_product.createdBy,
                aws_account_id=provisioned_product.awsAccountId,
                instance_id=provisioned_product.instanceId,
                region=provisioned_product.region,
            )

        except insufficient_capacity_exception.InsufficientCapacityException as error:
            current_state = product_status.EC2InstanceState.Stopped
            reason = provisioned_product_start_failed.StartFailedReason.InsufficientInstanceCapacity
            self.__logger.error(error)
            provisioned_product.statusReason = str(error)

        current_ec2_instance_state = product_status.EC2InstanceState(current_state)
        provisioned_product.status = product_status.EC2_TO_PRODUCT_STATE_MAP.get(current_ec2_instance_state)

        if current_ec2_instance_state != product_status.EC2InstanceState.Pending:
            return provisioned_product_start_failed.ProvisionedProductStartFailed(
                projectId=provisioned_product.projectId,
                provisionedProductId=provisioned_product.provisionedProductId,
                productName=provisioned_product.productName,
                productType=provisioned_product.provisionedProductType,
                owner=provisioned_product.userId,
                reason=reason,
            )
        else:
            return provisioned_product_instance_started.ProvisionedProductInstanceStarted(
                provisionedProductId=provisioned_product.provisionedProductId
            )
