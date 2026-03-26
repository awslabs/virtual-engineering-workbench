import logging
import re
from datetime import datetime, timedelta, timezone

from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.events.provisioned_product_sync import provisioned_product_status_out_of_sync
from app.provisioning.domain.exceptions import not_found_exception
from app.provisioning.domain.model import product_status, provisioned_product, provisioned_product_details
from app.provisioning.domain.ports import instance_management_service, products_service
from app.shared.ddd import aggregate

PROVISIONED_PRODUCT_SYNC_PROCESS_NAME = "VEWProvisioningBCSync"


class ProvisionedProductStateSyncAggregate(aggregate.Aggregate):
    def __init__(
        self,
        logger: logging.Logger,
        pp_ent: provisioned_product.ProvisionedProduct,
        sc_pp: provisioned_product_details.ProvisionedProductDetails | None,
    ):
        super().__init__()
        self._provisioned_product = pp_ent
        self._sc_provisioned_product = sc_pp
        self._real_status: product_status.ProductStatus | None = None
        self._real_instance_id: str | None = None
        self._logger = logger

    def sync(
        self,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        products_srv: products_service.ProductsService,
    ):
        if self.__exists_in_db_but_not_in_service_catalog():
            self._publish(
                provisioned_product_status_out_of_sync.ProvisionedProductStatusOutOfSync(
                    provisionedProductId=self._provisioned_product.provisionedProductId,
                    oldStatus=self._provisioned_product.status,
                    newStatus=product_status.ProductStatus.Terminated,
                )
            )
            return

        if self.__is_orphan():
            return

        if self.__is_status_out_of_sync(instance_mgmt_srv=instance_mgmt_srv, products_srv=products_srv):
            self._publish(
                provisioned_product_status_out_of_sync.ProvisionedProductStatusOutOfSync(
                    provisionedProductId=self._provisioned_product.provisionedProductId,
                    oldStatus=self._provisioned_product.status,
                    newStatus=self._real_status,
                )
            )
            return

    def __exists_in_db_but_not_in_service_catalog(self):
        return (
            self.__is_orphan() and self.__is_stale() and self.__is_not(status=product_status.ProductStatus.Terminated)
        )

    def __is_orphan(self):
        """Checks if VEW provisioned product has a corresponging Service Catalog provisioned product."""

        return self._sc_provisioned_product is None

    def __is_stale(self):
        """Sync is only processing provisioned products that where created 1 hour before to avoid race condition."""

        minutes = 180 if self._provisioned_product.status == product_status.ProductStatus.Updating else 30

        return datetime.now(timezone.utc) - datetime.fromisoformat(self._provisioned_product.lastUpdateDate).replace(
            tzinfo=timezone.utc
        ) > timedelta(minutes=minutes)

    def __is_not(self, status: product_status.ProductStatus | None = None):
        if status and self._provisioned_product.status == status:
            return False
        return True

    def __is_status_out_of_sync(
        self,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        products_srv: products_service.ProductsService,
    ):
        if self._provisioned_product.status in [
            product_status.ProductStatus.ProvisioningError,
            product_status.ProductStatus.ConfigurationFailed,
        ]:
            return False  # There is no going back from ProvisioningError or ConfigurationFailed states

        if self.__is_in_provision_failed_state():
            return self._provisioned_product.status != self._real_status

        if self.__is_in_deprovision_failed_state():
            return self._provisioned_product.status != self._real_status

        if self.__is_in_update_failed_state():
            return self._provisioned_product.status != self._real_status

        if self.__is_stuck_in_configuration_in_progress():
            return self._provisioned_product.status != self._real_status

        if self.__is_in_transient_state():
            return False

        self.__refresh_state(
            instance_mgmt_srv=instance_mgmt_srv,
            products_srv=products_srv,
        )

        return self._real_status and self._real_status != self._provisioned_product.status

    def __is_in_provision_failed_state(self) -> bool:
        """Checks if provisioned product is stuck in provisioning failed state

        When initial provisioning fails, SC provisioned product enters ERROR state.
        """

        if self._sc_provisioned_product.status == product_status.ServiceCatalogStatus.Error:
            self._real_status = product_status.ProductStatus.ProvisioningError
            return True

        return False

    def __is_in_deprovision_failed_state(self) -> bool:
        """Checks if provisioned product is stuck in deprovisioning state

        When deprovisioning fails, SC provisioned product enters TAINTED state.
        However, all the resources are terminated, and user should see Terminated state.
        This step requires manual intervention to delete TAINTED provisioend product in SC.
        """

        if (
            self._sc_provisioned_product.status == product_status.ServiceCatalogStatus.Tainted
            and self._provisioned_product.status == product_status.ProductStatus.Deprovisioning
        ):
            self._real_status = product_status.ProductStatus.ProvisioningError
            return True

        return False

    def __is_in_update_failed_state(self) -> bool:
        """Checks if provisioned product is stuck in update failed state

        When update fails, SC provisioned product enters TAINTED state.
        """

        if (
            self._sc_provisioned_product.status == product_status.ServiceCatalogStatus.Tainted
            and self._provisioned_product.status == product_status.ProductStatus.Updating
        ):
            self._real_status = product_status.ProductStatus.ProvisioningError
            return True

        return False

    def __is_in_transient_state(self) -> bool:
        """Checks if provisioned product is in a transient state

        When provisioned product is being provisioned or updated, do not do any state sync checks.
        We will wait for the provisioning to complete and try to resolve the terminal state
        via events.
        """

        if self._sc_provisioned_product.status in [
            product_status.ServiceCatalogStatus.UnderChange,
            product_status.ServiceCatalogStatus.PlanInProgress,
        ]:
            return True
        return False

    def __is_stuck_in_configuration_in_progress(self) -> bool:
        """Checks if provisioned product is stuck in configuration in progress state for a long time

        Configuration starts after service catalog product is provisioned successfully.
        It must be completed within one hour, otherwise we consider the product is stuck in this state.
        """

        if (
            self.__is_stale()
            and self._sc_provisioned_product.status == product_status.ServiceCatalogStatus.Available
            and self._provisioned_product.status == product_status.ProductStatus.ConfigurationInProgress
        ):
            self._real_status = product_status.ProductStatus.ConfigurationFailed
            return True

        return False

    def __refresh_state(
        self,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        products_srv: products_service.ProductsService,
    ):
        match self._provisioned_product.provisionedProductType:
            case p if p in provisioned_product.PRODUCT_INSTANCE_TYPES:
                self.__refresh_real_instance_id(products_srv=products_srv)
                self.__refresh_real_instance_status(instance_mgmt_srv=instance_mgmt_srv)

    def __refresh_real_instance_id(
        self,
        products_srv: products_service.ProductsService,
    ):
        if self._provisioned_product.status != product_status.ProductStatus.Updating:
            self._real_instance_id = self._provisioned_product.instanceId

        if not self._real_instance_id:
            try:
                outputs = products_srv.get_provisioned_product_outputs(
                    provisioned_product_id=self._provisioned_product.scProvisionedProductId,
                    user_id=PROVISIONED_PRODUCT_SYNC_PROCESS_NAME,
                    aws_account_id=self._provisioned_product.awsAccountId,
                    region=self._provisioned_product.region,
                )
                for output in outputs:
                    if re.match(
                        product_provisioning_aggregate.PRODUCT_OUTPUT_INSTANCE_ID_REGEX, output.outputValue, flags=re.I
                    ):
                        self._real_instance_id = output.outputValue
            except not_found_exception.NotFoundException:
                self._logger.exception(
                    f"Unable to fetch provisioned product outputs for {self._provisioned_product.scProvisionedProductId}"
                )
                self._real_status = product_status.ProductStatus.ProvisioningError
            except:
                self._logger.exception(
                    f"Unable to fetch provisioned product outputs for {self._provisioned_product.scProvisionedProductId}"
                )

    def __refresh_real_instance_status(
        self,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
    ):
        if not self._real_instance_id or self._real_status:
            return

        instance_state: str | None = None
        try:
            instance_state = instance_mgmt_srv.get_instance_state(
                user_id=PROVISIONED_PRODUCT_SYNC_PROCESS_NAME,
                aws_account_id=self._provisioned_product.awsAccountId,
                region=self._provisioned_product.region,
                instance_id=self._real_instance_id,
            )
        except:
            self._logger.exception(f"Unable to fetch instance state for {self._real_instance_id}")

        if instance_state and instance_state in product_status.EC2_TO_PRODUCT_STATE_MAP:
            self._real_status = product_status.EC2_TO_PRODUCT_STATE_MAP.get(instance_state)

    def _repository_actions(self):
        pass
