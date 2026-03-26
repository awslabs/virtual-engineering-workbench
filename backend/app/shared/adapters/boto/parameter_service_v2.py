from abc import ABC, abstractmethod
from typing import List, Optional

from app.shared.adapters.boto.boto_provider import BotoProviderOptions


class ParameterService(ABC):
    @abstractmethod
    def get_parameter_value(
        self,
        parameter_name: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> str | None: ...

    @abstractmethod
    def get_list_parameter_value(
        self,
        parameter_name: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> List[str]: ...

    @abstractmethod
    def get_parameters_by_path(
        self,
        path: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> dict[str, str]: ...

    @abstractmethod
    def create_string_parameter(
        self,
        parameter_name: str,
        parameter_value: str,
        is_overwrite: bool = False,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> None: ...

    @abstractmethod
    def delete_parameter(
        self,
        parameter_name: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> None: ...
