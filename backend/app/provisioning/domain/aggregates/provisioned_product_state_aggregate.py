import logging
from datetime import datetime, timezone

from app.provisioning.domain.aggregates.internal import provisioning_helpers
from app.provisioning.domain.aggregates.state import factory
from app.provisioning.domain.commands.provisioned_product_state import (
    complete_provisioned_product_start_command,
    complete_provisioned_product_stop_command,
    initiate_provisioned_product_start_command,
    initiate_provisioned_product_stop_command,
    start_provisioned_product_command,
    stop_provisioned_product_command,
)
from app.provisioning.domain.events.provisioned_product_state import (
    provisioned_product_start_initiated,
    provisioned_product_stop_initiated,
)
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import product_status, provisioned_product
from app.provisioning.domain.ports import (
    container_management_service,
    instance_management_service,
    parameter_service,
)
from app.provisioning.domain.value_objects import (
    project_id_value_object,
    user_id_value_object,
    user_role_value_object,
)
from app.shared.ddd import aggregate
from app.shared.middleware.authorization import VirtualWorkbenchRoles

PROVISIONED_PRODUCT_BATCH_STOP_PROCESS_NAME = "VEWProvisioningBCBatchStop"


class ProvisionedProductStateAggregate(aggregate.Aggregate):
    def __init__(
        self,
        logger: logging.Logger,
        provisioned_product: provisioned_product.ProvisionedProduct | None = None,
    ):
        super().__init__()
        self._logger = logger
        if provisioned_product is None:
            raise domain_exception.DomainException("No virtual target has been found")
        self._provisioned_product = provisioned_product.copy(deep=True)
        self._original_provisioned_product = provisioned_product.copy(deep=True)

    def initiate_stop_instance(
        self,
        command: initiate_provisioned_product_stop_command.InitiateProvisionedProductStopCommand,
    ):
        """
        Initiates the stop of the underlying workbench EC2 instance when in a running state.
        """
        if command.user_id.type == user_id_value_object.UserIdType.User:
            self.__raise_if_not(
                project_id=command.project_id,
                user_id=command.user_id,
                user_roles=command.user_roles,
            )
        elif command.user_id.type == user_id_value_object.UserIdType.Service:
            self.__raise_if_not(project_id=command.project_id)
        else:
            raise domain_exception.DomainException("Invalid user id type")

        self._provisioned_product.status = product_status.ProductStatus.Stopping
        self._provisioned_product.lastUpdatedBy = command.user_id.value
        self._publish(
            provisioned_product_stop_initiated.ProvisionedProductStopInitiated(
                provisionedProductId=command.provisioned_product_id.value
            )
        )

    def stop_instance(
        self,
        command: stop_provisioned_product_command.StopProvisionedProductCommand,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        container_mgmt_srv: container_management_service.ContainerManagementService,
    ):
        """
        Stops the underlying workbench Container/EC2 instance when in running state.
        """
        stop_handler = factory.get_handler_factory(
            product_type=self._provisioned_product.provisionedProductType,
            container_mgmt_srv=container_mgmt_srv,
            instance_mgmt_srv=instance_mgmt_srv,
            logger=self._logger,
        ).get_stop_handler()

        if event := stop_handler.process(self._provisioned_product):
            self._publish(event)

    def complete_stop_instance(
        self,
        command: complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        container_mgmt_srv: container_management_service.ContainerManagementService,
    ):
        """
        Completes the stop of the underlying workbench EC2 instance when in a running state.
        """
        complete_stop_handler = factory.get_handler_factory(
            product_type=self._provisioned_product.provisionedProductType,
            container_mgmt_srv=container_mgmt_srv,
            instance_mgmt_srv=instance_mgmt_srv,
            logger=self._logger,
        ).get_complete_stop_handler()

        if event := complete_stop_handler.process(self._provisioned_product):
            self._publish(event)

    def initiate_start_instance(
        self,
        command: initiate_provisioned_product_start_command.InitiateProvisionedProductStartCommand,
    ):
        """
        Initiates the start of the underlying workbench EC2 instance when in a stopped state.
        """
        if command.user_id.type == user_id_value_object.UserIdType.User:
            self.__raise_if_not(project_id=command.project_id, user_id=command.user_id)
        elif command.user_id.type == user_id_value_object.UserIdType.Service:
            self.__raise_if_not(project_id=command.project_id)
        else:
            raise domain_exception.DomainException("Invalid user id type")

        self._provisioned_product.status = product_status.ProductStatus.Starting
        self._provisioned_product.lastUpdatedBy = command.user_id.value
        self._publish(
            provisioned_product_start_initiated.ProvisionedProductStartInitiated(
                provisionedProductId=command.provisioned_product_id.value,
                userIpAddress=command.user_ip_address.value,
            )
        )

    def start_instance(
        self,
        command: start_provisioned_product_command.StartProvisionedProductCommand,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        container_mgmt_srv: container_management_service.ContainerManagementService,
        parameter_srv: parameter_service.ParameterService,
        spoke_account_vpc_id_param_name: str,
        authorize_user_ip_address_param_value: bool,
    ):
        """
        Starts the underlying workbench EC2/Container instance when in a stopped state.
        """
        if authorize_user_ip_address_param_value:
            provisioning_helpers.authorize_user_ip_address(
                instance_mgmt_srv=instance_mgmt_srv,
                parameter_srv=parameter_srv,
                user_id=self._provisioned_product.createdBy,
                aws_account_id=self._provisioned_product.awsAccountId,
                region=self._provisioned_product.region,
                ip_address=f"{command.user_ip_address.value}/32",
                spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
            )

        start_handler = factory.get_handler_factory(
            product_type=self._provisioned_product.provisionedProductType,
            container_mgmt_srv=container_mgmt_srv,
            instance_mgmt_srv=instance_mgmt_srv,
            logger=self._logger,
        ).get_start_handler()

        if event := start_handler.process(self._provisioned_product):
            self._publish(event)

    def complete_start_instance(
        self,
        command: complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        container_mgmt_srv: container_management_service.ContainerManagementService,
    ):
        """
        Completes the start of the underlying workbench Container/EC2 instance when in a stopped state.
        """
        complete_start_handler = factory.get_handler_factory(
            product_type=self._provisioned_product.provisionedProductType,
            container_mgmt_srv=container_mgmt_srv,
            instance_mgmt_srv=instance_mgmt_srv,
            logger=self._logger,
        ).get_complete_start_handler()

        if event := complete_start_handler.process(self._provisioned_product):
            self._publish(event)

    def __is_user_owner(self, user_id: user_id_value_object.UserIdValueObject | None = None) -> bool:
        return user_id and self._provisioned_product.userId.upper().strip() == user_id.value.upper().strip()

    def __is_user_admin_or_program_owner(
        self, user_roles: list[user_role_value_object.UserRoleValueObject] | None = None
    ) -> bool:
        return user_roles and any(
            [item.value in [VirtualWorkbenchRoles.Admin, VirtualWorkbenchRoles.ProgramOwner] for item in user_roles]
        )

    def __is_user_batch_process(self, user_id: user_id_value_object.UserIdValueObject | None = None) -> bool:
        return user_id and user_id.value == PROVISIONED_PRODUCT_BATCH_STOP_PROCESS_NAME

    def __raise_if_not(
        self,
        project_id: project_id_value_object.ProjectIdValueObject | None = None,
        user_id: user_id_value_object.UserIdValueObject | None = None,
        user_roles: list[user_role_value_object.UserRoleValueObject] | None = None,
    ):
        if project_id and project_id.value != self._provisioned_product.projectId:
            raise domain_exception.DomainException(
                "Provided project ID is different from the provisioned product project ID"
            )

        # raise exception only when user is not owner or role is not admin
        if (
            user_id
            and not self.__is_user_owner(user_id=user_id)
            and not self.__is_user_admin_or_program_owner(user_roles=user_roles)
            and not self.__is_user_batch_process(user_id=user_id)
        ):
            raise domain_exception.DomainException("User is not allowed to modify the requested provisioned product.")

    def _repository_actions(self):
        self._provisioned_product.lastUpdateDate = datetime.now(timezone.utc).isoformat()

        self._pending_updates.append(
            lambda uow: uow.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey,
                provisioned_product.ProvisionedProduct,
            ).update_entity(
                pk=provisioned_product.ProvisionedProductPrimaryKey(
                    projectId=self._provisioned_product.projectId,
                    provisionedProductId=self._provisioned_product.provisionedProductId,
                ),
                entity=self._provisioned_product,
            )
        )
        self._original_provisioned_product = self._provisioned_product.copy(deep=True)
