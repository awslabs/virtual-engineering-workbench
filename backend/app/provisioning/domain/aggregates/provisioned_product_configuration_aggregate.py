import logging
from datetime import datetime, timezone

from app.provisioning.domain.aggregates.internal import provisioning_helpers
from app.provisioning.domain.commands.provisioned_product_configuration import (
    complete_provisioned_product_configuration_command,
    fail_provisioned_product_configuration_command,
    start_provisioned_product_configuration_command,
)
from app.provisioning.domain.events.product_provisioning import product_launched
from app.provisioning.domain.events.provisioned_product_configuration import (
    provisioned_product_configuration_failed,
    provisioned_product_configuration_started,
)
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import product_status, provisioned_product
from app.provisioning.domain.ports import (
    container_management_service,
    instance_management_service,
    system_command_service,
)
from app.provisioning.domain.value_objects import provisioned_product_id_value_object
from app.shared.ddd import aggregate


class ProvisionedProductConfigurationAggregate(aggregate.Aggregate):
    def __init__(
        self,
        logger: logging.Logger,
        provisioned_product_entity: provisioned_product.ProvisionedProduct | None = None,
    ):
        super().__init__()
        self._logger = logger
        self._provisioned_product = provisioned_product_entity.copy(deep=True) if provisioned_product_entity else None
        self._original_provisioned_product = (
            provisioned_product_entity.copy(deep=True) if provisioned_product_entity else None
        )

    def _repository_actions(self):
        """Logic to persist the aggregate state in the database

        This function is called by the AggregatePublisher class when it wants to store the data in DB.
        Handles create and update entity scenarios.
        """
        if self._provisioned_product.dict() != self._original_provisioned_product.dict():
            # Update
            self._provisioned_product.lastUpdateDate = datetime.now(timezone.utc).isoformat()

            self._pending_updates.append(
                lambda uow: uow.get_repository(
                    provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
                ).update_entity(
                    pk=provisioned_product.ProvisionedProductPrimaryKey(
                        projectId=self._provisioned_product.projectId,
                        provisionedProductId=self._provisioned_product.provisionedProductId,
                    ),
                    entity=self._provisioned_product,
                )
            )
            self._original_provisioned_product = self._provisioned_product.copy(deep=True)

    def start(
        self,
        command: start_provisioned_product_configuration_command.StartProvisionedProductConfigurationCommand,
        system_command_srv: system_command_service.SystemCommandService,
    ):
        """
        Second step in provisioned product configuration.
        This command:
            - Updates the provisioned product status
            - Runs the configuration document asynchronously
            - Publishes the ProvisionedProductConfigurationStarted event
        """

        self.__raise_if_entity_not_loaded_for(
            provisioned_product_id=command.provisioned_product_id,
        )

        self.__raise_if_no_additional_configurations()

        # Update status
        self._provisioned_product.status = product_status.ProductStatus.ConfigurationInProgress

        # Run the document
        for config in self._provisioned_product.additionalConfigurations:
            config.run_id = system_command_srv.run_document(
                aws_account_id=self._provisioned_product.awsAccountId,
                region=self._provisioned_product.region,
                user_id=self._provisioned_product.userId,
                provisioned_product_configuration_type=config.type,
                instance_id=self._provisioned_product.instanceId,
                parameters=config.parameters,
            )

        # Publish event
        self._publish(
            provisioned_product_configuration_started.ProvisionedProductConfigurationStarted(
                provisionedProductId=command.provisioned_product_id.value,
            )
        )

    def complete(
        self,
        command: complete_provisioned_product_configuration_command.CompleteProvisionedProductConfigurationCommand,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        container_mgmt_srv: container_management_service.ContainerManagementService,
    ):
        """
        Completes the provisioned product configuration.
        This command:
            - Updates the provisioned product status
            - Publishes the ProductLaunched event
        """

        self.__raise_if_entity_not_loaded_for(
            provisioned_product_id=command.provisioned_product_id,
        )
        match self._provisioned_product.provisionedProductType:
            case p if p in provisioned_product.PRODUCT_CONTAINER_TYPES:
                status = container_mgmt_srv.get_container_details(
                    aws_account_id=self._provisioned_product.awsAccountId,
                    cluster_name=self._provisioned_product.containerClusterName,
                    region=self._provisioned_product.region,
                    service_name=self._provisioned_product.containerServiceName,
                    user_id=self._provisioned_product.userId,
                )
                container_state = product_status.TaskState(status.state.name)
                self._provisioned_product.status = product_status.CONTAINER_TO_PRODUCT_STATE_MAP.get(container_state)

                # Publish event
                self._publish(
                    product_launched.ProductLaunched(
                        projectId=self._provisioned_product.projectId,
                        provisionedProductId=self._provisioned_product.provisionedProductId,
                        productName=self._provisioned_product.productName,
                        productType=self._provisioned_product.provisionedProductType,
                        owner=self._provisioned_product.userId,
                        privateIP=self._provisioned_product.privateIp,
                        service_id=self._provisioned_product.containerServiceName,
                        awsAccountId=self._provisioned_product.awsAccountId,
                        region=self._provisioned_product.region,
                    )
                )
                pass
            case p if p in provisioned_product.PRODUCT_INSTANCE_TYPES:
                # Update status
                ent_details = instance_mgmt_srv.get_instance_details(
                    user_id=self._provisioned_product.createdBy,
                    aws_account_id=self._provisioned_product.awsAccountId,
                    region=self._provisioned_product.region,
                    instance_id=self._provisioned_product.instanceId,
                )
                self._provisioned_product.status = provisioning_helpers.map_provisioned_product_instance_type_status(
                    ent_details
                )

                # Publish event
                self._publish(
                    product_launched.ProductLaunched(
                        projectId=self._provisioned_product.projectId,
                        provisionedProductId=self._provisioned_product.provisionedProductId,
                        productName=self._provisioned_product.productName,
                        productType=self._provisioned_product.provisionedProductType,
                        owner=self._provisioned_product.userId,
                        instanceId=self._provisioned_product.instanceId,
                        privateIP=self._provisioned_product.privateIp,
                        awsAccountId=self._provisioned_product.awsAccountId,
                        region=self._provisioned_product.region,
                    )
                )

    def fail(
        self,
        command: fail_provisioned_product_configuration_command.FailProvisionedProductConfigurationCommand,
    ):
        """
        Fail the provisioned product configuration.
        This command:
            - Updates the provisioned product status
        """

        self.__raise_if_entity_not_loaded_for(
            provisioned_product_id=command.provisioned_product_id,
        )

        self._provisioned_product.status = product_status.ProductStatus.ConfigurationFailed
        self._provisioned_product.statusReason = command.reason.value
        self._publish(
            provisioned_product_configuration_failed.ProvisionedProductConfigurationFailed(
                provisionedProductId=self._provisioned_product.provisionedProductId,
            )
        )

    def __raise_if_entity_not_loaded_for(
        self,
        provisioned_product_id: provisioned_product_id_value_object.ProvisionedProductIdValueObject | None = None,
    ):
        if not self._provisioned_product:
            raise domain_exception.DomainException(f"Provisioned product {provisioned_product_id} does not exist")

        if provisioned_product_id and self._provisioned_product.provisionedProductId != provisioned_product_id.value:
            raise domain_exception.DomainException(
                f"Trying to change entity with ID {provisioned_product_id.value} but aggregate is loaded for {self._provisioned_product.provisionedProductId}"
            )

    def __raise_if_no_additional_configurations(self):
        if not self._provisioned_product.additionalConfigurations:
            raise domain_exception.DomainException(
                f"Provisioned product {self._provisioned_product.provisionedProductId} has no additional configurations set"
            )
