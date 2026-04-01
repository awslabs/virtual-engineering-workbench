import logging
import typing

from botocore.exceptions import ClientError
from mypy_boto3_ecs import client

from app.provisioning.adapters.exceptions import adapter_exception
from app.provisioning.domain.exceptions import insufficient_capacity_exception
from app.provisioning.domain.model import container_details
from app.provisioning.domain.ports import container_management_service


class ECSContainerManagementService(container_management_service.ContainerManagementService):
    def __init__(
        self,
        ecs_boto_client_provider: typing.Callable[[str, str, str], client.ECSClient],
        logger: logging.Logger,
    ):
        self._ecs_boto_client_provider = ecs_boto_client_provider
        self._logger = logger

    def start_container(
        self, aws_account_id: str, region: str, cluster_name: str, service_name: str, user_id: str
    ) -> None:
        self.__set_service_desired_count(aws_account_id, region, cluster_name, service_name, 1, user_id)

    def stop_container(
        self, aws_account_id: str, region: str, cluster_name: str, service_name: str, user_id: str
    ) -> None:
        ecs_client = self._ecs_boto_client_provider(aws_account_id, region, user_id)

        try:
            # Set the desired count to 0 to stop the service from maintaining tasks
            self.__set_service_desired_count(aws_account_id, region, cluster_name, service_name, 0, user_id)

            # Retrieve the task ARNs for the service
            task_arns = self.__get_task_arns(ecs_client, cluster_name, service_name)

            # Stop each task immediately
            if task_arns:
                for task_arn in task_arns:
                    self._logger.debug(f"Stopping task {task_arn}")
                    ecs_client.stop_task(
                        cluster=cluster_name,
                        task=task_arn,
                        reason="Stopping container as part of service stop operation.",
                    )
            else:
                self._logger.debug(f"No tasks found to stop for service {service_name}.")

        except ClientError as e:
            self.__handle_client_error(e)

    def __get_current_desired_count(self, ecs_client: client.ECSClient, cluster_name: str, service_name: str) -> int:
        response = ecs_client.describe_services(cluster=cluster_name, services=[service_name])
        services = response.get("services", [])
        if services:
            return services[0].get("desiredCount", 0)
        else:
            return 0

    def get_container_status(
        self, aws_account_id: str, region: str, cluster_name: str, service_name: str, user_id: str
    ) -> container_details.ContainerState:

        try:
            desired_count = self.__get_current_desired_count(
                self._ecs_boto_client_provider(aws_account_id, region, user_id), cluster_name, service_name
            )
            if desired_count > 0:
                return container_details.ContainerState(Name="RUNNING")
            else:
                return container_details.ContainerState(Name="STOPPED")

        except ClientError as e:
            self.__handle_client_error(e)

    def get_container_details(
        self, aws_account_id: str, region: str, cluster_name: str, service_name: str, user_id: str
    ) -> container_details.ContainerDetails | None:
        ecs_client = self._ecs_boto_client_provider(aws_account_id, region, user_id)

        try:
            # Fetch task ARNs for the service
            task_arns = self.__get_task_arns(ecs_client, cluster_name, service_name)
            if not task_arns:
                desired_count = self.__get_current_desired_count(
                    self._ecs_boto_client_provider(aws_account_id, region, user_id), cluster_name, service_name
                )
                if desired_count == 0:
                    return container_details.ContainerDetails(state=container_details.ContainerState(Name="STOPPED"))
                else:
                    return None

            # Get details about the first task
            task = self.__get_task_details(ecs_client, cluster_name, task_arns[0])
            self._logger.info(f"Task details: {task}")
            if task is None:
                raise adapter_exception.AdapterException("No running task found for the specified service.")

            # Return the container instance details
            return container_details.ContainerDetails(
                private_ip_address=self.__extract_private_ip(task),
                state=container_details.ContainerState(Name=task.get("lastStatus")),
                tags=task.get("tags", []),
                task_arn=task.get("taskArn"),
                name=self.__extract_container_name(task),
            )
        except ClientError as e:
            self.__handle_client_error(e)

    def get_container_tags_from_task_arn(
        self, aws_account_id: str, region: str, cluster_name: str, task_arn: str, user_id: str
    ) -> list[container_details.ContainerTag]:

        ecs_client = self._ecs_boto_client_provider(aws_account_id, region, user_id)
        task_details = self.__get_task_details(ecs_client, cluster_name, task_arn)
        if task_details is None:
            raise adapter_exception.AdapterException("No running task found for the specified service.")
        tags = task_details.get("tags", [])
        self._logger.debug(f"Task tags: {tags}")
        return [
            container_details.ContainerTag.model_validate({"Key": tag.get("key"), "Value": tag.get("value")})
            for tag in tags
        ]

    def __set_service_desired_count(
        self, aws_account_id: str, region: str, cluster_name: str, service_name: str, desired_count: int, user_id: str
    ) -> None:
        try:
            self._logger.debug(f"Setting service desired count to: {desired_count}")
            # Get the ECS client for the specified account and region
            ecs_client = self._ecs_boto_client_provider(aws_account_id, region, user_id)

            # Update the service with the desired count
            ecs_client.update_service(
                cluster=cluster_name,  # Assuming a default cluster, change as needed
                service=service_name,
                desiredCount=desired_count,
            )

        except ClientError as e:
            self.__handle_client_error(e)

    def __get_task_arns(self, ecs_client, cluster_name: str, service_name: str) -> list[str]:
        """Retrieve the list of task ARNs for a given ECS service."""
        task_response = ecs_client.list_tasks(cluster=cluster_name, serviceName=service_name)
        self._logger.debug(f"List Tasks response: {task_response}")
        return task_response.get("taskArns", [])

    def __get_task_details(self, ecs_client, cluster_name: str, task_arn: str) -> dict | None:
        """Describe the task and return task details."""
        task_details = ecs_client.describe_tasks(cluster=cluster_name, tasks=[task_arn], include=["TAGS"])
        self._logger.debug(f"Task details: {task_details}")
        return task_details.get("tasks", None)[0]  # Get the first task

    def __extract_private_ip(self, task: dict) -> str | None:
        """Extract the private IP from task detail."""
        for container in task.get("containers", []):
            for network_interface in container.get("networkInterfaces", []):
                if "privateIpv4Address" in network_interface:
                    return network_interface.get("privateIpv4Address")
        return None

    def __extract_container_name(self, task: dict) -> str | None:
        """Extract the container name task detail."""
        for container in task.get("containers", []):
            if "name" in container:
                return container.get("name")
        return None

    def __handle_client_error(self, e: ClientError) -> None:
        """Handle known ClientErrors and raise appropriate exceptions."""
        error_code = e.response["Error"]["Code"]
        if error_code == "ClusterNotFoundException":
            raise adapter_exception.AdapterException(f"Cluster not found: {e}")
        elif error_code == "ServiceNotFoundException":
            raise adapter_exception.AdapterException(f"Service not found: {e}")
        elif error_code == "InsufficientClusterCapacityException":
            raise insufficient_capacity_exception.InsufficientCapacityException(f"Insufficient capacity: {e}")
        else:
            raise adapter_exception.AdapterException(f"Unexpected error occurred: {e}")
