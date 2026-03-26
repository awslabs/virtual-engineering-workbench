from typing import Optional

from mypy_boto3_logs import client

from app.shared.adapters.boto.boto_provider import BotoProviderOptions, ProviderType
from app.shared.domain.ports import logs_service


class AWSLogsService(logs_service.LogsService):
    def __init__(
        self,
        logs_provider: ProviderType[client.CloudWatchLogsClient],
    ):
        self._provider = logs_provider

    def describe_log_groups(
        self,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> list[dict]:
        logs_client = self._provider(provider_options)
        log_groups = []
        paginator = logs_client.get_paginator("describe_log_groups")

        for page in paginator.paginate():
            log_groups.extend(page.get("logGroups", []))

        return log_groups

    def put_retention_policy(
        self,
        log_group_name: str,
        retention_days: int,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> None:
        logs_client = self._provider(provider_options)

        logs_client.put_retention_policy(
            logGroupName=log_group_name,
            retentionInDays=retention_days,
        )
