from abc import ABC, abstractmethod


class OrgIntegrationService(ABC):
    @abstractmethod
    def is_license_manager_org_integration_active(self) -> bool: ...
