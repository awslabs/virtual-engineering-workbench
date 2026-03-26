from app.provisioning.domain.model import additional_configuration
from app.provisioning.domain.ports import provisioned_products_query_service, system_command_service
from app.provisioning.domain.value_objects import provisioned_product_id_value_object


class ProvisionedProductConfigurationDomainQueryService:
    def __init__(
        self,
        provisioned_products_qry_srv: provisioned_products_query_service.ProvisionedProductsQueryService,
        system_command_srv: system_command_service.SystemCommandService,
    ) -> None:
        self._provisioned_products_qry_srv = provisioned_products_qry_srv
        self._system_command_srv = system_command_srv

    def get_provisioned_product_configuration_run_status(
        self,
        provisioned_product_id: provisioned_product_id_value_object.ProvisionedProductIdValueObject,
    ) -> tuple[additional_configuration.AdditionalConfigurationRunStatus, str]:
        provisioned_product_entity = self._provisioned_products_qry_srv.get_by_id(
            provisioned_product_id=provisioned_product_id.value,
        )

        for config in provisioned_product_entity.additionalConfigurations:
            status, reason = self._system_command_srv.get_run_status(
                aws_account_id=provisioned_product_entity.awsAccountId,
                region=provisioned_product_entity.region,
                user_id=provisioned_product_entity.userId,
                instance_id=provisioned_product_entity.instanceId,
                run_id=config.run_id,
            )
            # Return Failed if one config is failed
            # Return InProgress if one config is in progress
            if status in [
                additional_configuration.AdditionalConfigurationRunStatus.Failed,
                additional_configuration.AdditionalConfigurationRunStatus.InProgress,
            ]:
                return status, reason

        # Return Success if all configs are successful
        return additional_configuration.AdditionalConfigurationRunStatus.Success, reason

    def is_provisioned_product_ready(
        self,
        provisioned_product_id: provisioned_product_id_value_object.ProvisionedProductIdValueObject,
    ) -> bool:
        # Get the entity
        provisioned_product_entity = self._provisioned_products_qry_srv.get_by_id(
            provisioned_product_id=provisioned_product_id.value,
        )

        # Return instance status
        return self._system_command_srv.is_instance_ready(
            aws_account_id=provisioned_product_entity.awsAccountId,
            region=provisioned_product_entity.region,
            user_id=provisioned_product_entity.userId,
            instance_id=provisioned_product_entity.instanceId,
        )
