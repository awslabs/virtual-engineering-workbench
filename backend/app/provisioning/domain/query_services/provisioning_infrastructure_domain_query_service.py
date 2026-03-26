from app.provisioning.domain.aggregates.internal import networking_helpers
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import network_subnet
from app.provisioning.domain.ports import instance_management_service, parameter_service
from app.provisioning.domain.value_objects import account_id_value_object, region_value_object


class ProvisioningInfrastructureDomainQueryService:

    def __init__(
        self,
        parameter_srv: parameter_service.ParameterService,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        all_subnets_selector: networking_helpers.AllSubnetsSelector,
        spoke_account_vpc_id_param_name: str,
        service_name: str,
    ) -> None:
        self._parameter_srv = parameter_srv
        self._instance_mgmt_srv = instance_mgmt_srv
        self._all_subnets_selector = all_subnets_selector
        self._spoke_account_vpc_id_param_name = spoke_account_vpc_id_param_name
        self._service_name = service_name

    def get_provisioning_subnets_in_account(
        self, account_id: account_id_value_object.AccountIdValueObject, region: region_value_object.RegionValueObject
    ) -> list[network_subnet.NetworkSubnet]:

        vpc_id = self._parameter_srv.get_parameter_value(
            parameter_name=self._spoke_account_vpc_id_param_name,
            aws_account_id=account_id.value,
            region=region.value,
            user_id=self._service_name,
        )

        if not vpc_id:
            raise domain_exception.DomainException(
                f"Unable to fetch VPC ID from the spoke account {account_id.value} region {region.value}"
            )

        subnets = self._instance_mgmt_srv.describe_vpc_subnets(
            aws_account_id=account_id.value,
            region=region.value,
            vpc_id=vpc_id,
            user_id=self._service_name,
        )

        route_tables = self._instance_mgmt_srv.describe_vpc_route_tables(
            aws_account_id=account_id.value,
            region=region.value,
            vpc_id=vpc_id,
            user_id=self._service_name,
        )

        return self._all_subnets_selector(route_tables, subnets)
