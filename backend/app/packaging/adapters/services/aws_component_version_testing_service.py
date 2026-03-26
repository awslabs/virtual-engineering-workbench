from enum import Enum, StrEnum
from typing import Any, Dict

import boto3
import jinja2
from botocore.exceptions import ClientError
from mypy_boto3_ec2 import client as ec2_client
from mypy_boto3_ssm import client as ssm_client

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.domain.model.component import component_version_test_execution
from app.packaging.domain.ports import component_version_testing_service
from app.shared.api import sts_api

SESSION_USER = "ProductPackagingProcess"


class SSMCommandStatusMapping(Enum):
    Failed = [
        "Cancelled",
        "Cancelling",
        "Failed",
        "TimedOut",
    ]
    Pending = [
        "Delayed",
        "Pending",
    ]
    Running = [
        "InProgress",
    ]
    Success = [
        "Success",
    ]


class SystemConfigurationMappingAttributes(StrEnum):
    AMI_SSM_PARAM_NAME = "ami_ssm_param_name"
    COMMAND_SSM_DOCUMENT_NAME = "command_ssm_document_name"
    INSTANCE_TYPE = "instance_type"
    RUN_TESTING_COMMAND = "run_testing_command"
    SETUP_TESTING_ENVIRONMENT_COMMAND = "setup_testing_environment_command"


class AwsComponentVersionTestingService(component_version_testing_service.ComponentVersionTestingService):
    def __init__(
        self,
        admin_role: str,
        ami_factory_aws_account_id: str,
        ami_factory_subnet_names: list[str],
        instance_profile_name: str,
        instance_security_group_name: str,
        region: str,
        system_configuration_mapping: Dict,
        volume_size: int,
        ssm_run_command_timeout: int,
        component_test_s3_bucket_name: str,
        boto_session: Any = None,
    ):
        self._admin_role = admin_role
        self._ami_factory_aws_account_id = ami_factory_aws_account_id
        self._ami_factory_subnet_names = ami_factory_subnet_names
        self._instance_profile_name = instance_profile_name
        self._instance_security_group_name = instance_security_group_name
        self._region = region
        self._system_configuration_mapping = system_configuration_mapping
        self._volume_size = volume_size
        self._ssm_run_command_timeout = ssm_run_command_timeout
        self._boto_session = boto_session
        self._component_test_s3_bucket_name = component_test_s3_bucket_name

    def __get_attr_from_system_configuration(self, architecture: str, attr: str, os_version: str, platform: str) -> str:
        return self._system_configuration_mapping.get(platform).get(architecture).get(os_version).get(attr)

    def __get_ec2_client(
        self, aws_access_key_id: str, aws_secret_access_key: str, aws_session_token: str
    ) -> ec2_client.EC2Client:
        _ec2_client: ec2_client.EC2Client = (
            self._boto_session.client(
                "ec2",
                region_name=self._region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
            )
            if self._boto_session
            else boto3.client(
                "ec2",
                region_name=self._region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
            )
        )

        return _ec2_client

    def __get_subnets(self, ec2_client: ec2_client.EC2Client) -> list[dict]:
        subnets = ec2_client.describe_subnets(Filters=[{"Name": "tag:Name", "Values": self._ami_factory_subnet_names}])

        if not subnets["Subnets"]:
            raise adapter_exception.AdapterException(
                f"No subnets found with id: {','.join(self._ami_factory_subnet_names)}."
            )

        return sorted(list(subnets.get("Subnets")), key=lambda x: x.get("AvailableIpAddressCount"), reverse=True)

    def __get_ssm_client(
        self, aws_access_key_id: str, aws_secret_access_key: str, aws_session_token: str
    ) -> ssm_client.SSMClient:
        _ssm_client: ssm_client.SSMClient = (
            self._boto_session.client(
                "ssm",
                region_name=self._region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
            )
            if self._boto_session
            else boto3.client(
                "ssm",
                region_name=self._region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
            )
        )

        return _ssm_client

    def __run_command(self, architecture: str, command: str, instance_id: str, os_version: str, platform: str) -> str:
        command_ssm_document_name = self.__get_attr_from_system_configuration(
            architecture=architecture,
            attr=SystemConfigurationMappingAttributes.COMMAND_SSM_DOCUMENT_NAME,
            platform=platform,
            os_version=os_version,
        )

        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            ssm_client = self.__get_ssm_client(access_key_id, secret_access_key, session_token)

            response = ssm_client.send_command(
                CloudWatchOutputConfig={"CloudWatchOutputEnabled": True},
                DocumentName=command_ssm_document_name,
                InstanceIds=[instance_id],
                Parameters={
                    "commands": [command],
                    # This is valid for AWS-RunPowerShellScript
                    # and AWS-RunShellScript SSM documents
                    "executionTimeout": [str(self._ssm_run_command_timeout)],
                },
            )

            return response.get("Command").get("CommandId")

    def get_testing_environment_image_upstream_id(self, architecture: str, platform: str, os_version: str) -> str:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            ssm_client = self.__get_ssm_client(access_key_id, secret_access_key, session_token)

            return (
                ssm_client.get_parameter(
                    Name=self.__get_attr_from_system_configuration(
                        architecture,
                        SystemConfigurationMappingAttributes.AMI_SSM_PARAM_NAME,
                        os_version,
                        platform,
                    )
                )
                .get("Parameter")
                .get("Value")
            )

    def get_testing_environment_instance_type(self, architecture: str, platform: str, os_version: str) -> str:
        return self.__get_attr_from_system_configuration(
            architecture,
            SystemConfigurationMappingAttributes.INSTANCE_TYPE,
            os_version,
            platform,
        )

    def launch_testing_environment(self, image_upstream_id: str, instance_type: str) -> str:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            ec2_client = self.__get_ec2_client(access_key_id, secret_access_key, session_token)

            security_groups = ec2_client.describe_security_groups(
                Filters=[{"Name": "group-name", "Values": [self._instance_security_group_name]}]
            )

            if not security_groups["SecurityGroups"]:
                raise adapter_exception.AdapterException(
                    f"Security group with name {self._instance_security_group_name} not found"
                )

            for subnet in self.__get_subnets(ec2_client=ec2_client):
                try:
                    response = ec2_client.run_instances(
                        BlockDeviceMappings=[
                            {
                                "DeviceName": "/dev/sda1",
                                "Ebs": {
                                    "DeleteOnTermination": True,
                                    "Encrypted": True,
                                    "Iops": 3000,
                                    "VolumeSize": self._volume_size,
                                    "VolumeType": "gp3",
                                },
                            },
                        ],
                        IamInstanceProfile={"Name": self._instance_profile_name},
                        ImageId=image_upstream_id,
                        InstanceType=instance_type,
                        MaxCount=1,
                        MetadataOptions={"HttpTokens": "required"},
                        MinCount=1,
                        SecurityGroupIds=[security_groups.get("SecurityGroups")[0].get("GroupId")],
                        SubnetId=subnet.get("SubnetId"),
                    )
                except ClientError as error:
                    if error.response["Error"]["Code"] in ("InsufficientInstanceCapacity", "Unsupported"):
                        continue

                    raise

                return response.get("Instances")[0].get("InstanceId")

            raise adapter_exception.AdapterException(
                "Unable to launch a test EC2 instance - all subnets have been tried."
            )

    def get_testing_environment_creation_time(self, instance_id: str) -> str:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            ec2_client = self.__get_ec2_client(access_key_id, secret_access_key, session_token)

            response = ec2_client.describe_instances(InstanceIds=[instance_id])

            return response.get("Reservations")[0].get("Instances")[0].get("LaunchTime").strftime("%Y-%m-%d %H:%M:%S")

    def get_testing_environment_status(
        self, instance_id: str
    ) -> component_version_test_execution.ComponentVersionTestExecutionInstanceStatus:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            ssm_client = self.__get_ssm_client(access_key_id, secret_access_key, session_token)

            # https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_GetConnectionStatus.html
            response = ssm_client.get_connection_status(Target=instance_id)

            return (
                component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Connected
                if response.get("Status") == "connected"
                else component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Disconnected
            )

    def setup_testing_environment(self, architecture: str, instance_id: str, os_version: str, platform: str) -> str:
        setup_testing_environment_command = self.__get_attr_from_system_configuration(
            architecture=architecture,
            attr=SystemConfigurationMappingAttributes.SETUP_TESTING_ENVIRONMENT_COMMAND,
            platform=platform,
            os_version=os_version,
        )

        return self.__run_command(
            architecture=architecture,
            command=setup_testing_environment_command,
            instance_id=instance_id,
            platform=platform,
            os_version=os_version,
        )

    def get_testing_command_status(
        self, command_id: str, instance_id: str
    ) -> component_version_test_execution.ComponentVersionTestExecutionCommandStatus:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            ssm_client = self.__get_ssm_client(access_key_id, secret_access_key, session_token)

            ssm_command_status = ssm_client.get_command_invocation(CommandId=command_id, InstanceId=instance_id).get(
                "Status"
            )

            if ssm_command_status in SSMCommandStatusMapping.Failed.value:
                return component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed
            elif ssm_command_status in SSMCommandStatusMapping.Pending.value:
                return component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Pending
            elif ssm_command_status in SSMCommandStatusMapping.Running.value:
                return component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running
            elif ssm_command_status in SSMCommandStatusMapping.Success.value:
                return component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success

            # Return FAILED if no match (it shouldn't happen as per SSM API documentation)
            return component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed

    def run_testing(
        self,
        architecture: str,
        component_version_definition_s3_uri: str,
        instance_id: str,
        os_version: str,
        platform: str,
        component_id: str,
        component_version_id: str,
    ) -> str:
        # SSM API doesn't allow {{}} or {{ssm:parameter-name}} in the parameter values,
        # hence using a Jinja Environment with < and > characters instead of { and }
        # https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_PutParameter.html
        environment = jinja2.Environment(  # nosec B701
            block_end_string="%>",
            block_start_string="<%",
            comment_end_string="#>",
            comment_start_string="<#",
            loader=jinja2.BaseLoader(),
            trim_blocks=True,
            variable_end_string=">>",
            variable_start_string="<<",
        )

        run_testing_command_template = environment.from_string(
            self.__get_attr_from_system_configuration(
                architecture=architecture,
                attr=SystemConfigurationMappingAttributes.RUN_TESTING_COMMAND,
                platform=platform,
                os_version=os_version,
            )
        )

        documents = list()
        documents.append(component_version_definition_s3_uri)

        # The attribute SystemConfigurationMappingAttributes.RUN_TESTING_COMMAND
        # must contain << documents  >> for the interpolation
        # to succeed. Parameter system_configuration_mapping itself comes from SSM
        run_testing_command = run_testing_command_template.render(
            documents=",".join([document for document in documents]),
            object_id=component_id,
            version_id=component_version_id,
            instance_id=instance_id,
            log_s3_bucket_name=self.get_component_test_bucket_name(),
        )

        return self.__run_command(
            architecture=architecture,
            command=run_testing_command,
            instance_id=instance_id,
            platform=platform,
            os_version=os_version,
        )

    def teardown_testing_environment(self, instance_id: str) -> None:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            ec2_client = self.__get_ec2_client(access_key_id, secret_access_key, session_token)

            ec2_client.terminate_instances(InstanceIds=[instance_id])

    def get_component_test_bucket_name(self) -> str:
        return self._component_test_s3_bucket_name
