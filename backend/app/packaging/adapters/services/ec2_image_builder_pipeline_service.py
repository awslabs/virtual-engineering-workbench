from enum import StrEnum
from typing import Any

import boto3
from mypy_boto3_ec2 import client as ec2_client
from mypy_boto3_imagebuilder import client as imagebuilder_client

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.domain.ports import pipeline_service
from app.shared.api import sts_api

SESSION_USER = "ProductPackagingProcess"


class PagingParams(StrEnum):
    MAX_RESULTS = "maxResults"
    NEXT_TOKEN = "nextToken"

    def __str__(self):
        return str(self.value)


class Ec2ImageBuilderPipelineService(pipeline_service.PipelineService):
    def __init__(
        self,
        admin_role: str,
        ami_factory_aws_account_id: str,
        ami_factory_subnet_names: list[str],
        image_key_name: str,
        instance_profile_name: str,
        instance_security_group_name: str,
        region: str,
        topic_arn: str,
        pipelines_configuration_mapping: dict,
        boto_session: Any = None,
        max_results: int | None = None,
    ):
        self._admin_role = admin_role
        self._ami_factory_aws_account_id = ami_factory_aws_account_id
        self._ami_factory_subnet_names = ami_factory_subnet_names
        self._image_key_name = image_key_name
        self._instance_profile_name = instance_profile_name
        self._instance_security_group_name = instance_security_group_name
        self._region = region
        self._topic_arn = topic_arn
        self._pipelines_configuration_mapping = pipelines_configuration_mapping
        self._boto_session = boto_session
        self._max_results = max_results

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

    def __get_subnet_id(self, ec2_client: ec2_client.EC2Client, subnet_names: list[str]) -> str:
        subnets = ec2_client.describe_subnets(Filters=[{"Name": "tag:Name", "Values": subnet_names}])

        if not subnets["Subnets"]:
            raise adapter_exception.AdapterException(f"No subnets found with id: {','.join(subnet_names)}.")

        subnet_list = sorted(list(subnets.get("Subnets")), key=lambda x: x.get("AvailableIpAddressCount"), reverse=True)

        return subnet_list[0].get("SubnetId")

    def __get_imagebuilder_client(
        self, aws_access_key_id: str, aws_secret_access_key: str, aws_session_token: str
    ) -> imagebuilder_client.ImagebuilderClient:
        _imagebuilder_client: imagebuilder_client.ImagebuilderClient = (
            self._boto_session.client(
                "imagebuilder",
                region_name=self._region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
            )
            if self._boto_session
            else boto3.client(
                "imagebuilder",
                region_name=self._region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
            )
        )
        return _imagebuilder_client

    def create_distribution_config(self, description: str, image_tags: dict[str, str], name: str) -> str:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            imagebuilder_client = self.__get_imagebuilder_client(access_key_id, secret_access_key, session_token)
            response = imagebuilder_client.create_distribution_configuration(
                description=description,
                distributions=[
                    {
                        "amiDistributionConfiguration": {
                            "amiTags": image_tags,
                            "kmsKeyId": f"arn:aws:kms:{self._region}:{self._ami_factory_aws_account_id}:alias/{self._image_key_name}",
                        },
                        "region": self._region,
                    }
                ],
                name=name,
            )

            return response.get("distributionConfigurationArn")

    def create_infrastructure_config(self, description: str, instance_types: list[str], name: str) -> str:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            ec2_client = self.__get_ec2_client(access_key_id, secret_access_key, session_token)

            subnet_id = self.__get_subnet_id(ec2_client=ec2_client, subnet_names=self._ami_factory_subnet_names)

            security_groups = ec2_client.describe_security_groups(
                Filters=[{"Name": "group-name", "Values": [self._instance_security_group_name]}]
            )

            if not security_groups["SecurityGroups"]:
                raise adapter_exception.AdapterException(
                    f"Security group with name {self._instance_security_group_name} not found."
                )

            imagebuilder_client = self.__get_imagebuilder_client(access_key_id, secret_access_key, session_token)
            response = imagebuilder_client.create_infrastructure_configuration(
                description=description,
                instanceMetadataOptions={"httpTokens": "required"},
                instanceProfileName=self._instance_profile_name,
                instanceTypes=instance_types,
                name=name,
                securityGroupIds=[security_groups.get("SecurityGroups")[0].get("GroupId")],
                snsTopicArn=self._topic_arn,
                subnetId=subnet_id,
            )

            return response.get("infrastructureConfigurationArn")

    def create_pipeline(
        self,
        description: str,
        distribution_config_arn: str,
        infrastructure_config_arn: str,
        name: str,
        recipe_version_arn: str,
        schedule: str,
    ) -> str:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            imagebuilder_client = self.__get_imagebuilder_client(access_key_id, secret_access_key, session_token)
            response = imagebuilder_client.create_image_pipeline(
                description=description,
                distributionConfigurationArn=distribution_config_arn,
                imageRecipeArn=recipe_version_arn,
                infrastructureConfigurationArn=infrastructure_config_arn,
                name=name,
                schedule={
                    "scheduleExpression": f"cron({schedule})",
                    "pipelineExecutionStartCondition": "EXPRESSION_MATCH_ONLY",
                },
            )

            return response.get("imagePipelineArn")

    def delete_distribution_config(self, distribution_config_arn: str) -> None:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            imagebuilder_client = self.__get_imagebuilder_client(access_key_id, secret_access_key, session_token)

            imagebuilder_client.delete_distribution_configuration(distributionConfigurationArn=distribution_config_arn)

    def delete_infrastructure_config(self, infrastructure_config_arn: str) -> None:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            imagebuilder_client = self.__get_imagebuilder_client(access_key_id, secret_access_key, session_token)

            imagebuilder_client.delete_infrastructure_configuration(
                infrastructureConfigurationArn=infrastructure_config_arn
            )

    def delete_pipeline(self, pipeline_arn: str) -> None:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            imagebuilder_client = self.__get_imagebuilder_client(access_key_id, secret_access_key, session_token)

            imagebuilder_client.delete_image_pipeline(imagePipelineArn=pipeline_arn)

    def start_pipeline_execution(self, pipeline_arn: str) -> str:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            imagebuilder_client = self.__get_imagebuilder_client(access_key_id, secret_access_key, session_token)
            response = imagebuilder_client.start_image_pipeline_execution(imagePipelineArn=pipeline_arn)

            return response.get("imageBuildVersionArn")

    def update_distribution_config(
        self, description: str, distribution_config_arn: str, image_tags: dict[str, str]
    ) -> None:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            imagebuilder_client = self.__get_imagebuilder_client(access_key_id, secret_access_key, session_token)
            response = imagebuilder_client.update_distribution_configuration(
                description=description,
                distributionConfigurationArn=distribution_config_arn,
                distributions=[
                    {
                        "amiDistributionConfiguration": {
                            "amiTags": image_tags,
                            "kmsKeyId": f"arn:aws:kms:{self._region}:{self._ami_factory_aws_account_id}:alias/{self._image_key_name}",
                        },
                        "region": self._region,
                    }
                ],
            )

            return response.get("distributionConfigurationArn")

    def update_infrastructure_config(
        self, description: str, instance_types: list[str], infrastructure_config_arn: str
    ) -> None:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            ec2_client = self.__get_ec2_client(access_key_id, secret_access_key, session_token)

            subnet_id = self.__get_subnet_id(ec2_client=ec2_client, subnet_names=self._ami_factory_subnet_names)

            security_groups = ec2_client.describe_security_groups(
                Filters=[{"Name": "group-name", "Values": [self._instance_security_group_name]}]
            )

            if not security_groups["SecurityGroups"]:
                raise adapter_exception.AdapterException(
                    f"Security group with name {self._instance_security_group_name} not found."
                )

            imagebuilder_client = self.__get_imagebuilder_client(access_key_id, secret_access_key, session_token)
            response = imagebuilder_client.update_infrastructure_configuration(
                description=description,
                infrastructureConfigurationArn=infrastructure_config_arn,
                instanceMetadataOptions={"httpTokens": "required"},
                instanceProfileName=self._instance_profile_name,
                instanceTypes=instance_types,
                securityGroupIds=[security_groups.get("SecurityGroups")[0].get("GroupId")],
                snsTopicArn=self._topic_arn,
                subnetId=subnet_id,
            )

            return response.get("infrastructureConfigurationArn")

    def update_pipeline(
        self,
        description: str,
        distribution_config_arn: str,
        infrastructure_config_arn: str,
        pipeline_arn: str,
        recipe_version_arn: str,
        schedule: str,
    ) -> None:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            imagebuilder_client = self.__get_imagebuilder_client(access_key_id, secret_access_key, session_token)
            response = imagebuilder_client.update_image_pipeline(
                description=description,
                distributionConfigurationArn=distribution_config_arn,
                imagePipelineArn=pipeline_arn,
                imageRecipeArn=recipe_version_arn,
                infrastructureConfigurationArn=infrastructure_config_arn,
                schedule={
                    "scheduleExpression": f"cron({schedule})",
                    "pipelineExecutionStartCondition": "EXPRESSION_MATCH_ONLY",
                },
            )

            return response.get("imagePipelineArn")

    def get_pipeline_allowed_build_instance_types(self, architecture: str) -> list[str]:
        try:
            return (
                self._pipelines_configuration_mapping.get("Pipelines")
                .get(architecture)
                .get("allowed_build_instance_types")
            )
        except (TypeError, AttributeError):
            raise adapter_exception.AdapterException(
                f"No pipelines configuration found for architecture: {architecture}"
            )
