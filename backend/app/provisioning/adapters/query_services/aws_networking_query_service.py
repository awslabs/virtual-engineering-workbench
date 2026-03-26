import json
from typing import Dict

from aws_lambda_powertools import logging

from app.provisioning.adapters.exceptions import adapter_exception
from app.provisioning.domain.ports import networking_query_service
from app.shared.api import ssm_parameter_service


class AWSNetworkingService(networking_query_service.NetworkingQueryService):
    """Secondary adapter for Virtual Workbench networking functionality based on AWS."""

    def __init__(
        self,
        ssm_api: ssm_parameter_service.SSMApi,
        network_ip_map_param_name: str,
        logger: logging.Logger,
        available_networks_param_name: str = "",
    ) -> None:
        self._ssm_api = ssm_api
        self._network_ip_map_param_name = network_ip_map_param_name
        self._logger = logger
        self._available_networks_param_name = available_networks_param_name

    def get_network_ip_address_mapping(self) -> Dict:
        """Returns a dictionary of IP address mapping between networks from SSM Parameter Store."""

        try:
            result = json.loads(self._ssm_api.get_parameter_value(self._network_ip_map_param_name))
            if not result:
                return []
            return result

        except:
            self._logger.exception("Unable to fetch IP address mapping")
            return []

    def get_available_networks(self) -> list[str]:
        try:
            result = json.loads(self._ssm_api.get_parameter_value(self._available_networks_param_name))
            if not result:
                return []
            return result
        except:
            self._logger.exception("Unable to fetch available networks")
            raise adapter_exception.AdapterException("Unable to fetch available networks")
