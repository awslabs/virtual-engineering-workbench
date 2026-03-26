import ipaddress
import logging
import random
import re
from datetime import datetime, timezone

import semver

from app.provisioning.domain.aggregates.internal import (
    networking_helpers,
    product_helpers,
    provisioning_helpers,
)
from app.provisioning.domain.commands.product_provisioning import (
    authorize_user_ip_address_command,
    check_if_upgrade_available_command,
    cleanup_provisioned_products_command,
    complete_product_launch_command,
    complete_provisioned_product_removal_command,
    complete_provisioned_product_update,
    deprovision_provisioned_product_command,
    fail_product_launch_command,
    fail_provisioned_product_removal_command,
    fail_provisioned_product_update,
    launch_product_command,
    provision_product_command,
    remove_provisioned_product_command,
    start_provisioned_product_update_command,
    stop_provisioned_product_after_update_complete_command,
    stop_provisioned_product_for_update_command,
    update_provisioned_product_command,
)
from app.provisioning.domain.events.product_provisioning import (
    insufficient_capacity_reached,
    product_launch_failed,
    product_launch_started,
    product_launched,
    product_provisioning_started,
    provisioned_product_deprovisioning_started,
    provisioned_product_dormant_cleanup_failed,
    provisioned_product_removal_failed,
    provisioned_product_removal_retried,
    provisioned_product_removal_started,
    provisioned_product_removed,
    provisioned_product_stop_for_upgrade_failed,
    provisioned_product_stop_for_upgrade_initiated,
    provisioned_product_stopped_for_upgrade,
    provisioned_product_update_initialized,
    provisioned_product_update_started,
    provisioned_product_upgrade_available,
    provisioned_product_upgrade_failed,
    provisioned_product_upgraded,
)
from app.provisioning.domain.events.provisioned_product_configuration import (
    provisioned_product_configuration_requested,
)
from app.provisioning.domain.events.provisioned_product_state import (
    provisioned_product_stop_initiated,
)
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import (
    container_details,
    instance_details,
    network_subnet,
    product_status,
    provisioned_product,
    user_profile,
)
from app.provisioning.domain.ports import (
    container_management_service,
    instance_management_service,
    parameter_service,
    products_query_service,
    products_service,
    projects_query_service,
    provisioned_products_query_service,
    versions_query_service,
)
from app.provisioning.domain.read_models import product, version
from app.provisioning.domain.value_objects import (
    project_id_value_object,
    provisioned_product_id_value_object,
    provisioning_parameters_value_object,
    user_id_value_object,
    user_role_value_object,
)
from app.shared.adapters.feature_toggling import backend_feature_toggles
from app.shared.adapters.message_bus import message_bus
from app.shared.ddd import aggregate
from app.shared.middleware.authorization import VirtualWorkbenchRoles

EXPERIMENTAL_INPUT_PARAM_NAME = "Experimental"
PRODUCT_TO_PROVISIONED_PRODUCT_TYPE_MAP = {
    product.ProductType.VirtualTarget: provisioned_product.ProvisionedProductType.VirtualTarget,
    product.ProductType.Workbench: provisioned_product.ProvisionedProductType.Workbench,
    product.ProductType.Container: provisioned_product.ProvisionedProductType.Container,
}

PRODUCT_PARAM_TYPE_SUBNET_ID = "AWS::EC2::Subnet::Id"
PRODUCT_PARAM_TYPE_SUBNETS_ID = "List<AWS::EC2::Subnet::Id>"
PRODUCT_PARAM_TYPE_AZ = "AWS::EC2::AvailabilityZone::Name"
PRODUCT_PARAM_NAME_SECURITY_GROUP = "UserSecurityGroupId"
PRODUCT_PARAM_NAME_OWNER_TID = "OwnerTID"
PRODUCT_PARAM_NAME_CONTAINER_CLUSTER_NAME = "ClusterName"
PRODUCT_PARAM_NAME_CONTAINER_SERVICE_NAME = "ServiceName"
PRODUCT_PARAM_NAME_VEW_ALLOCATED_IP = "VEWAllocatedIPAddress"

PRODUCT_OUTPUT_INSTANCE_ID_REGEX = r"i-[\d\w-]{8,}"
PRODUCT_OUTPUT_SSH_KEY_NAME = "SSHKeyPair"
PRODUCT_OUTPUT_SSH_KEY_ID = "KeyPairId"
PRODUCT_OUTPUT_USER_CREDENTIALS_NAME = "UserCredentialsSecret"

PRODUCT_CONTAINER_TYPES = [provisioned_product.ProvisionedProductType.Container]
PRODUCT_EC2_TYPES = [
    provisioned_product.ProvisionedProductType.VirtualTarget,
    provisioned_product.ProvisionedProductType.Workbench,
]
AUTO_UPDATE_PROCESS_NAME = "AUTO_UPDATE"
AUTO_STOP_AFTER_UPDATE_PROCESS_NAME = "AUTO_STOP_AFTER_UPDATE_PROCESS_NAME"
CLEANUP_ERROR_PROVISIONED_PRODUCT = "CLEANUP_ERROR_PROVISIONED_PRODUCT"


class ProductProvisioningAggregate(aggregate.Aggregate):
    def __init__(
        self,
        logger: logging.Logger,
        provisioned_product_entity: provisioned_product.ProvisionedProduct | None = None,
        user_profile_entity: user_profile.UserProfile | None = None,
        product_entity: product.Product | None = None,
    ):
        super().__init__()
        self._logger = logger
        self._provisioned_product = provisioned_product_entity.copy(deep=True) if provisioned_product_entity else None
        self._original_provisioned_product = (
            provisioned_product_entity.copy(deep=True) if provisioned_product_entity else None
        )
        self._user_profile = user_profile_entity.copy(deep=True) if user_profile_entity else None
        self._original_user_profile = user_profile_entity.copy(deep=True) if user_profile_entity else None
        self._product = product_entity.copy() if product_entity else None
        self._original_product = product_entity.copy() if product_entity else None
        self._vpc_id: str = None
        self._route_tables = None
        self._vpc_subnets = None
        self._vpc_subnet_for_provisioning: network_subnet.NetworkSubnet | None = None
        self._instance: instance_details.InstanceDetails | None = None
        self._container: container_details.ContainerDetails | None = None
        self._available_subnets_ordered_by_ip_count: list[network_subnet.NetworkSubnet] | None = None

    """
    Command handlers
    """

    def launch(
        self,
        command: launch_product_command.LaunchProductCommand,
        products_qs: products_query_service.ProductsQueryService,
        versions_qs: versions_query_service.VersionsQueryService,
        provisioned_products_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
        feature_toggles_srv: backend_feature_toggles.BackendFeatureToggles,
        experimental_provisioned_product_per_project_limit: int,
        projects_qs: projects_query_service.ProjectsQueryService,
    ):
        """First step in launching a provisioned product.
        Validates input parameters and stores provisioned product entity in PROVISIONING state.

        Launch process:
        LaunchProductCommand >
            ProvisionProductCommand >
            CompleteProductLaunchCommand / FailProductLaunchCommand.
        """
        if self._provisioned_product:
            raise domain_exception.DomainException(
                "Product provisioning aggregate cannot be loaded with an entity when launching."
            )

        product_read_model = products_qs.get_product(
            project_id=command.project_id.value, product_id=command.product_id.value
        )

        if not product_read_model:
            raise domain_exception.DomainException(f"Product {command.product_id.value} does not exist")

        if product_read_model.productType not in PRODUCT_TO_PROVISIONED_PRODUCT_TYPE_MAP:
            raise domain_exception.DomainException(
                f"Products of type {product_read_model.productType} are not supported."
            )

        assignment = projects_qs.get_project_assignment(
            project_id=command.project_id.value, user_id=command.user_id.value
        )
        if not assignment or not assignment.roles:
            raise domain_exception.DomainException(
                "User does not have a role in the project to allow product provisioning"
            )

        version_distribution = self.__get_version_distribution(
            versions_qs=versions_qs,
            product_id=command.product_id.value,
            version_id=command.version_id.value,
            region=command.region.value,
            stage=command.stage.value,
        )

        mapped_params = self.__validate_and_map_input_parameters(
            provisioning_parameters=command.provisioning_parameters.value,
            product_parameters=version_distribution.parameters,
        )

        existing_user_provisioned_products = provisioned_products_qs.get_provisioned_products_by_user_id(
            user_id=command.user_id.value,
            project_id=command.project_id.value,
            stage=command.stage.value,
            exclude_status=[
                product_status.ProductStatus.Terminated,
                product_status.ProductStatus.Deprovisioning,
            ],
            product_id=command.product_id.value,
        )

        provisioned_product_limit_per_type_and_user = 5
        if command.stage.value == provisioned_product.ProvisionedProductStage.QA:
            provisioned_product_limit_per_type_and_user += 1

        if len(existing_user_provisioned_products) >= provisioned_product_limit_per_type_and_user:
            raise domain_exception.DomainException(
                "Number of allowed provisioned products per product type is reached. You must deprovision a product of the same type before provisioning a new product."
            )

        experimental_provisioning_parameter_value = self.__get_experimental_provisionining_parameter_value(
            provisioning_parameters=command.provisioning_parameters.value,
        )
        if experimental_provisioning_parameter_value:
            self.__raise_if_experimental_product_attempted_provisioning_in_not_allow_stage(stage=command.stage.value)
            self.__raise_if_experimental_provisioned_product_project_limit_exceeded(
                project_id=command.project_id.value,
                provisioned_products_qs=provisioned_products_qs,
                experimental_provisioned_product_per_project_limit=experimental_provisioned_product_per_project_limit,
            )

        provisioned_product_name = re.sub(
            r"[^a-zA-Z0-9_-]",
            "-",
            f"{command.product_id.value}-{command.version_id.value}-{command.user_id.value}-{str(random.randrange(1, 99999)).zfill(5)}",
        )
        provisioned_product_type = PRODUCT_TO_PROVISIONED_PRODUCT_TYPE_MAP.get(product_read_model.productType)
        current_time = datetime.now(timezone.utc).isoformat()
        self._provisioned_product = provisioned_product.ProvisionedProduct(
            projectId=command.project_id.value,
            provisionedProductId=command.provisioned_product_id.value,
            provisionedProductName=provisioned_product_name,
            provisionedProductType=provisioned_product_type,
            userId=command.user_id.value,
            userDomains=command.user_domains.value,
            status=product_status.ProductStatus.Provisioning,
            productId=command.product_id.value,
            productName=product_read_model.productName,
            productDescription=product_read_model.productDescription,
            technologyId=product_read_model.technologyId,
            versionId=command.version_id.value,
            versionName=version_distribution.versionName,
            versionDescription=version_distribution.versionDescription,
            awsAccountId=version_distribution.awsAccountId,
            accountId=version_distribution.accountId,
            stage=command.stage.value,
            region=command.region.value,
            amiId=version_distribution.amiId,
            scProductId=version_distribution.scProductId,
            scProvisioningArtifactId=version_distribution.scProvisioningArtifactId,
            provisioningParameters=mapped_params,
            createDate=current_time,
            lastUpdateDate=current_time,
            createdBy=command.user_id.value,
            lastUpdatedBy=command.user_id.value,
            additionalConfigurations=command.additional_configurations.value,
            experimental=experimental_provisioning_parameter_value,
            componentVersionDetails=version_distribution.componentVersionDetails,
            osVersion=version_distribution.osVersion,
            userIpAddress=command.user_ip_address.value,
            provisionedCompoundProductId=command.provisioned_compound_product_id.value,
            deploymentOption=command.deployment_option.value,
        )

        self._publish(
            product_launch_started.ProductLaunchStarted(
                provisionedProductId=command.provisioned_product_id.value,
                userIpAddress=command.user_ip_address.value,
            )
        )

    def remove(
        self,
        command: remove_provisioned_product_command.RemoveProvisionedProductCommand,
    ):
        """First step in removing a provisioned product.
        Updates provisioned product state to DEPROVISIONING state.

        Remove process:
        RemoveProvisionedProductCommand >
            DeprovisionProvisionedProductCommand >
            CompleteProvisionedProductRemovalCommand / FailProvisionedProductRemovalCommand.
        """
        self.__raise_if_entity_not_loaded_for(provisioned_product_id=command.provisioned_product_id)

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

        self.__raise_for(status=product_status.ProductStatus.Deprovisioning)
        self.__raise_for(status=product_status.ProductStatus.Provisioning)
        self.__raise_for(status=product_status.ProductStatus.Terminated)

        self._provisioned_product.status = product_status.ProductStatus.Deprovisioning
        self._provisioned_product.lastUpdatedBy = command.user_id.value
        self._publish(
            provisioned_product_removal_started.ProvisionedProductRemovalStarted(
                provisionedProductId=self._provisioned_product.provisionedProductId
            )
        )

    def check_if_upgrade_available(
        self,
        command: check_if_upgrade_available_command.CheckIfUpgradeAvailableCommand,
    ):
        """
        Updates provisioned product entity with new version ID and name if it's different from the current one.
        """

        if self._provisioned_product.versionId == command.product_version_id.value:
            return

        if self._provisioned_product.stage != command.stage.value:
            return

        if self._provisioned_product.region != command.region.value:
            return

        current_version = semver.Version.parse(self._provisioned_product.versionName)
        target_version = semver.Version.parse(command.product_version_name.value)

        if current_version > target_version:
            return

        self._provisioned_product.newVersionId = command.product_version_id.value
        self._provisioned_product.newVersionName = command.product_version_name.value
        self._provisioned_product.upgradeAvailable = True
        self._publish(
            provisioned_product_upgrade_available.ProvisionedProductUpgradeAvailable(
                provisionedProductId=self._provisioned_product.provisionedProductId
            )
        )

    def start_update(
        self,
        command: start_provisioned_product_update_command.StartProvisionedProductUpdateCommand,
        versions_qs: versions_query_service.VersionsQueryService,
    ):
        """The first step of updating a workbench.
        Initiates provisioned product update, which is triggered by the user.

        Workbench update process:
        StartProvisionedProductUpdateCommand >
            StopProvisionedProductForUpdateCommand >
            UpdateProvisionedProductCommand >
            CompleteProvisionedProductUpdateCommand / FailProvisionedProductUpdateCommand
        """

        self.__raise_if_entity_not_loaded_for(provisioned_product_id=command.provisioned_product_id)
        self.__raise_if_not(project_id=command.project_id, user_id=command.user_id)
        self.__raise_if_not(
            status=[
                product_status.ProductStatus.Running,
                product_status.ProductStatus.Stopped,
            ]
        )

        self._provisioned_product.status = product_status.ProductStatus.Updating
        version_distribution = self.__get_version_distribution(
            versions_qs=versions_qs,
            product_id=self._provisioned_product.productId,
            version_id=command.version_id.value,
            region=self._provisioned_product.region,
            stage=self._provisioned_product.stage,
        )

        self._provisioned_product.newProvisioningParameters = self.__validate_and_map_input_parameters(
            provisioning_parameters=command.provisioning_parameters.value,
            current_provisioned_parameters=self._provisioned_product.provisioningParameters,
            product_parameters=version_distribution.parameters,
        )
        self._provisioned_product.newVersionId = version_distribution.versionId
        self._provisioned_product.newVersionName = version_distribution.versionName
        self._provisioned_product.lastUpdatedBy = command.user_id.value

        self._publish(
            provisioned_product_update_initialized.ProvisionedProductUpdateInitialized(
                provisionedProductId=self._provisioned_product.provisionedProductId,
                userIpAddress=command.user_ip_address.value,
            )
        )

    def __get_product_category(self):
        """
        According to
        every provisioned product must be tagged with
        `vew:product:category` tag. The values:
            - VirtualMachine
            - BareMetal
            - Container

        We assume all BareMetal instance types have the word "metal" iun it.
        """
        if self._provisioned_product.provisionedProductType == provisioned_product.ProvisionedProductType.Container:
            return "Container"

        for parameter in self._provisioned_product.provisioningParameters:
            if parameter.key == "InstanceType":
                instance_type = parameter.value
                if ".metal" in instance_type:
                    return "BareMetal"
                else:
                    return "VirtualMachine"

    def provision_product(
        self,
        command: provision_product_command.ProvisionProductCommand,
        products_srv: products_service.ProductsService,
        parameter_srv: parameter_service.ParameterService,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        spoke_account_vpc_id_param_name: str,
        subnet_selector: networking_helpers.SubnetSelector,
        authorize_user_ip_address_param_value: bool,
    ):
        """Second step in launching a provisioned product.
        Provisions a product in Service Catalog.

        Launch process:
        LaunchProductCommand >
            ProvisionProductCommand >
            CompleteProductLaunchCommand / FailProductLaunchCommand.
        """
        self.__raise_if_entity_not_loaded_for(provisioned_product_id=command.provisioned_product_id)
        self.__raise_if_not(status=product_status.ProductStatus.Provisioning)

        if self._provisioned_product.scProvisionedProductId:
            self._logger.warning(
                {
                    "provisionedProductId": self._provisioned_product.provisionedProductId,
                    "provisionedProductStatus": self._provisioned_product.status,
                    "scProvisionedProductId": self._provisioned_product.scProvisionedProductId,
                    "message": "Product provisioning is already in progress.",
                }
            )
            return

        try:
            self.__set_technical_product_provisioning_parameters(
                parameter_srv=parameter_srv,
                instance_mgmt_srv=instance_mgmt_srv,
                spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
                subnet_selector=subnet_selector,
            )
            # All subnets were triggered for provisioning already
            # There is no capacity for provisioning
            if self._provisioned_product.availabilityZonesTriggered and len(
                self._provisioned_product.availabilityZonesTriggered
            ) == len(self._available_subnets_ordered_by_ip_count):
                self.__fail(
                    event=product_launch_failed.ProductLaunchFailed(
                        projectId=self._provisioned_product.projectId,
                        provisionedProductId=self._provisioned_product.provisionedProductId,
                        provisionedCompoundProductId=self._provisioned_product.provisionedCompoundProductId,
                        productName=self._provisioned_product.productName,
                        productType=self._provisioned_product.provisionedProductType,
                        owner=self._provisioned_product.userId,
                    ),
                    reason="InsufficientCapacityInAllAvailabilityZones",
                )
                return

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

            provisioned_product_name = self._provisioned_product.provisionedProductName
            if self._vpc_subnet_for_provisioning:
                current_availability_zones = (
                    self._provisioned_product.availabilityZonesTriggered
                    if self._provisioned_product.availabilityZonesTriggered
                    else []
                )
                current_availability_zones.append(self._vpc_subnet_for_provisioning.availability_zone)
                self._provisioned_product.availabilityZonesTriggered = current_availability_zones
                provisioned_product_name = f"{self._provisioned_product.provisionedProductName}-{self._vpc_subnet_for_provisioning.availability_zone}"

            self._provisioned_product.scProvisionedProductId = products_srv.provision_product(
                user_id=self._provisioned_product.createdBy,
                aws_account_id=self._provisioned_product.awsAccountId,
                sc_product_id=self._provisioned_product.scProductId,
                sc_provisioning_artifact_id=self._provisioned_product.scProvisioningArtifactId,
                provisioning_parameters=self._provisioned_product.provisioningParameters,
                name=provisioned_product_name,
                region=self._provisioned_product.region,
                tags=[
                    {"Key": "UserTID", "Value": self._provisioned_product.createdBy},
                    {"Key": "OwnerID", "Value": self._provisioned_product.createdBy},
                    {
                        "Key": "OwnerDomains",
                        "Value": ":".join(self._provisioned_product.userDomains or ["", ""]),
                    },
                    {
                        "Key": "vew:provisionedProduct:ownerDomains",
                        "Value": ":".join(self._provisioned_product.userDomains or ["", ""]),
                    },
                    {
                        "Key": "vew:provisionedProduct:productType",
                        "Value": self._provisioned_product.provisionedProductType,
                    },
                    {
                        "Key": "vew:provisionedProduct:id",
                        "Value": self._provisioned_product.provisionedProductId,
                    },
                    {
                        "Key": "vew:provisionedProduct:ownerId",
                        "Value": self._provisioned_product.createdBy,
                    },
                    {
                        "Key": "vew:provisionedProduct:versionName",
                        "Value": self._provisioned_product.versionName,
                    },
                    {
                        "Key": "vew:product:name",
                        "Value": self._provisioned_product.productName,
                    },
                    {
                        "Key": "vew:product:versionName",
                        "Value": self._provisioned_product.versionName,
                    },
                    {
                        "Key": "vew:product:type",
                        "Value": self._provisioned_product.provisionedProductType,
                    },
                    {
                        "Key": "vew:product:category",
                        "Value": self.__get_product_category(),
                    },
                ],
            )

            self.__update_user_profile()

            self._publish(
                product_provisioning_started.ProductProvisioningStarted(
                    projectId=self._provisioned_product.projectId,
                    provisionedProductId=command.provisioned_product_id.value,
                    provisionedCompoundProductId=self._provisioned_product.provisionedCompoundProductId,
                )
            )

        except Exception as e:
            self._logger.exception("Unable to provision Service Catalog provisioned product")

            self.__fail(
                event=product_launch_failed.ProductLaunchFailed(
                    projectId=self._provisioned_product.projectId,
                    provisionedProductId=self._provisioned_product.provisionedProductId,
                    provisionedCompoundProductId=self._provisioned_product.provisionedCompoundProductId,
                    productName=self._provisioned_product.productName,
                    productType=self._provisioned_product.provisionedProductType,
                    owner=self._provisioned_product.userId,
                ),
                reason=str(e),
            )

    def deprovision_product(
        self,
        command: deprovision_provisioned_product_command.DeprovisionProvisionedProductCommand,
        products_srv: products_service.ProductsService,
    ):
        """Second step in removing a provisioned product.
        Deprovisions a product in Service Catalog.

        Remove process:
        RemoveProvisionedProductCommand >
            DeprovisionProvisionedProductCommand >
            CompleteProvisionedProductRemovalCommand / FailProvisionedProductRemovalCommand.
        """
        self.__raise_if_entity_not_loaded_for(provisioned_product_id=command.provisioned_product_id)
        self.__raise_if_not(status=product_status.ProductStatus.Deprovisioning)

        try:
            if self._provisioned_product.scProvisionedProductId:
                products_srv.deprovision_product(
                    user_id=self._provisioned_product.createdBy,
                    aws_account_id=self._provisioned_product.awsAccountId,
                    provisioned_product_id=self._provisioned_product.scProvisionedProductId,
                    region=self._provisioned_product.region,
                )

                self._publish(
                    provisioned_product_deprovisioning_started.ProvisionedProductDeprovisioningStarted(
                        provisionedProductId=self._provisioned_product.provisionedProductId
                    )
                )
            else:
                if self.__warn_for(status=product_status.ProductStatus.Terminated):
                    return

                self._provisioned_product.status = product_status.ProductStatus.Terminated

                self._publish(
                    provisioned_product_removed.ProvisionedProductRemoved(
                        projectId=self._provisioned_product.projectId,
                        provisionedProductId=self._provisioned_product.provisionedProductId,
                        provisionedCompoundProductId=self._provisioned_product.provisionedCompoundProductId,
                        awsAccountId=self._provisioned_product.awsAccountId,
                        region=self._provisioned_product.region,
                        instanceId=self._provisioned_product.instanceId,
                    )
                )

        except Exception as e:
            self._logger.exception("Unable to deprovision Service Catalog provisioned product")

            self.__fail(
                event=provisioned_product_removal_failed.ProvisionedProductRemovalFailed(
                    projectId=self._provisioned_product.projectId,
                    provisionedProductId=self._provisioned_product.provisionedProductId,
                    provisionedCompoundProductId=self._provisioned_product.provisionedCompoundProductId,
                ),
                reason=str(e),
            )

    def stop_for_update(
        self,
        command: stop_provisioned_product_for_update_command.StopProvisionedProductForUpdateCommand,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        container_mgmt_srv: container_management_service.ContainerManagementService,
        parameter_srv: parameter_service.ParameterService,
        spoke_account_vpc_id_param_name: str,
        authorize_user_ip_address_param_value: bool,
    ):
        """Second step of updating a workbench.
        Stops the provisioned product before update.
        This is needed to detach the EBS volume from the instance.

        Workbench update process:
        StartProvisionedProductUpdateCommand >
            StopProvisionedProductForUpdateCommand >
            UpdateProvisionedProductCommand >
            CompleteProvisionedProductUpdateCommand / FailProvisionedProductUpdateCommand
        """

        if self._provisioned_product.status != product_status.ProductStatus.Updating:
            self._publish(
                provisioned_product_stop_for_upgrade_failed.ProvisionedProductStopForUpgradeFailed(
                    provisionedProductId=command.provisioned_product_id.value
                )
            )
            return

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

        match self._provisioned_product.provisionedProductType:
            case p if p in provisioned_product.PRODUCT_CONTAINER_TYPES:
                status = container_mgmt_srv.get_container_status(
                    aws_account_id=self._provisioned_product.awsAccountId,
                    cluster_name=self._provisioned_product.containerClusterName,
                    service_name=self._provisioned_product.provisionedProductId,
                    region=self._provisioned_product.region,
                    user_id=self._provisioned_product.userId,
                )
                if (
                    product_status.CONTAINER_TO_PRODUCT_STATE_MAP.get(status.name)
                    == product_status.ProductStatus.Stopped
                ):
                    self._publish(
                        provisioned_product_stopped_for_upgrade.ProvisionedProductStoppedForUpgrade(
                            provisionedProductId=command.provisioned_product_id.value
                        )
                    )
                    return
                try:
                    container_mgmt_srv.stop_container(
                        aws_account_id=self._provisioned_product.awsAccountId,
                        cluster_name=self._provisioned_product.containerClusterName,
                        service_name=self._provisioned_product.provisionedProductId,
                        region=self._provisioned_product.region,
                        user_id=self._provisioned_product.userId,
                    )

                    self._publish(
                        provisioned_product_stop_for_upgrade_initiated.ProvisionedProductStopForUpgradeInitiated(
                            provisionedProductId=command.provisioned_product_id.value
                        )
                    )
                except Exception as e:
                    self._logger.exception("Unable to stop the Container instance before updating")
                    self._provisioned_product.statusReason = str(e)
                    self._publish(
                        provisioned_product_stop_for_upgrade_failed.ProvisionedProductStopForUpgradeFailed(
                            provisionedProductId=command.provisioned_product_id.value
                        )
                    )
                    return
            case p if p in provisioned_product.PRODUCT_INSTANCE_TYPES:
                instance_details = instance_mgmt_srv.get_instance_details(
                    user_id=self._provisioned_product.createdBy,
                    aws_account_id=self._provisioned_product.awsAccountId,
                    instance_id=self._provisioned_product.instanceId,
                    region=self._provisioned_product.region,
                )

                if instance_details.state.name == product_status.EC2InstanceState.Stopped:
                    self._publish(
                        provisioned_product_stopped_for_upgrade.ProvisionedProductStoppedForUpgrade(
                            provisionedProductId=command.provisioned_product_id.value
                        )
                    )
                    return

                try:
                    current_state = instance_mgmt_srv.stop_instance(
                        user_id=self._provisioned_product.createdBy,
                        aws_account_id=self._provisioned_product.awsAccountId,
                        instance_id=self._provisioned_product.instanceId,
                        region=self._provisioned_product.region,
                    )

                except Exception as e:
                    self._logger.exception("Unable to stop the EC2 instance before updating")
                    self._provisioned_product.statusReason = str(e)
                    self._publish(
                        provisioned_product_stop_for_upgrade_failed.ProvisionedProductStopForUpgradeFailed(
                            provisionedProductId=command.provisioned_product_id.value
                        )
                    )
                    return

                current_ec2_instance_state = product_status.EC2InstanceState(current_state)

                if current_ec2_instance_state != product_status.EC2InstanceState.Stopping:
                    self._publish(
                        provisioned_product_stop_for_upgrade_failed.ProvisionedProductStopForUpgradeFailed(
                            provisionedProductId=command.provisioned_product_id.value
                        )
                    )
                else:
                    self._publish(
                        provisioned_product_stop_for_upgrade_initiated.ProvisionedProductStopForUpgradeInitiated(
                            provisionedProductId=command.provisioned_product_id.value
                        )
                    )

    def update_product(
        self,
        command: update_provisioned_product_command.UpdateProvisionedProductCommand,
        products_srv: products_service.ProductsService,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        container_mgmt_srv: container_management_service.ContainerManagementService,
        versions_qs: versions_query_service.VersionsQueryService,
        parameter_srv: parameter_service.ParameterService,
        subnet_selector: networking_helpers.SubnetSelector,
        spoke_account_vpc_id_param_name: str,
    ):
        """Third step in updating a workbench.
        This command handler calls Service Catalog to update the provisioned product.
        If provisioned product has attached EBS volumes, it will stop the
        workbench EC2 instance and detach the volume for the update to succeed.

        Workbench update process:
        StartProvisionedProductUpdateCommand >
            StopProvisionedProductForUpdateCommand >
            UpdateProvisionedProductCommand >
            CompleteProvisionedProductUpdateCommand / FailProvisionedProductUpdateCommand
        """

        self.__raise_if_entity_not_loaded_for(provisioned_product_id=command.provisioned_product_id)
        self.__raise_if_not(status=product_status.ProductStatus.Updating)
        if not self._provisioned_product.scProvisionedProductId:
            raise domain_exception.DomainException("Service Catalog ID must be present to do an update.")

        try:
            self.__set_technical_product_provisioning_parameters(
                parameter_srv=parameter_srv,
                instance_mgmt_srv=instance_mgmt_srv,
                spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
                subnet_selector=subnet_selector,
            )

            new_version_distribution = self.__get_version_distribution(
                versions_qs=versions_qs,
                product_id=self._provisioned_product.productId,
                version_id=self._provisioned_product.newVersionId,
                stage=self._provisioned_product.stage,
                region=self._provisioned_product.region,
            )
            if self._provisioned_product.provisionedProductType != provisioned_product.ProvisionedProductType.Container:
                # update block device mappings before update if version changed
                if self._provisioned_product.versionId != self._provisioned_product.newVersionId:
                    block_device_mappings = instance_mgmt_srv.get_block_device_mappings(
                        user_id=self._provisioned_product.createdBy,
                        aws_account_id=self._provisioned_product.awsAccountId,
                        instance_id=self._provisioned_product.instanceId,
                        region=self._provisioned_product.region,
                    )
                    self._provisioned_product.blockDeviceMappings = block_device_mappings

                    if non_root_block_devices := [
                        d
                        for d in self._provisioned_product.blockDeviceMappings.mappings
                        if d.deviceName != self._provisioned_product.blockDeviceMappings.rootDeviceName
                    ]:
                        for device in non_root_block_devices:
                            instance_mgmt_srv.detach_instance_volume(
                                user_id=self._provisioned_product.createdBy,
                                aws_account_id=self._provisioned_product.awsAccountId,
                                region=self._provisioned_product.region,
                                instance_id=self._provisioned_product.instanceId,
                                volume_id=device.volumeId,
                            )

            products_srv.update_product(
                user_id=self._provisioned_product.createdBy,
                aws_account_id=self._provisioned_product.awsAccountId,
                sc_provisioned_product_id=self._provisioned_product.scProvisionedProductId,
                sc_product_id=self._provisioned_product.scProductId,
                sc_provisioning_artifact_id=new_version_distribution.scProvisioningArtifactId,
                provisioning_parameters=self._provisioned_product.newProvisioningParameters,
                region=self._provisioned_product.region,
            )

            self.__update_user_profile()

            self._publish(
                provisioned_product_update_started.ProvisionedProductUpdateStarted(
                    provisionedProductId=self._provisioned_product.provisionedProductId,
                )
            )

        except Exception as e:
            self._logger.exception("Unable to update Service Catalog provisioned product")

            self.__refresh_product_parameters(
                products_srv=products_srv,
                instance_mgmt_srv=instance_mgmt_srv,
                container_mgmt_srv=container_mgmt_srv,
            )
            self._provisioned_product.statusReason = str(e)
            self._publish(
                provisioned_product_upgrade_failed.ProvisionedProductUpgradeFailed(
                    provisionedProductId=self._provisioned_product.provisionedProductId,
                )
            )

    def __validate_mandatory_fields_by_product_type(self):
        if self._provisioned_product.provisionedProductType == provisioned_product.ProvisionedProductType.Container:
            return self.__validate_container_fields()
        else:
            return self.__validate_ec2_product_fields()

    def __validate_container_fields(self):
        if not self._provisioned_product.containerName:
            self.__fail(
                event=product_launch_failed.ProductLaunchFailed(
                    projectId=self._provisioned_product.projectId,
                    provisionedProductId=self._provisioned_product.provisionedProductId,
                    provisionedCompoundProductId=self._provisioned_product.provisionedCompoundProductId,
                    productName=self._provisioned_product.productName,
                    productType=self._provisioned_product.provisionedProductType,
                    owner=self._provisioned_product.userId,
                ),
                reason="Missing container name in the output.",
            )
            return False

        if not self._provisioned_product.containerServiceName:
            self.__fail(
                event=product_launch_failed.ProductLaunchFailed(
                    projectId=self._provisioned_product.projectId,
                    provisionedProductId=self._provisioned_product.provisionedProductId,
                    provisionedCompoundProductId=self._provisioned_product.provisionedCompoundProductId,
                    productName=self._provisioned_product.productName,
                    productType=self._provisioned_product.provisionedProductType,
                    owner=self._provisioned_product.userId,
                ),
                reason="Missing service ID in the output.",
            )
            return False

        if not self._provisioned_product.privateIp:
            self.__fail(
                event=product_launch_failed.ProductLaunchFailed(
                    projectId=self._provisioned_product.projectId,
                    provisionedProductId=self._provisioned_product.provisionedProductId,
                    provisionedCompoundProductId=self._provisioned_product.provisionedCompoundProductId,
                    productName=self._provisioned_product.productName,
                    productType=self._provisioned_product.provisionedProductType,
                    owner=self._provisioned_product.userId,
                ),
                reason="Missing IP address in the output.",
            )
            return False

        return True

    def __validate_ec2_product_fields(self):
        if not self._provisioned_product.instanceId:
            self.__fail(
                event=product_launch_failed.ProductLaunchFailed(
                    projectId=self._provisioned_product.projectId,
                    provisionedProductId=self._provisioned_product.provisionedProductId,
                    provisionedCompoundProductId=self._provisioned_product.provisionedCompoundProductId,
                    productName=self._provisioned_product.productName,
                    productType=self._provisioned_product.provisionedProductType,
                    owner=self._provisioned_product.userId,
                ),
                reason="Missing virtual target instance ID in the output.",
            )
            return False

        if not self._provisioned_product.privateIp:
            self.__fail(
                event=product_launch_failed.ProductLaunchFailed(
                    projectId=self._provisioned_product.projectId,
                    provisionedProductId=self._provisioned_product.provisionedProductId,
                    provisionedCompoundProductId=self._provisioned_product.provisionedCompoundProductId,
                    productName=self._provisioned_product.productName,
                    productType=self._provisioned_product.provisionedProductType,
                    owner=self._provisioned_product.userId,
                ),
                reason="Missing IP address in the output.",
            )
            return False

        return True

    def complete_launch(
        self,
        command: complete_product_launch_command.CompleteProductLaunchCommand,
        products_srv: products_service.ProductsService,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        container_mgmt_srv: container_management_service.ContainerManagementService,
        versions_qs: versions_query_service.VersionsQueryService,
    ):
        """Final step in launching a provisioned product if successful.
        Fetches the provisioned product params (IP, instance ID), and sets the status to RUNNING.

        Launch process:
        LaunchProductCommand >
            ProvisionProductCommand >
            CompleteProductLaunchCommand / FailProductLaunchCommand.
        """
        self.__raise_if_entity_not_loaded_for(
            provisioned_product_id=command.provisioned_product_id,
        )

        if self.__warn_if_not(status=product_status.ProductStatus.Provisioning):
            return

        try:
            self.__refresh_product_parameters(
                products_srv=products_srv,
                instance_mgmt_srv=instance_mgmt_srv,
                container_mgmt_srv=container_mgmt_srv,
            )
            # Validate the fields for the product type
            if not self.__validate_mandatory_fields_by_product_type():
                return  # Exit if validation fails

            self._update_provisioning_time_stats()

            version_distribution = self.__get_version_distribution(
                versions_qs=versions_qs,
                product_id=self._provisioned_product.productId,
                version_id=self._provisioned_product.versionId,
                region=self._provisioned_product.region,
                stage=self._provisioned_product.stage,
            )

            new_version_distribution = self.__get_new_version_distribution(
                versions_qs=versions_qs,
                product_id=self._provisioned_product.productId,
                region=self._provisioned_product.region,
                stage=self._provisioned_product.stage,
            )

            has_new_version = semver.Version.parse(new_version_distribution.versionName) > semver.Version.parse(
                version_distribution.versionName
            )

            self._provisioned_product.newVersionName = new_version_distribution.versionName if has_new_version else None
            self._provisioned_product.newVersionId = new_version_distribution.versionId if has_new_version else None
            self._provisioned_product.upgradeAvailable = has_new_version
            self._provisioned_product.startDate = datetime.now(timezone.utc).isoformat()

            # update block device mappings if it's not a container
            if self._provisioned_product.provisionedProductType != provisioned_product.ProvisionedProductType.Container:
                block_device_mappings = instance_mgmt_srv.get_block_device_mappings(
                    user_id=self._provisioned_product.createdBy,
                    aws_account_id=self._provisioned_product.awsAccountId,
                    instance_id=self._provisioned_product.instanceId,
                    region=self._provisioned_product.region,
                )
                self._provisioned_product.blockDeviceMappings = block_device_mappings

            # Request additional configuration if needed, otherwise finish product launch
            if self._provisioned_product.additionalConfigurations:
                self.__request_additional_configuration()
            else:
                # If Provisioning is successful then clear triggered AZ
                # so AZs could be retired when starting as well
                self._provisioned_product.availabilityZonesTriggered = None
                match self._provisioned_product.provisionedProductType:
                    case p if p in provisioned_product.PRODUCT_CONTAINER_TYPES:
                        self._publish(
                            product_launched.ProductLaunched(
                                projectId=self._provisioned_product.projectId,
                                provisionedProductId=self._provisioned_product.provisionedProductId,
                                provisionedCompoundProductId=self._provisioned_product.provisionedCompoundProductId,
                                productName=self._provisioned_product.productName,
                                productType=self._provisioned_product.provisionedProductType,
                                owner=self._provisioned_product.userId,
                                privateIP=self._provisioned_product.privateIp,
                                serviceId=self._provisioned_product.containerServiceName,
                                awsAccountId=self._provisioned_product.awsAccountId,
                                region=self._provisioned_product.region,
                                containerTaskArn=self._provisioned_product.containerTaskArn,
                            )
                        )
                    case p if p in provisioned_product.PRODUCT_INSTANCE_TYPES:
                        self._publish(
                            product_launched.ProductLaunched(
                                projectId=self._provisioned_product.projectId,
                                provisionedProductId=self._provisioned_product.provisionedProductId,
                                provisionedCompoundProductId=self._provisioned_product.provisionedCompoundProductId,
                                productName=self._provisioned_product.productName,
                                productType=self._provisioned_product.provisionedProductType,
                                owner=self._provisioned_product.userId,
                                instanceId=self._provisioned_product.instanceId,
                                privateIP=self._provisioned_product.privateIp,
                                awsAccountId=self._provisioned_product.awsAccountId,
                                region=self._provisioned_product.region,
                            )
                        )
        except Exception as e:
            self._logger.exception("Unable to complete provisioned product launch operation.")

            self.__fail(
                event=product_launch_failed.ProductLaunchFailed(
                    projectId=self._provisioned_product.projectId,
                    provisionedProductId=self._provisioned_product.provisionedProductId,
                    provisionedCompoundProductId=self._provisioned_product.provisionedCompoundProductId,
                    productName=self._provisioned_product.productName,
                    productType=self._provisioned_product.provisionedProductType,
                    owner=self._provisioned_product.userId,
                ),
                reason=str(e),
            )

    def complete_removal(
        self,
        command: complete_provisioned_product_removal_command.CompleteProvisionedProductRemovalCommand,
    ):
        """Final step in removing a provisioned product if successful.
        Sets the provisioned product entity status to TERMINATED.

        Remove process:
        RemoveProvisionedProductCommand >
            DeprovisionProvisionedProductCommand >
            CompleteProvisionedProductRemovalCommand / FailProvisionedProductRemovalCommand.
        """
        self.__raise_if_entity_not_loaded_for(
            provisioned_product_id=command.provisioned_product_id,
        )

        if self.__warn_for(status=product_status.ProductStatus.Terminated):
            return

        self._provisioned_product.status = product_status.ProductStatus.Terminated

        self._publish(
            provisioned_product_removed.ProvisionedProductRemoved(
                projectId=self._provisioned_product.projectId,
                provisionedProductId=self._provisioned_product.provisionedProductId,
                provisionedCompoundProductId=self._provisioned_product.provisionedCompoundProductId,
                awsAccountId=self._provisioned_product.awsAccountId,
                region=self._provisioned_product.region,
                instanceId=self._provisioned_product.instanceId,
            )
        )

    def complete_update(
        self,
        command: complete_provisioned_product_update.CompleteProvisionedProductUpdateCommand,
        products_srv: products_service.ProductsService,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        container_mgmt_srv: container_management_service.ContainerManagementService,
        versions_qs: versions_query_service.VersionsQueryService,
    ):
        """Last step of updating a workbench if successful.
        Fetches the new provisioned product parameters (IP, instance ID) and stores them in the database.

        Workbench update processes:
        * UpdateProvisionedProductCommand >
            StopProvisionedProductForUpdateCommand >
            UpdateProvisionedProductCommand >
            CompleteProvisionedProductUpdateCommand / FailProvisionedProductUpdateCommand
        * AutoUpgradeProvisionedProductCommand >
            CompleteProvisionedProductUpdateCommand / FailProvisionedProductUpdateCommand
        """

        self.__raise_if_entity_not_loaded_for(
            provisioned_product_id=command.provisioned_product_id,
        )
        self.__raise_if_not(status=product_status.ProductStatus.Updating)

        try:
            pp = products_srv.get_provisioned_product_details(
                provisioned_product_id=self._provisioned_product.scProvisionedProductId,
                aws_account_id=self._provisioned_product.awsAccountId,
                region=self._provisioned_product.region,
                user_id=self._provisioned_product.createdBy,
            )

            expected_upgraded_version = self.__get_version_distribution(
                versions_qs=versions_qs,
                product_id=self._provisioned_product.productId,
                version_id=self._provisioned_product.newVersionId,
                stage=self._provisioned_product.stage,
                region=self._provisioned_product.region,
            )

            actual_upgraded_version = versions_qs.get_by_provisioning_artifact_id(
                sc_provisioning_artifact_id=pp.provisioning_artifact_id,
            )

            new_version_distribution = self.__get_new_version_distribution(
                versions_qs=versions_qs,
                product_id=self._provisioned_product.productId,
                region=self._provisioned_product.region,
                stage=self._provisioned_product.stage,
            )

            has_new_version = semver.Version.parse(new_version_distribution.versionName) > semver.Version.parse(
                actual_upgraded_version.versionName
            )

            if not actual_upgraded_version:
                raise domain_exception.DomainException(
                    f"Version for provisioning artifact {pp.provisioning_artifact_id} not found"
                )

            # checking if there was no new version published during upgrade
            if pp.provisioning_artifact_id == expected_upgraded_version.scProvisioningArtifactId:
                self._provisioned_product.newVersionId = None
                self._provisioned_product.newVersionName = None
                self._provisioned_product.upgradeAvailable = False

            if has_new_version:
                self._provisioned_product.newVersionId = new_version_distribution.versionId
                self._provisioned_product.newVersionName = new_version_distribution.versionName
                self._provisioned_product.upgradeAvailable = True

            self._provisioned_product.versionId = actual_upgraded_version.versionId
            self._provisioned_product.versionName = actual_upgraded_version.versionName
            self._provisioned_product.provisioningParameters = self._provisioned_product.newProvisioningParameters
            self._provisioned_product.newProvisioningParameters = None
            self._provisioned_product.recommendedInstanceType = None
            self._provisioned_product.instanceRecommendationReason = None

            # update block device mappings if its not a container
            if self._provisioned_product.provisionedProductType != provisioned_product.ProvisionedProductType.Container:
                block_device_mappings = instance_mgmt_srv.get_block_device_mappings(
                    user_id=self._provisioned_product.createdBy,
                    aws_account_id=self._provisioned_product.awsAccountId,
                    instance_id=self._provisioned_product.instanceId,
                    region=self._provisioned_product.region,
                )
                self._provisioned_product.blockDeviceMappings = block_device_mappings
            self._provisioned_product.oldInstanceId = self._provisioned_product.instanceId
            self.__refresh_product_parameters(
                products_srv=products_srv,
                instance_mgmt_srv=instance_mgmt_srv,
                container_mgmt_srv=container_mgmt_srv,
                refresh_status=False,
            )

            self._publish(
                provisioned_product_upgraded.ProvisionedProductUpgraded(
                    provisionedProductId=self._provisioned_product.provisionedProductId,
                    awsAccountId=self._provisioned_product.awsAccountId,
                    region=self._provisioned_product.region,
                    oldInstanceId=self._provisioned_product.oldInstanceId,
                    instanceId=self._provisioned_product.instanceId,
                    projectId=self._provisioned_product.projectId,
                    owner=self._provisioned_product.userId,
                    privateIp=self._provisioned_product.privateIp,
                    productType=self._provisioned_product.provisionedProductType,
                    productName=self._provisioned_product.productName,
                )
            )
        except Exception as e:
            self._logger.exception("Unable to complete provisioned product upgrade operation.")

            self._provisioned_product.statusReason = str(e)
            self._provisioned_product.status = product_status.ProductStatus.ProvisioningError

            self._publish(
                provisioned_product_upgrade_failed.ProvisionedProductUpgradeFailed(
                    provisionedProductId=self._provisioned_product.provisionedProductId,
                )
            )

    def stop_after_update(
        self,
        command: stop_provisioned_product_after_update_complete_command.StopProvisionedProductAfterUpdateCompleteCommand,
    ):
        self.__raise_if_entity_not_loaded_for(
            provisioned_product_id=command.provisioned_product_id,
        )
        self.__raise_if_not(status=product_status.ProductStatus.Updating)
        self._provisioned_product.status = product_status.ProductStatus.Stopping
        self._provisioned_product.lastUpdatedBy = AUTO_STOP_AFTER_UPDATE_PROCESS_NAME
        self._publish(
            provisioned_product_stop_initiated.ProvisionedProductStopInitiated(
                provisionedProductId=command.provisioned_product_id.value
            )
        )

    def fail_launch(
        self,
        command: fail_product_launch_command.FailProductLaunchCommand,
        products_srv: products_service.ProductsService,
    ):
        """Final step in launching a provisioned product if failed.
        Sets the provisioned product status to PROVISIONING_ERROR.

        Launch process:
        LaunchProductCommand >
            ProvisionProductCommand >
            CompleteProductLaunchCommand / FailProductLaunchCommand.

        In case INSUFFICIENT_INSTANCE_CAPACITY retry from > ProvisionProductCommand
        """
        self.__raise_if_entity_not_loaded_for(
            provisioned_product_id=command.provisioned_product_id,
        )
        if self._provisioned_product.provisionedProductType != provisioned_product.ProvisionedProductType.Container:
            provisioned_instance_type = next(
                filter(
                    lambda parameter: parameter.key == "InstanceType",
                    self._provisioned_product.provisioningParameters,
                ),
                None,
            )
            has_insufficient_capacity_error = products_srv.has_provisioned_product_insufficient_capacity_error(
                provisioned_product_id=self._provisioned_product.scProvisionedProductId,
                aws_account_id=self._provisioned_product.awsAccountId,
                region=self._provisioned_product.region,
                user_id=self._provisioned_product.userId,
                provisioned_instance_type=(provisioned_instance_type.value if provisioned_instance_type else None),
            )

            if (
                has_insufficient_capacity_error
                and self._provisioned_product.deploymentOption != provisioned_product.DeploymentOption.SINGLE_AZ
                and (
                    self.__get_provisioning_param_by_type(PRODUCT_PARAM_TYPE_SUBNET_ID)
                    or self.__get_provisioning_param_by_type(PRODUCT_PARAM_TYPE_AZ)
                )
            ):
                # Clear product attributes as provisioning fails and will be retriggered
                self._provisioned_product.scProvisionedProductId = None
                self._publish(
                    insufficient_capacity_reached.InsufficientCapacityReached(
                        projectId=self._provisioned_product.projectId,
                        provisionedProductId=self._provisioned_product.provisionedProductId,
                        productType=self._provisioned_product.provisionedProductType,
                        productName=self._provisioned_product.productName,
                        owner=self._provisioned_product.userId,
                        userIpAddress=self._provisioned_product.userIpAddress,
                    )
                )
                return

        if self.__warn_for(status=product_status.ProductStatus.ProvisioningError):
            return

        self.__fail(
            event=product_launch_failed.ProductLaunchFailed(
                projectId=self._provisioned_product.projectId,
                provisionedProductId=self._provisioned_product.provisionedProductId,
                provisionedCompoundProductId=self._provisioned_product.provisionedCompoundProductId,
                productName=self._provisioned_product.productName,
                productType=self._provisioned_product.provisionedProductType,
                owner=self._provisioned_product.userId,
            )
        )

    def fail_removal(
        self,
        command: fail_provisioned_product_removal_command.FailProvisionedProductRemovalCommand,
        products_srv: products_service.ProductsService,
    ):
        """Final step in removing a provisioned product if failed.

        Remove process:
        RemoveProvisionedProductCommand >
            DeprovisionProvisionedProductCommand >
            CompleteProvisionedProductRemovalCommand / FailProvisionedProductRemovalCommand.
        """
        self.__raise_if_entity_not_loaded_for(
            provisioned_product_id=command.provisioned_product_id,
        )

        has_remove_missing_signal_error = products_srv.has_provisioned_product_missing_removal_signal_error(
            provisioned_product_id=self._provisioned_product.scProvisionedProductId,
            aws_account_id=self._provisioned_product.awsAccountId,
            region=self._provisioned_product.region,
            user_id=self._provisioned_product.userId,
        )

        if has_remove_missing_signal_error:
            # In case remove action failed because of the missing signal error
            # the next deprovisioning will be successful
            self._provisioned_product.status = product_status.ProductStatus.Deprovisioning
            self._publish(
                provisioned_product_removal_retried.ProvisionedProductRemovalRetried(
                    provisionedProductId=self._provisioned_product.provisionedProductId
                )
            )
            return

        if self.__warn_for(status=product_status.ProductStatus.ProvisioningError):
            return

        self.__fail(
            event=provisioned_product_removal_failed.ProvisionedProductRemovalFailed(
                projectId=self._provisioned_product.projectId,
                provisionedProductId=self._provisioned_product.provisionedProductId,
                provisionedCompoundProductId=self._provisioned_product.provisionedCompoundProductId,
            )
        )

    def fail_update(
        self,
        command: fail_provisioned_product_update.FailProvisionedProductUpdateCommand,
        products_srv: products_service.ProductsService,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        container_mgmt_srv: container_management_service.ContainerManagementService,
    ):
        """Last step of updating a workbench if failed.
        Sets the status of the provisioned product to the status of the EC2 instance.
        When update fails, the old instance is still provisioned.

        Set to provisioning error if during update we can't find the EC2 instance.

        Workbench update processes:
        * UpdateProvisionedProductCommand >
            StopProvisionedProductForUpdateCommand >
            UpdateProvisionedProductCommand >
            CompleteProvisionedProductUpdateCommand / FailProvisionedProductUpdateCommand
        * AutoUpgradeProvisionedProductCommand >
            StopProvisionedProductForUpdateCommand >
            CompleteProvisionedProductUpdateCommand / FailProvisionedProductUpdateCommand
        """

        self.__raise_if_entity_not_loaded_for(
            provisioned_product_id=command.provisioned_product_id,
        )
        self.__raise_if_not(status=product_status.ProductStatus.Updating)

        try:

            self.__refresh_product_parameters(
                products_srv=products_srv,
                instance_mgmt_srv=instance_mgmt_srv,
                container_mgmt_srv=container_mgmt_srv,
            )
            if (
                self._provisioned_product.provisionedProductType != provisioned_product.ProvisionedProductType.Container
                and self._provisioned_product.blockDeviceMappings
                and self._provisioned_product.blockDeviceMappings.mappings
            ):

                if non_root_block_devices := [
                    d
                    for d in self._provisioned_product.blockDeviceMappings.mappings
                    if d.deviceName != self._provisioned_product.blockDeviceMappings.rootDeviceName
                ]:

                    for device in non_root_block_devices:
                        instance_mgmt_srv.attach_instance_volume(
                            user_id=self._provisioned_product.createdBy,
                            aws_account_id=self._provisioned_product.awsAccountId,
                            region=self._provisioned_product.region,
                            instance_id=self._provisioned_product.instanceId,
                            volume_id=device.volumeId,
                            device_name=device.deviceName,
                        )

            self._publish(
                provisioned_product_upgrade_failed.ProvisionedProductUpgradeFailed(
                    provisionedProductId=self._provisioned_product.provisionedProductId,
                )
            )
        except Exception as e:
            self._logger.exception("Unable to fetch provisioned product parameters after a failed upgrade.")

            self._provisioned_product.statusReason = str(e)
            self.__fail(
                provisioned_product_upgrade_failed.ProvisionedProductUpgradeFailed(
                    provisionedProductId=self._provisioned_product.provisionedProductId,
                )
            )

    def authorize_user_ip_address(
        self,
        command: authorize_user_ip_address_command.AuthorizeUserIpAddressCommand,
        parameter_srv: parameter_service.ParameterService,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        spoke_account_vpc_id_param_name: str,
        authorize_user_ip_address_param_value: bool,
    ):
        """Authorizes the user current IP address to access provisioned products.
        Connection options authorized:
            - ADB (TCP 6520)
            - Browser IDE (TCP 9443)
            - NICE DCV (TCP 8443)
            - QUIC (UDP 8444)
            - RDP (TCP 3389)
            - SSH (TCP 22)
            - WebRTC (TCP 8443, TCP 15550-15599, UDP 15550-15599)
        """

        if command.user_id.value != self._provisioned_product.createdBy:
            raise domain_exception.DomainException(
                f"User {command.user_id.value} is not authorized to authorize IP address "
                f"for provisioned product {self._provisioned_product.provisionedProductId}"
            )

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

    def cleanup_provisioned_product(
        self,
        command: cleanup_provisioned_products_command.CleanupProvisionedProductsCommand,
    ):
        """
        Delete dormant provisioned products
        Statuses we're looking for: PROVISIONING_ERROR, STOPPED
        """

        try:
            current_date = datetime.now(timezone.utc).date()

            # get number of days since provisioned_product.lastUpdateDate
            given_date = datetime.fromisoformat(self._provisioned_product.lastUpdateDate).date()
            dormant_period = (current_date - given_date).days

            if self._provisioned_product.status == product_status.ProductStatus.Stopped:
                _, cleanup_threshold = self.__select_limits(command.provisioned_product_cleanup_config.value)

                if dormant_period > cleanup_threshold:
                    # The provisioned product is too old and should be removed
                    self.__remove_dormant_pp()
        except Exception as e:

            self._logger.error(
                f"Unable to remove PP {self._provisioned_product.provisionedProductId} because: {str(e)}. Skipping..."
            )

            self._publish(provisioned_product_dormant_cleanup_failed.ProvisionedProductDormantCleanupFailed())

    """
    Helpers
    """

    def __get_new_version_distribution(
        self,
        versions_qs: versions_query_service.VersionsQueryService,
        product_id: str,
        region: str,
        stage: str,
    ):
        version_distributions = versions_qs.get_product_version_distributions(
            product_id=product_id,
            region=region,
            stage=version.VersionStage[stage],
        )

        newest_version_name = None
        newest_version = None
        for vers in version_distributions:
            if not newest_version_name or newest_version_name < semver.Version.parse(vers.versionName):
                newest_version_name = semver.Version.parse(vers.versionName)
                newest_version = vers

        return newest_version

    def __fail(self, event: message_bus.Message, reason: str | None = None):
        self._provisioned_product.status = product_status.ProductStatus.ProvisioningError
        self._provisioned_product.statusReason = reason
        self._publish(event)

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

    def __is_user_owner(self, user_id: user_id_value_object.UserIdValueObject | None = None) -> bool:
        return user_id and self._provisioned_product.userId.upper().strip() == user_id.value.upper().strip()

    def __is_user_admin_or_program_owner(
        self, user_roles: list[user_role_value_object.UserRoleValueObject] | None = None
    ) -> bool:
        return user_roles and any(
            [item.value in [VirtualWorkbenchRoles.Admin, VirtualWorkbenchRoles.ProgramOwner] for item in user_roles]
        )

    def __raise_if_not(
        self,
        status: product_status.ProductStatus | list[product_status.ProductStatus] | None = None,
        project_id: project_id_value_object.ProjectIdValueObject | None = None,
        user_id: user_id_value_object.UserIdValueObject | None = None,
        user_roles: list[user_role_value_object.UserRoleValueObject] | None = None,
    ):
        if status and type(status) is list and self._provisioned_product.status not in set(status):
            allowed_statuses = ", ".join(status)
            raise domain_exception.DomainException(
                f"Provisioned product {self._provisioned_product.provisionedProductId} must be in one of {allowed_statuses} states (current state: {self._provisioned_product.status})"
            )

        if status and type(status) is not list and self._provisioned_product.status != status:
            raise domain_exception.DomainException(
                f"Provisioned product {self._provisioned_product.provisionedProductId} must be in {status} state (current state: {self._provisioned_product.status})"
            )

        if project_id and project_id.value != self._provisioned_product.projectId:
            raise domain_exception.DomainException(
                "Provided project ID is different from the provisioned product project ID"
            )

        # raise exception only when user is not owner or role is not admin/product owner
        if (
            user_id
            and not self.__is_user_owner(user_id=user_id)
            and not self.__is_user_admin_or_program_owner(user_roles=user_roles)
        ):
            raise domain_exception.DomainException("User is not allowed to modify the requested provisioned product.")

    def __raise_for(
        self,
        status: product_status.ProductStatus | None = None,
    ):
        if status and self._provisioned_product.status == status:
            raise domain_exception.DomainException(
                f"Requested provisioned product cannot be in {status} state to do the action."
            )

    def __warn_for(self, status: product_status.ProductStatus):
        if self._provisioned_product.status == status:
            self._logger.warning(
                {
                    "provisionedProductId": self._provisioned_product.provisionedProductId,
                    "provisionedProductStatus": self._provisioned_product.status,
                    "message": f"Provisioned product is already in {self._provisioned_product.status} status. Ignoring.",
                }
            )
            return True
        return False

    def __warn_if_not(self, status: product_status.ProductStatus):
        if self._provisioned_product.status != status:
            self._logger.warning(
                {
                    "provisionedProductId": self._provisioned_product.provisionedProductId,
                    "status": self._provisioned_product.status,
                    "message": f"Provisioned product is not in {status} status. Ignoring.",
                }
            )
            return True
        return False

    def _repository_actions(self):
        """Logic to persist the aggregate state in the database

        This function is called by the AggregatePublisher class when it wants to store the data in DB.
        Handles create and update entity scenarios.
        """
        current_time = datetime.now(timezone.utc).isoformat()

        if self._original_product and self._original_product.dict() != self._product.dict():
            self._pending_updates.append(
                lambda uow: uow.get_repository(product.ProductPrimaryKey, product.Product).update_entity(
                    pk=product.ProductPrimaryKey(
                        projectId=self._product.projectId,
                        productId=self._product.productId,
                    ),
                    entity=self._product,
                )
            )
            self._original_product = self._product.copy(deep=True)

        if self._original_user_profile is None and self._user_profile:
            self._user_profile.createDate = current_time
            self._user_profile.lastUpdateDate = current_time
            self._pending_updates.append(
                lambda uow: uow.get_repository(user_profile.UserProfilePrimaryKey, user_profile.UserProfile).add(
                    self._user_profile
                )
            )

            self._original_user_profile = self._user_profile.copy(deep=True)
        elif (
            self._original_user_profile
            and self._user_profile
            and self._original_user_profile.dict() != self._user_profile.dict()
        ):
            self._user_profile.createDate = current_time
            self._user_profile.lastUpdateDate = current_time

            self._pending_updates.append(
                lambda uow: uow.get_repository(
                    user_profile.UserProfilePrimaryKey, user_profile.UserProfile
                ).update_entity(
                    pk=user_profile.UserProfilePrimaryKey(userId=self._user_profile.userId),
                    entity=self._user_profile,
                )
            )
            self._original_user_profile = self._user_profile.copy(deep=True)

        if self._original_provisioned_product is None and self._provisioned_product:
            current_time = datetime.now(timezone.utc).isoformat()
            self._provisioned_product.lastUpdateDate = current_time
            self._provisioned_product.createDate = current_time

            self._pending_updates.append(
                lambda uow: uow.get_repository(
                    provisioned_product.ProvisionedProductPrimaryKey,
                    provisioned_product.ProvisionedProduct,
                ).add(self._provisioned_product)
            )

            self._original_provisioned_product = self._provisioned_product.copy(deep=True)
            return

        if self._provisioned_product:
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

    """
    Handling of provisioned product output parameters.
    """

    def __refresh_product_parameters(
        self,
        products_srv: products_service.ProductsService,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        container_mgmt_srv: container_management_service.ContainerManagementService,
        refresh_status: bool = True,
    ):
        """
        Gets outputs of a provisioned product and tries to parse the private IP, instance ID and status.
        """
        if not self._provisioned_product.scProvisionedProductId:
            raise domain_exception.DomainException(
                f"Provisioned product {self._provisioned_product.provisionedProductId} is not provisioned in Service Catalog."
            )

        if self._provisioned_product.status not in product_status.PRODUCT_PROVISION_PROGRESS_STATES:
            raise domain_exception.DomainException(
                f"Provisioned product {self._provisioned_product.provisionedProductId} must be in one of {product_status.PRODUCT_PROVISION_PROGRESS_STATES} states, but is in {self._provisioned_product.status} state"
            )
        self.__refresh_product_outputs(products_srv=products_srv)
        match self._provisioned_product.provisionedProductType:
            case p if p in provisioned_product.PRODUCT_CONTAINER_TYPES:
                self.__refresh_container_product_service_name()
                self.__refresh_container_product_cluster_name()
                self.__refresh_container_parameters(container_mgmt_srv=container_mgmt_srv)
            case p if p in provisioned_product.PRODUCT_INSTANCE_TYPES:
                self.__refresh_product_instance_id()
                self.__refresh_ssh_key_path()
                self.__refresh_ssh_key_id()
                self.__refresh_user_credential_name()
                self.__refresh_instance_parameters(instance_mgmt_srv=instance_mgmt_srv, refresh_status=refresh_status)

    def __refresh_product_outputs(self, products_srv: products_service.ProductsService):
        self._provisioned_product.outputs = products_srv.get_provisioned_product_outputs(
            provisioned_product_id=self._provisioned_product.scProvisionedProductId,
            user_id=self._provisioned_product.createdBy,
            aws_account_id=self._provisioned_product.awsAccountId,
            region=self._provisioned_product.region,
        )

    def __refresh_product_instance_id(self):
        self._provisioned_product.instanceId = next(
            (
                output.outputValue
                for output in self._provisioned_product.outputs
                if re.match(PRODUCT_OUTPUT_INSTANCE_ID_REGEX, output.outputValue, flags=re.I)
            ),
            None,
        )

    def __refresh_container_product_service_name(self):
        self._provisioned_product.containerServiceName = next(
            (
                output.outputValue
                for output in self._provisioned_product.outputs
                if output.outputKey.strip().lower() == PRODUCT_PARAM_NAME_CONTAINER_SERVICE_NAME.lower()
            ),
            None,
        )

    def __refresh_container_product_cluster_name(self):
        self._provisioned_product.containerClusterName = next(
            (
                output.outputValue
                for output in self._provisioned_product.outputs
                if output.outputKey.strip().lower() == PRODUCT_PARAM_NAME_CONTAINER_CLUSTER_NAME.lower()
            ),
            None,
        )

    def __refresh_ssh_key_path(self):
        self._provisioned_product.sshKeyPath = next(
            (
                output.outputValue
                for output in self._provisioned_product.outputs
                if output.outputKey.strip().lower() == PRODUCT_OUTPUT_SSH_KEY_NAME.lower()
            ),
            None,
        )

    def __refresh_ssh_key_id(self):
        self._provisioned_product.keyPairId = next(
            (
                output.outputValue
                for output in self._provisioned_product.outputs
                if output.outputKey.strip().lower() == PRODUCT_OUTPUT_SSH_KEY_ID.lower()
            ),
            None,
        )

    def __refresh_user_credential_name(self):
        self._provisioned_product.userCredentialName = next(
            (
                output.outputValue
                for output in self._provisioned_product.outputs
                if output.outputKey.strip().lower() == PRODUCT_OUTPUT_USER_CREDENTIALS_NAME.lower()
            ),
            None,
        )

    def __refresh_container_parameters(
        self,
        container_mgmt_srv: container_management_service.ContainerManagementService,
    ):
        if not self._provisioned_product.containerServiceName:
            return

        if not self._provisioned_product.containerClusterName:
            return

        self.__get_container_details(container_mgmt_srv=container_mgmt_srv)

        if not self._container:
            raise domain_exception.DomainException(
                f"Container {self._provisioned_product.containerServiceName} not found."
            )

        self._provisioned_product.privateIp = self._container.private_ip_address
        self._provisioned_product.status = provisioning_helpers.map_provisioned_product_container_type_status(
            self._container
        )
        self._provisioned_product.containerName = self._container.name
        self._provisioned_product.containerTaskArn = self._container.task_arn

    def __get_container_details(
        self,
        container_mgmt_srv: container_management_service.ContainerManagementService,
    ):
        if not self._provisioned_product.containerServiceName:
            return

        if not self._container:
            self._container = container_mgmt_srv.get_container_details(
                aws_account_id=self._provisioned_product.awsAccountId,
                region=self._provisioned_product.region,
                cluster_name=self._provisioned_product.containerClusterName,
                service_name=self._provisioned_product.containerServiceName,
                user_id=self._provisioned_product.userId,
            )

        return self._container

    def __refresh_instance_parameters(
        self,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        refresh_status: bool = True,
    ):
        if not self._provisioned_product.instanceId:
            return

        self.__get_instance_details(instance_mgmt_srv=instance_mgmt_srv)

        if not self._instance:
            raise domain_exception.DomainException(f"Instance {self._provisioned_product.instanceId} not found.")

        self._provisioned_product.privateIp = self._instance.private_ip_address
        self._provisioned_product.publicIp = self._instance.public_ip_address
        if refresh_status:
            self._provisioned_product.status = provisioning_helpers.map_provisioned_product_instance_type_status(
                self._instance
            )

    def __get_instance_details(self, instance_mgmt_srv: instance_management_service.InstanceManagementService):
        if not self._provisioned_product.instanceId:
            return

        if not self._instance:
            self._instance = instance_mgmt_srv.get_instance_details(
                instance_id=self._provisioned_product.instanceId,
                user_id=self._provisioned_product.createdBy,
                aws_account_id=self._provisioned_product.awsAccountId,
                region=self._provisioned_product.region,
            )

        return self._instance

    """
    Handling of user and technical provisioning parameters
    """

    def __set_technical_product_provisioning_parameters(
        self,
        parameter_srv: parameter_service.ParameterService,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        spoke_account_vpc_id_param_name: str,
        subnet_selector: networking_helpers.SubnetSelector,
    ):
        self.__set_user_security_group_id(
            parameter_srv=parameter_srv,
            instance_mgmt_srv=instance_mgmt_srv,
            spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
        )
        self.__set_subnet_id(
            parameter_srv=parameter_srv,
            instance_mgmt_srv=instance_mgmt_srv,
            spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
            subnet_selector=subnet_selector,
        )
        self.__set_subnets_ids(
            parameter_srv=parameter_srv,
            instance_mgmt_srv=instance_mgmt_srv,
            spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
            subnet_selector=subnet_selector,
        )
        self.__set_availability_zone(
            parameter_srv=parameter_srv,
            instance_mgmt_srv=instance_mgmt_srv,
            spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
            subnet_selector=subnet_selector,
        )
        self.__set_user_tid_in_provisioning_params(user_tid=self._provisioned_product.createdBy)
        self.__set_allocated_private_ip_address(instance_mgmt_srv=instance_mgmt_srv)

    def __set_user_security_group_id(
        self,
        parameter_srv: parameter_service.ParameterService,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        spoke_account_vpc_id_param_name: str,
    ):
        """
        Sets user security group id in provisioning parameters by creating/fetching it in target account
        """
        # Get VPC Id in the target account and region
        vpc_id = self.__get_spoke_vpc_id(
            parameter_srv=parameter_srv,
            spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
        )

        # Check to see if the security group exists in the target account
        user_sg_id = instance_mgmt_srv.get_user_security_group_id(
            user_id=self._provisioned_product.userId,
            aws_account_id=self._provisioned_product.awsAccountId,
            region=self._provisioned_product.region,
            vpc_id=vpc_id,
        )

        # Create the security group in the target account if does not exist
        if not user_sg_id:
            user_sg_id = instance_mgmt_srv.create_user_security_group(
                user_id=self._provisioned_product.userId,
                aws_account_id=self._provisioned_product.awsAccountId,
                region=self._provisioned_product.region,
                vpc_id=vpc_id,
            )

        if self._provisioned_product.status == product_status.ProductStatus.Provisioning:
            self.__set_user_security_group_id_in_provisioning_params(user_sg_id=user_sg_id)

        if self._provisioned_product.status == product_status.ProductStatus.Updating:
            self.__set_user_security_group_id_in_upgrading_params(user_sg_id=user_sg_id)

    def __set_user_security_group_id_in_provisioning_params(self, user_sg_id: str):
        # Set UserSecurityGroupId parameter if it exists as provisioning parameter
        user_sg_param = next(
            (
                param
                for param in self._provisioned_product.provisioningParameters or []
                if param.key == PRODUCT_PARAM_NAME_SECURITY_GROUP
            ),
            None,
        )
        if user_sg_param:
            user_sg_param.value = user_sg_id

    def __set_user_tid_in_provisioning_params(self, user_tid: str):
        # Set UserTid parameter if it exists as a provisioning parameter
        user_tid_param = next(
            (
                param
                for param in self._provisioned_product.provisioningParameters or []
                if param.key == PRODUCT_PARAM_NAME_OWNER_TID
            ),
            None,
        )
        if user_tid_param:
            user_tid_param.value = user_tid

    def __set_user_security_group_id_in_upgrading_params(self, user_sg_id: str):
        # Set UserSecurityGroupId parameter if it exists as upgrading parameter
        user_sg_param = next(
            (
                param
                for param in self._provisioned_product.newProvisioningParameters or []
                if param.key == PRODUCT_PARAM_NAME_SECURITY_GROUP
            ),
            None,
        )
        if user_sg_param:
            user_sg_param.value = user_sg_id

    def __set_subnet_id(
        self,
        parameter_srv: parameter_service.ParameterService,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        spoke_account_vpc_id_param_name: str,
        subnet_selector: networking_helpers.SubnetSelector,
    ):
        """
        Sets a subnet ID for a product parameter of type AWS::EC2::Subnet::Id.
        If there are more than one parameter of this type, raises domain error.
        If product does not have a Subnet ID parameter, returns.
        """

        if not (subnet_id_param := self.__get_provisioning_param_by_type(PRODUCT_PARAM_TYPE_SUBNET_ID)):
            return

        if self._provisioned_product.status == product_status.ProductStatus.Updating:
            """
            Upgrade flow needs to reuse the subnet ID from provisioning.
            This is to avoid changing AZ parameter on the EBS volume.
            """
            subnet_id_param_from_provisioning = next(
                (
                    p
                    for p in self._provisioned_product.provisioningParameters or []
                    if p.isTechnicalParameter and p.parameterType == PRODUCT_PARAM_TYPE_SUBNET_ID
                ),
                None,
            )
            if subnet_id_param_from_provisioning:
                subnet_id_param.value = subnet_id_param_from_provisioning.value
                return

        """
        In all other cases fetching subnet with the most remaining IPs.
        """
        target_param = self.__get_subnet_for_provisioning(
            parameter_srv=parameter_srv,
            instance_mgmt_srv=instance_mgmt_srv,
            spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
            subnet_selector=subnet_selector,
        )
        if target_param:
            subnet_id_param.value = target_param.subnet_id

    def __set_subnets_ids(
        self,
        parameter_srv: parameter_service.ParameterService,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        spoke_account_vpc_id_param_name: str,
        subnet_selector: networking_helpers.SubnetSelector,
    ):
        """
        Sets the subnets IDs for a product parameter of type List<AWS::EC2::Subnet::Id>.
        If there are more than one parameter of this type, raises domain error.
        If product does not have a Subnets IDs parameter, returns.
        """

        if not (subnets_ids_param := self.__get_provisioning_param_by_type(PRODUCT_PARAM_TYPE_SUBNETS_ID)):
            return

        if self._provisioned_product.status == product_status.ProductStatus.Updating:
            """
            Upgrade flow needs to reuse the subnets IDs from provisioning.
            This is to avoid changing AZ parameter on the EBS volume.
            """
            subnets_ids_param_from_provisioning = next(
                (
                    p
                    for p in self._provisioned_product.provisioningParameters or []
                    if p.isTechnicalParameter and p.parameterType == PRODUCT_PARAM_TYPE_SUBNETS_ID
                ),
                None,
            )
            if subnets_ids_param_from_provisioning:
                subnets_ids_param.value = subnets_ids_param_from_provisioning.value
                return

        """
        In all other cases fetching subnet with the most remaining IPs.
        """
        target_param = self.__get_subnets_for_provisioning(
            parameter_srv=parameter_srv,
            instance_mgmt_srv=instance_mgmt_srv,
            spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
            subnet_selector=subnet_selector,
        )
        if target_param:
            subnets_ids_param.value = ",".join([subnet.subnet_id for subnet in target_param])

    def __set_availability_zone(
        self,
        parameter_srv: parameter_service.ParameterService,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        spoke_account_vpc_id_param_name: str,
        subnet_selector: networking_helpers.SubnetSelector,
    ):
        """
        Sets an AZ name for product parameter of type AWS::EC2::AvailabilityZone::Name.
        If there are more than one parameter of this type, raises domain error.
        If product does not have an AZ parameter, returns.
        """

        if not (az_param := self.__get_provisioning_param_by_type(PRODUCT_PARAM_TYPE_AZ)):
            return

        if self._provisioned_product.status == product_status.ProductStatus.Updating:
            """
            Upgrade flow needs to reuse the AZ from provisioning parameter.
            This is to avoid changing AZ parameter on the EBS volume.
            """
            az_name_param_from_provisioning = next(
                (
                    p
                    for p in self._provisioned_product.provisioningParameters or []
                    if p.isTechnicalParameter and p.parameterType == PRODUCT_PARAM_TYPE_AZ
                ),
                None,
            )
            if az_name_param_from_provisioning:
                az_param.value = az_name_param_from_provisioning.value
                return

            """
            If AZ parameter is not in the provisioning parameters, checking if there is a Subnet ID param to match.
            """
            subnet_id_param_from_provisioning = next(
                (
                    p
                    for p in self._provisioned_product.provisioningParameters or []
                    if p.isTechnicalParameter and p.parameterType == PRODUCT_PARAM_TYPE_SUBNET_ID
                ),
                None,
            )
            if subnet_id_param_from_provisioning:
                spoke_subnets = self.__get_spoke_subnets(
                    parameter_srv=parameter_srv,
                    instance_mgmt_srv=instance_mgmt_srv,
                    spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
                )

                if not (
                    spoke_subnet := next(
                        (s for s in spoke_subnets if s.subnet_id == subnet_id_param_from_provisioning.value),
                        None,
                    )
                ):
                    raise domain_exception.DomainException(
                        "Provisioned product was launched in a subnet that no longer exists in the spoke account."
                    )

                az_param.value = spoke_subnet.availability_zone
                return

        """
        In all other cases, fetching AZ of a private subnet with the most IPs.
        """
        target_param = self.__get_subnet_for_provisioning(
            parameter_srv=parameter_srv,
            instance_mgmt_srv=instance_mgmt_srv,
            spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
            subnet_selector=subnet_selector,
        )
        if target_param:
            az_param.value = target_param.availability_zone

    def __set_allocated_private_ip_address(
        self,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
    ):
        """
        Finds an unallocated IP address in the chosen subnet.
        """

        allocated_ip_address_param = self.__get_provisioning_param_by_name(name=PRODUCT_PARAM_NAME_VEW_ALLOCATED_IP)
        if not allocated_ip_address_param:
            return

        if self._provisioned_product.status == product_status.ProductStatus.Updating:
            """
            Upgrade flow needs to reuse the IP from provisioning parameter.
            """
            ip_from_provisioning_param = next(
                (
                    p
                    for p in self._provisioned_product.provisioningParameters or []
                    if p.isTechnicalParameter and p.key == PRODUCT_PARAM_NAME_VEW_ALLOCATED_IP
                ),
                None,
            )
            if ip_from_provisioning_param:
                allocated_ip_address_param.value = ip_from_provisioning_param.value
                return

        if not (subnet_id_param := self.__get_provisioning_param_by_type(PRODUCT_PARAM_TYPE_SUBNET_ID)):
            raise domain_exception.DomainException(
                "Product must contain subnet ID parameter to pre-allocate an IP address."
            )

        if not (
            subnet := instance_mgmt_srv.describe_subnet(
                user_id=self._provisioned_product.userId,
                aws_account_id=self._provisioned_product.awsAccountId,
                region=self._provisioned_product.region,
                subnet_id=subnet_id_param.value,
            )
        ):
            raise domain_exception.DomainException(
                f"Subnet {subnet_id_param.value} for provisioning to allocate IP address not found"
            )

        network_interfaces = instance_mgmt_srv.describe_subnet_interfaces(
            user_id=self._provisioned_product.userId,
            aws_account_id=self._provisioned_product.awsAccountId,
            region=self._provisioned_product.region,
            subnet_id=subnet_id_param.value,
        )
        taken_ips = {pa.private_ip_address for ni in network_interfaces for pa in ni.private_ip_addresses}

        network = ipaddress.IPv4Network(subnet.cidr_block)
        available_ips = {str(ip) for ip in network.hosts() if not str(ip).endswith((".1", ".2", ".3"))}

        available_ips -= taken_ips

        if not available_ips:
            raise domain_exception.DomainException("No available IP addresses in the subnet.")

        self._provisioned_product.privateIp = random.choice(list(available_ips))
        allocated_ip_address_param.value = self._provisioned_product.privateIp

    def __get_provisioning_param_by_type(self, type: str):
        params = []
        if self._provisioned_product.status == product_status.ProductStatus.Provisioning:
            params = [
                p
                for p in self._provisioned_product.provisioningParameters or []
                if p.parameterType == type and p.isTechnicalParameter
            ]

        if self._provisioned_product.status == product_status.ProductStatus.Updating:
            params = [
                p
                for p in self._provisioned_product.newProvisioningParameters or []
                if p.parameterType == type and p.isTechnicalParameter
            ]

        if len(params) > 1:
            """
            Currently handling only one instance of a technical parameter.
            """
            raise domain_exception.DomainException(f"More than one {type} parameter found in the product parameters.")

        return params.pop() if params else None

    def __get_provisioning_param_by_name(self, name: str):
        params = []
        if self._provisioned_product.status == product_status.ProductStatus.Provisioning:
            params = [
                p
                for p in self._provisioned_product.provisioningParameters or []
                if p.key == name and p.isTechnicalParameter
            ]

        if self._provisioned_product.status == product_status.ProductStatus.Updating:
            params = [
                p
                for p in self._provisioned_product.newProvisioningParameters or []
                if p.key == name and p.isTechnicalParameter
            ]

        if len(params) > 1:
            """
            Currently handling only one instance of a technical parameter.
            """
            raise domain_exception.DomainException(f"More than one {name} parameter found in the product parameters.")

        return params.pop() if params else None

    def __validate_and_map_input_parameters(
        self,
        provisioning_parameters: list[provisioning_parameters_value_object.ProvisioningParameter],
        product_parameters: list[version.VersionParameter],
        current_provisioned_parameters: list[provisioning_parameters_value_object.ProvisioningParameter] | None = None,
    ):
        if not current_provisioned_parameters:
            current_provisioned_parameters = []

        product_helpers.validate_provisioning_parameters(
            requested_provisioning_parameters=provisioning_parameters,
            product_provisioning_parameters=product_parameters,
        )

        return product_helpers.map_provisioning_parameters(
            requested_provisioning_parameters=provisioning_parameters,
            current_provisioned_parameters=current_provisioned_parameters,
            product_provisioning_parameters=product_parameters,
        )

    def __update_user_profile(self):
        if not self._vpc_subnet_for_provisioning:
            return

        if not self._user_profile:
            self._user_profile = user_profile.UserProfile(
                userId=self._provisioned_product.userId,
                preferredRegion=self._provisioned_product.region,
                createDate=datetime.now(timezone.utc).isoformat(),
                lastUpdateDate=datetime.now(timezone.utc).isoformat(),
                preferredAvailabilityZone=self._vpc_subnet_for_provisioning.availability_zone,
            )
        elif not self._user_profile.preferredAvailabilityZone:
            self._user_profile.preferredAvailabilityZone = self._vpc_subnet_for_provisioning.availability_zone

    """
    Spoke account networking resource fetchers
    """

    def __get_subnet_for_provisioning(
        self,
        parameter_srv: parameter_service.ParameterService,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        spoke_account_vpc_id_param_name: str,
        subnet_selector: networking_helpers.SubnetSelector,
    ):
        """
        Gets private subnet in the spoke account VPC that has the most remaining IPs.

        Only the following subnets are considered:
        * Must be in a VPC that is set as the one to be used during account on-boarding.
        * Must not have a route to an internet gateway,
        * Must have a transit gateway attachment.

        Returns a subnet with the most IPs in the spoke account.

        :param parameter_srv: Parameter service
        :param instance_mgmt_srv: Instance management service
        :param spoke_account_vpc_id_param_name: Spoke account VPC ID parameter name
        """
        if self._vpc_subnet_for_provisioning:
            return self._vpc_subnet_for_provisioning

        self._available_subnets_ordered_by_ip_count = subnet_selector(
            route_tables=self.__get_spoke_route_tables(
                parameter_srv=parameter_srv,
                instance_mgmt_srv=instance_mgmt_srv,
                spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
            ),
            subnets=self.__get_spoke_subnets(
                parameter_srv=parameter_srv,
                instance_mgmt_srv=instance_mgmt_srv,
                spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
            ),
        )
        # Check which availability zones were already used for provisioning and
        # pick the next one with the highest available IPs count
        already_tried_availability_zones = (
            [az for az in self._provisioned_product.availabilityZonesTriggered]
            if self._provisioned_product.availabilityZonesTriggered
            else []
        )

        # first try selecting subnet by user's AZ
        if (
            self._user_profile
            and self._user_profile.preferredAvailabilityZone
            and self._user_profile.preferredAvailabilityZone not in already_tried_availability_zones
        ):
            self._vpc_subnet_for_provisioning = next(
                (
                    s
                    for s in self._available_subnets_ordered_by_ip_count
                    if s.availability_zone == self._user_profile.preferredAvailabilityZone
                    and s.available_ip_address_count > 0
                ),
                None,
            )

        # try selecting from the remaining
        if not self._vpc_subnet_for_provisioning:
            self._vpc_subnet_for_provisioning = next(
                (
                    s
                    for s in self._available_subnets_ordered_by_ip_count
                    if s.availability_zone not in already_tried_availability_zones
                ),
                None,
            )

        return self._vpc_subnet_for_provisioning

    def __get_subnets_for_provisioning(
        self,
        parameter_srv: parameter_service.ParameterService,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        spoke_account_vpc_id_param_name: str,
        subnet_selector: networking_helpers.SubnetSelector,
    ):
        """
        Gets private subnets in the spoke account VPC.

        Only the following subnets are considered:
        * Must be in a VPC that is set as the one to be used during account on-boarding.
        * Must not have a route to an internet gateway,
        * Must have a transit gateway attachment.

        :param parameter_srv: Parameter service
        :param instance_mgmt_srv: Instance management service
        :param spoke_account_vpc_id_param_name: Spoke account VPC ID parameter name
        """
        if not self._vpc_subnet_for_provisioning:
            self._available_subnets_ordered_by_ip_count = subnet_selector(
                route_tables=self.__get_spoke_route_tables(
                    parameter_srv=parameter_srv,
                    instance_mgmt_srv=instance_mgmt_srv,
                    spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
                ),
                subnets=self.__get_spoke_subnets(
                    parameter_srv=parameter_srv,
                    instance_mgmt_srv=instance_mgmt_srv,
                    spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
                ),
            )

        return self._available_subnets_ordered_by_ip_count

    def __get_spoke_vpc_id(
        self,
        parameter_srv: parameter_service.ParameterService,
        spoke_account_vpc_id_param_name: str,
    ):
        # Get VPC Id in the target account and region
        if not self._vpc_id:
            self._vpc_id = parameter_srv.get_parameter_value(
                parameter_name=spoke_account_vpc_id_param_name,
                aws_account_id=self._provisioned_product.awsAccountId,
                region=self._provisioned_product.region,
                user_id=self._provisioned_product.userId,
            )

        return self._vpc_id

    def __get_spoke_subnets(
        self,
        parameter_srv: parameter_service.ParameterService,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        spoke_account_vpc_id_param_name: str,
    ):
        if not self._vpc_subnets:
            vpc_id = self.__get_spoke_vpc_id(
                parameter_srv=parameter_srv,
                spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
            )

            self._vpc_subnets = instance_mgmt_srv.describe_vpc_subnets(
                user_id=self._provisioned_product.userId,
                aws_account_id=self._provisioned_product.awsAccountId,
                region=self._provisioned_product.region,
                vpc_id=vpc_id,
            )

        return self._vpc_subnets

    def __get_spoke_route_tables(
        self,
        parameter_srv: parameter_service.ParameterService,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        spoke_account_vpc_id_param_name: str,
    ):
        if not self._route_tables:
            vpc_id = self.__get_spoke_vpc_id(
                parameter_srv=parameter_srv,
                spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
            )

            self._route_tables = instance_mgmt_srv.describe_vpc_route_tables(
                user_id=self._provisioned_product.userId,
                aws_account_id=self._provisioned_product.awsAccountId,
                region=self._provisioned_product.region,
                vpc_id=vpc_id,
            )

        return self._route_tables

    def __get_version_distribution(
        self,
        versions_qs: versions_query_service.VersionsQueryService,
        product_id: str,
        version_id: str,
        region: str,
        stage: str,
    ):
        version_distribution = next(
            iter(
                versions_qs.get_product_version_distributions(
                    product_id=product_id,
                    version_id=version_id,
                    region=region,
                    stage=version.VersionStage[stage],
                )
            ),
            None,
        )

        if not version_distribution:
            raise domain_exception.DomainException(
                f"Product version {version_id} is not published to {stage} {region} or was retired. Update product version."
            )

        return version_distribution

    def _update_provisioning_time_stats(
        self,
    ):
        current_time = datetime.now(timezone.utc).isoformat()
        self._provisioned_product.lastUpdateDate = current_time
        provisioning_time = int(
            (
                datetime.fromisoformat(self._provisioned_product.lastUpdateDate)
                - datetime.fromisoformat(self._provisioned_product.createDate)
            ).total_seconds()
        )
        if self._product.averageProvisioningTime:
            old_average_provisioning_time = self._product.averageProvisioningTime
            old_total_reported_times = self._product.totalReportedTimes
            new_total_reported_times = old_total_reported_times + 1
            new_average_provisioning_time = int(
                (provisioning_time + (old_total_reported_times * old_average_provisioning_time))
                / new_total_reported_times
            )
            self._product.averageProvisioningTime = new_average_provisioning_time
            self._product.totalReportedTimes = new_total_reported_times
        else:
            self._product.averageProvisioningTime = provisioning_time
            self._product.totalReportedTimes = 1

    def __get_experimental_provisionining_parameter_value(
        self,
        provisioning_parameters: list[provisioning_parameters_value_object.ProvisioningParameter],
    ):
        """Logic to get the experimental provisioning parameter value.

        This function is called during the launch of a product and checks if
        EXPERIMENTAL_INPUT_PARAM_NAME has been passed as provisioning parameter.
        Default value is None.
        """
        experimental_param = next(
            (param for param in provisioning_parameters or [] if param.key == EXPERIMENTAL_INPUT_PARAM_NAME),
            None,
        )
        if experimental_param:
            match experimental_param.value:
                case provisioned_product.ExperimentalEnum.TRUE:
                    return True
                case provisioned_product.ExperimentalEnum.FALSE:
                    return False
                case _:
                    return None
        else:
            return None

    def __raise_if_experimental_product_attempted_provisioning_in_not_allow_stage(
        self,
        stage: provisioned_product.ProvisionedProductStage,
    ):
        """Logic to raise an exception if an experimental product is attempted to
        be provisioned in a non-QA stage.

        This function is called during the launch of a product and checks if the
        stage is not QA: if it is, an exception is raised.
        """
        if stage != provisioned_product.ProvisionedProductStage.QA:
            raise domain_exception.DomainException("Experimental products can be provisioned only in QA stage.")

    def __raise_if_experimental_provisioned_product_project_limit_exceeded(
        self,
        project_id: str,
        provisioned_products_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
        experimental_provisioned_product_per_project_limit: int,
    ):
        """Logic to raise an exception if the project limit for experimental
        workbenches has been exceeded.

        This function is called during the launch of a product and checks if
        the project limit for experimental workbenches has been exceeded. If it
        has, an exception is raised.
        """
        if (
            len(
                provisioned_products_qs.get_provisioned_products_by_project_id(
                    project_id=project_id,
                    exclude_status=[
                        product_status.ProductStatus.ProvisioningError,
                        product_status.ProductStatus.InstanceError,
                        product_status.ProductStatus.Terminated,
                    ],
                    experimental=True,
                )
            )
            >= experimental_provisioned_product_per_project_limit
        ):
            raise domain_exception.DomainException(
                "The maximum amount of experimental provisioned products per program has been reached. Contact the program owner for assistance."
            )

    def __request_additional_configuration(self):
        self._provisioned_product.status = product_status.ProductStatus.Provisioning
        self._publish(
            provisioned_product_configuration_requested.ProvisionedProductConfigurationRequested(
                provisionedProductId=self._provisioned_product.provisionedProductId
            )
        )

    """
    Handling dormant provisioned products removing
    """

    def __remove_dormant_pp(self):
        self._provisioned_product.status = product_status.ProductStatus.Deprovisioning
        self._provisioned_product.lastUpdatedBy = CLEANUP_ERROR_PROVISIONED_PRODUCT
        self._publish(
            provisioned_product_removal_started.ProvisionedProductRemovalStarted(
                provisionedProductId=self._provisioned_product.provisionedProductId
            )
        )

    def __select_limits(self, provisioned_product_cleanup_config: dict):
        if self._provisioned_product.experimental:
            notification_age = provisioned_product_cleanup_config["pp-experimental-cleanup-alert"]
            cleanup_age = provisioned_product_cleanup_config["pp-experimental-cleanup"]
        else:
            notification_age = provisioned_product_cleanup_config["pp-cleanup-alert"]
            cleanup_age = provisioned_product_cleanup_config["pp-cleanup"]

        return notification_age, cleanup_age
