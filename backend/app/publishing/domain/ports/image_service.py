from abc import ABC, abstractmethod


class ImageService(ABC):
    @abstractmethod
    def copy_ami(self, region: str, original_ami_id: str, ami_name: str, ami_description: str) -> str: ...

    @abstractmethod
    def get_copied_ami_status(self, copied_ami_id: str, region: str) -> str: ...

    @abstractmethod
    def grant_kms_access(self, region: str, ami_id: str, aws_account_id: str) -> None: ...

    @abstractmethod
    def share_ami(self, region: str, copied_ami_id: str, aws_account_id: str) -> None: ...
