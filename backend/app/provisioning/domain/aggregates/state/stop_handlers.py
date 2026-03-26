from app.provisioning.domain.aggregates.state import handler
from app.provisioning.domain.events.provisioned_product_state import (
    provisioned_product_instance_stopped,
    provisioned_product_stop_failed,
    provisioned_product_stopped,
)
from app.provisioning.domain.model import product_status, provisioned_product
from app.provisioning.domain.ports import (
    container_management_service,
    instance_management_service,
)
from app.shared.adapters.message_bus import message_bus


class ContainerHandler(handler.Handler):

    def __init__(self, container_mgmt_srv: container_management_service.ContainerManagementService):
        self.__container_mgmt_srv = container_mgmt_srv

    def process(self, provisioned_product: provisioned_product.ProvisionedProduct) -> message_bus.Message | None:
        status = self.__container_mgmt_srv.get_container_details(
            aws_account_id=provisioned_product.awsAccountId,
            cluster_name=provisioned_product.containerClusterName,
            service_name=provisioned_product.containerServiceName,
            region=provisioned_product.region,
            user_id=provisioned_product.userId,
        )
        state = product_status.TaskState(status.state.name)
        if state == product_status.TaskState.Stopped:
            provisioned_product.status = product_status.CONTAINER_TO_PRODUCT_STATE_MAP.get(state)
            return provisioned_product_stopped.ProvisionedProductStopped(
                provisionedProductId=provisioned_product.provisionedProductId
            )

        self.__container_mgmt_srv.stop_container(
            aws_account_id=provisioned_product.awsAccountId,
            cluster_name=provisioned_product.containerClusterName,
            service_name=provisioned_product.containerServiceName,
            region=provisioned_product.region,
            user_id=provisioned_product.userId,
        )
        current_state = self.__container_mgmt_srv.get_container_details(
            aws_account_id=provisioned_product.awsAccountId,
            cluster_name=provisioned_product.containerClusterName,
            service_name=provisioned_product.containerServiceName,
            region=provisioned_product.region,
            user_id=provisioned_product.userId,
        )
        current_container_instance_state = product_status.TaskState(current_state.state.name)
        provisioned_product.status = product_status.CONTAINER_TO_PRODUCT_STATE_MAP.get(current_container_instance_state)
        if current_container_instance_state not in [
            product_status.TaskState.Stopping,
            product_status.TaskState.Stopped,
            product_status.TaskState.Deprovisioning,
        ]:
            return provisioned_product_stop_failed.ProvisionedProductStopFailed(
                provisionedProductId=provisioned_product.provisionedProductId
            )
        else:
            return provisioned_product_instance_stopped.ProvisionedProductInstanceStopped(
                provisionedProductId=provisioned_product.provisionedProductId
            )


class InstanceHandler(handler.Handler):

    def __init__(self, instance_mgmt_srv: instance_management_service.InstanceManagementService):
        self.__instance_mgmt_srv = instance_mgmt_srv

    def process(self, provisioned_product: provisioned_product.ProvisionedProduct) -> message_bus.Message | None:
        status = self.__instance_mgmt_srv.get_instance_state(
            user_id=provisioned_product.createdBy,
            aws_account_id=provisioned_product.awsAccountId,
            instance_id=provisioned_product.instanceId,
            region=provisioned_product.region,
        )
        ec2_instance_state = product_status.EC2InstanceState(status)

        if ec2_instance_state == product_status.EC2InstanceState.Stopped:
            provisioned_product.status = product_status.EC2_TO_PRODUCT_STATE_MAP.get(ec2_instance_state)
            return provisioned_product_stopped.ProvisionedProductStopped(
                provisionedProductId=provisioned_product.provisionedProductId
            )

        current_state = self.__instance_mgmt_srv.stop_instance(
            user_id=provisioned_product.createdBy,
            aws_account_id=provisioned_product.awsAccountId,
            instance_id=provisioned_product.instanceId,
            region=provisioned_product.region,
        )
        current_ec2_instance_state = product_status.EC2InstanceState(current_state)
        provisioned_product.status = product_status.EC2_TO_PRODUCT_STATE_MAP.get(current_ec2_instance_state)
        if current_ec2_instance_state != product_status.EC2InstanceState.Stopping:
            return provisioned_product_stop_failed.ProvisionedProductStopFailed(
                provisionedProductId=provisioned_product.provisionedProductId
            )
        else:
            return provisioned_product_instance_stopped.ProvisionedProductInstanceStopped(
                provisionedProductId=provisioned_product.provisionedProductId
            )
