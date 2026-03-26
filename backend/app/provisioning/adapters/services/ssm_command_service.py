import typing

from mypy_boto3_ssm import client

from app.provisioning.adapters.exceptions import adapter_exception
from app.provisioning.domain.model import additional_configuration
from app.provisioning.domain.ports import system_command_service


class SSMCommandService(system_command_service.SystemCommandService):
    def __init__(
        self,
        ssm_boto_client_provider: typing.Callable[[str, str, str], client.SSMClient],
        provisioned_product_configuration_document_mapping: dict,
    ):
        self._ssm_boto_client_provider = ssm_boto_client_provider
        self._provisioned_product_configuration_document_mapping = provisioned_product_configuration_document_mapping

    def run_document(
        self,
        aws_account_id: str,
        region: str,
        user_id: str,
        provisioned_product_configuration_type: additional_configuration.ProvisionedProductConfigurationTypeEnum,
        instance_id: str,
        parameters: list[additional_configuration.AdditionalConfigurationParameter],
    ) -> str | None:
        # Get SSM client
        ssm_client = self._ssm_boto_client_provider(aws_account_id, region, user_id)

        # Get SSM document name from config
        ssm_document_name = self._provisioned_product_configuration_document_mapping.get(
            provisioned_product_configuration_type
        )

        # Send the SSM command, which is executed async
        response = ssm_client.send_command(
            CloudWatchOutputConfig={"CloudWatchOutputEnabled": True},
            DocumentName=ssm_document_name,
            InstanceIds=[instance_id],
            Parameters={param.key: [param.value] for param in parameters},
        )

        command_id = response.get("Command").get("CommandId")
        if not command_id:
            raise adapter_exception.AdapterException(f"Could not run document for the instance {instance_id}")

        return command_id

    def get_run_status(
        self, aws_account_id: str, region: str, user_id: str, instance_id: str, run_id: str
    ) -> tuple[additional_configuration.AdditionalConfigurationRunStatus, str]:
        # Get SSM client
        ssm_client = self._ssm_boto_client_provider(aws_account_id, region, user_id)

        # Get the status of the SSM command
        response = ssm_client.get_command_invocation(CommandId=run_id, InstanceId=instance_id)

        # Return the status
        status = response.get("Status")
        reason = response.get("StatusDetails")
        if not status:
            raise adapter_exception.AdapterException(
                f"Could not get status for the run id {run_id} and instance id {instance_id}"
            )

        if status in ["Pending", "InProgress", "Delayed"]:
            return additional_configuration.AdditionalConfigurationRunStatus.InProgress, reason
        elif status == "Success":
            return additional_configuration.AdditionalConfigurationRunStatus.Success, reason
        elif status in ["Cancelled", "Cancelling", "Failed", "TimedOut"]:
            return additional_configuration.AdditionalConfigurationRunStatus.Failed, reason
        else:
            raise adapter_exception.AdapterException(f"Status {status} is not supported")

    def is_instance_ready(self, aws_account_id: str, region: str, user_id: str, instance_id: str) -> bool:
        """
        Returns True if SSM agent is connected to the instance, False otherwise
        """
        # Get SSM client
        ssm_client = self._ssm_boto_client_provider(aws_account_id, region, user_id)

        # Get the connection status of the instance
        response = ssm_client.get_connection_status(Target=instance_id)

        # Return the status
        return True if response.get("Status") == "connected" else False
