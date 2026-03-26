from abc import ABC, abstractmethod


class ParameterDefinitionService(ABC):
    @abstractmethod
    def get_parameter_value(self, parameter_name: str) -> str: ...

    @abstractmethod
    def get_parameter_value_from_path_with_decryption(self, parameter_path: str) -> str: ...

    @abstractmethod
    def create_parameter(self, parameter_name: str, parameter_value: str, parameter_type: str) -> dict: ...

    @abstractmethod
    def delete(self, parameter_name: str) -> None: ...

    @abstractmethod
    def delete_by_path(self, parameter_path: str) -> None: ...
