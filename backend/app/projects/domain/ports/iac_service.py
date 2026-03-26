from abc import ABC, abstractmethod


class IACService(ABC):
    @abstractmethod
    def deploy_iac(self, aws_account_id: str, region: str, variables: dict[str, str] = {}) -> None: ...
