from abc import ABC, abstractmethod


class ParameterService(ABC):
    @abstractmethod
    def get_parameter_value(
        self, parameter_name: str, aws_account_id: str, region: str, user_id: str
    ) -> str | None: ...

    @abstractmethod
    def get_secret_value(self, secret_name: str, aws_account_id: str, region: str, user_id: str) -> str | None: ...
