from abc import ABC, abstractmethod

from app.publishing.domain.read_models.license_details import LicenseDetails
from app.publishing.domain.read_models.license_grant_result import LicenseGrantResult


class LicenseManagerService(ABC):
    @abstractmethod
    def create_grant(
        self, license_arn: str, principal_arn: str, grant_name: str, home_region: str
    ) -> LicenseGrantResult: ...

    @abstractmethod
    def accept_grant(self, grant_arn: str, home_region: str, spoke_account_id: str) -> None: ...

    @abstractmethod
    def get_license(self, license_arn: str) -> LicenseDetails: ...

    @abstractmethod
    def verify_image_accessible(self, ami_id: str, region: str, spoke_account_id: str) -> bool: ...

    @abstractmethod
    def has_active_received_grant(self, license_arn: str, spoke_account_id: str, home_region: str) -> bool: ...

    @abstractmethod
    def can_distribute_license(self, license_arn: str, home_region: str) -> bool:
        """True if the hub's received license allows CreateGrant.

        No organization-level condition: AWS accepted grants from a plain member hub in live
        tests. Must not raise: return False when the license cannot be read.
        """
