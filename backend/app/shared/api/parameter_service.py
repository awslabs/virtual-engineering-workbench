from abc import ABC, abstractmethod
from typing import List


class ParameterService(ABC):
    @abstractmethod
    def get_parameter_value(self, parameter_name: str) -> str: ...

    @abstractmethod
    def create_string_parameter(
        self, parameter_name: str, parameter_value: str, is_overwrite: bool = False
    ) -> None: ...

    @abstractmethod
    def get_list_parameter_value(self, parameter_name: str) -> List[str]: ...
