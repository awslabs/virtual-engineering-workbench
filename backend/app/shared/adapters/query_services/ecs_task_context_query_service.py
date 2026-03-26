from json import loads
from urllib import request

from app.shared.domain.model import task_context
from app.shared.domain.ports import task_context_query_service

DEFAULT_MEMORY_LIMIT_IN_MB = -1  # No memory limit defined for the container


class EcsTaskContextQueryService(task_context_query_service.TaskContextQueryService):
    def __init__(
        self,
        endpoint: str,
    ):
        self.__endpoint = endpoint

    def __get_url_response(self, url: str) -> dict:
        with request.urlopen(url) as response:  # nosec B310 - ECS metadata endpoint
            return loads(response.read().decode("utf-8"))

    def __get_container_metadata(self) -> dict:
        return self.__get_url_response(self.__endpoint)

    def __get_task_metadata(self) -> dict:
        return self.__get_url_response(f"{self.__endpoint}/task")

    def get_task_context(self) -> task_context.TaskContext:
        container_metadata = self.__get_container_metadata()
        memory_limit_in_mb = DEFAULT_MEMORY_LIMIT_IN_MB
        if container_metadata.get("Limits"):
            memory_limit_in_mb = container_metadata.get("Limits").get("Memory", DEFAULT_MEMORY_LIMIT_IN_MB)
        task_metadata = self.__get_task_metadata()

        return task_context.TaskContext(
            aws_request_id=task_metadata.get("TaskARN").split("/")[-1],
            function_name=task_metadata.get("Family"),
            function_version=task_metadata.get("Revision"),
            log_group_name=container_metadata.get("LogOptions").get("awslogs-group"),
            log_stream_name=container_metadata.get("LogOptions").get("awslogs-stream"),
            invoked_function_arn=task_metadata.get("TaskARN"),
            memory_limit_in_mb=memory_limit_in_mb,
        )
