from abc import ABC, abstractmethod

from app.provisioning.domain.model import container_details


class ContainerManagementService(ABC):
    @abstractmethod
    def start_container(
        self, aws_account_id: str, region: str, cluster_name: str, service_name: str, user_id: str
    ) -> None: ...

    def stop_container(
        self, aws_account_id: str, region: str, cluster_name: str, service_name: str, user_id: str
    ) -> None: ...

    def get_container_status(
        self, aws_account_id: str, region: str, cluster_name: str, service_name: str, user_id: str
    ) -> container_details.ContainerState: ...

    def get_container_details(
        self, aws_account_id: str, region: str, cluster_name: str, service_name: str, user_id: str
    ) -> container_details.ContainerDetails | None: ...

    def get_container_tags_from_task_arn(
        self, aws_account_id: str, region: str, cluster_name: str, task_name: str, user_id: str
    ) -> list[container_details.ContainerTag]: ...
