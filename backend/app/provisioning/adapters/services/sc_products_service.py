import logging
import typing
import uuid

from botocore import exceptions
from mypy_boto3_cloudformation import client as cf_client
from mypy_boto3_servicecatalog import client

from app.provisioning.adapters.exceptions import adapter_exception
from app.provisioning.domain.exceptions import not_found_exception
from app.provisioning.domain.model import (
    provisioned_product_details,
    provisioned_product_output,
    provisioning_parameter,
)
from app.provisioning.domain.ports import products_service
from app.provisioning.domain.read_models import version

DELETE_FAILED_RESOURCE_STATUS = "DELETE_FAILED"


class ServiceCatalogProductsService(products_service.ProductsService):
    def __init__(
        self,
        sc_boto_client_provider: typing.Callable[[str, str, str], client.ServiceCatalogClient],
        cf_boto_client_provider: typing.Callable[[str, str, str], cf_client.CloudFormationClient],
        logger: logging.Logger,
    ):
        self._sc_boto_client_provider = sc_boto_client_provider
        self._cf_boto_client_provider = cf_boto_client_provider
        self._logger = logger

    def has_provisioned_product_insufficient_capacity_error(
        self,
        provisioned_product_id: str,
        user_id: str,
        aws_account_id: str,
        region: str,
        provisioned_instance_type: str | None,
    ) -> bool:
        if not provisioned_instance_type:
            return False

        stack_events = self.__get_stack_events(
            provisioned_product_id=provisioned_product_id,
            user_id=user_id,
            aws_account_id=aws_account_id,
            region=region,
        )
        if stack_events is None:
            return False

        for stack_event in stack_events:
            status_reason = stack_event.get("ResourceStatusReason")
            self._logger.info(f"Stack event status reason: {status_reason}")
            if self.__is_insufficient_capacity_reason(status_reason, provisioned_instance_type):
                return True

        return False

    @staticmethod
    def __is_insufficient_capacity_reason(status_reason: str | None, instance_type: str) -> bool:
        if not status_reason:
            return False
        has_capacity_error = (
            "We currently do not have sufficient" in status_reason
            or "insufficient capacity" in status_reason.lower()
            or "InsufficientInstanceCapacity" in status_reason
        )
        return has_capacity_error and instance_type in status_reason

    def has_provisioned_product_missing_removal_signal_error(
        self,
        provisioned_product_id: str,
        user_id: str,
        aws_account_id: str,
        region: str,
    ) -> bool:
        """
        The method checks if the stack failed to remove resources while waiting for removal signal from EC2.
        If the CloudFormation times out while waiting for remove signal the following error message will be given.

        error message: Resource handler returned message: "Exceeded attempts to wait"
        """
        stack_events = self.__get_stack_events(
            provisioned_product_id=provisioned_product_id,
            user_id=user_id,
            aws_account_id=aws_account_id,
            region=region,
        )
        if stack_events is None:
            return False

        for stack_event in stack_events:
            status_reason = stack_event.get("ResourceStatusReason")
            resource_status = stack_event.get("ResourceStatus")
            self._logger.debug(f"Stack event status reason: {status_reason}")
            if (
                status_reason
                and status_reason.startswith('Resource handler returned message: "Exceeded attempts to wait"')
                and resource_status == DELETE_FAILED_RESOURCE_STATUS
            ):
                return True

    def __get_stack_events(
        self,
        provisioned_product_id: str,
        user_id: str,
        aws_account_id: str,
        region: str,
    ) -> list[dict] | None:
        stack_arn = self.__get_stack_arn_from_product_outputs(
            aws_account_id=aws_account_id, region=region, user_id=user_id, provisioned_product_id=provisioned_product_id
        )
        if not stack_arn:
            self._logger.error(f"Unable to fetch CloudFormation stack ARN for {provisioned_product_id}")
            return None

        cf_client = self._cf_boto_client_provider(aws_account_id, region, user_id)
        try:
            events_response = cf_client.describe_stack_events(StackName=stack_arn)
        except exceptions.ClientError:
            self._logger.error("Failed to describe stack events")
            return None

        if not events_response.get("StackEvents"):
            raise adapter_exception.AdapterException(f"There is no events for stack {stack_arn}")

        return events_response["StackEvents"]

    def __get_stack_arn_from_product_outputs(
        self, aws_account_id: str, region: str, user_id: str, provisioned_product_id: str
    ) -> str | None:
        sc_client = self._sc_boto_client_provider(aws_account_id, region, user_id)

        result = sc_client.describe_provisioned_product(Id=provisioned_product_id)

        if not result or not result.get("ProvisionedProductDetail"):
            raise adapter_exception.AdapterException(f"Unable to fetch provisioned product {provisioned_product_id}")

        last_provisioning_record_id = result.get("ProvisionedProductDetail").get("LastProvisioningRecordId")

        response = sc_client.describe_record(Id=last_provisioning_record_id)
        if not response or not response.get("RecordOutputs"):
            self._logger.info(f"Unable to fetch record outputs for {last_provisioning_record_id}")
            return

        stack_arn = next(
            (
                record_output.get("OutputValue")
                for record_output in response.get("RecordOutputs")
                if record_output.get("OutputKey") == "CloudformationStackARN"
            ),
            None,
        )
        return stack_arn

    def get_provisioned_product_supported_instance_type_param(
        self, provisioned_product_id: str, user_id: str, aws_account_id: str, region: str
    ) -> version.VersionParameter | None:
        # GET STACK ARN
        sc_client = self._sc_boto_client_provider(aws_account_id, region, user_id)

        result = sc_client.describe_provisioned_product(Id=provisioned_product_id)

        if not result or not result.get("ProvisionedProductDetail"):
            raise adapter_exception.AdapterException(f"Unable to fetch provisioned product {provisioned_product_id}")

        last_provisioning_record_id = result.get("ProvisionedProductDetail").get("LastProvisioningRecordId")

        response = sc_client.describe_record(Id=last_provisioning_record_id)
        if not response or not response.get("RecordOutputs"):
            raise adapter_exception.AdapterException(
                f"Unable to fetch record outputs for {last_provisioning_record_id}"
            )

        stack_arn = next(
            (
                record_output.get("OutputValue")
                for record_output in response.get("RecordOutputs")
                if record_output.get("OutputKey") == "CloudformationStackARN"
            ),
            None,
        )

        if not stack_arn:
            raise adapter_exception.AdapterException(
                f"Unable to fetch CloudFormation stack ARN for {provisioned_product_id}"
            )

        # GET TEMPLATE
        cf_client = self._cf_boto_client_provider(aws_account_id, region, user_id)
        template_response = cf_client.get_template_summary(StackName=stack_arn)

        # THE INSTANCE TYPE PARAMETER IS HARDCODED
        if not template_response.get("Parameters"):
            return None
        template_parameters = template_response.get("Parameters")
        instance_type_param = next(
            (param for param in template_parameters if param.get("ParameterKey") == "InstanceType"), None
        )
        if not instance_type_param:
            return None
        supported_instance_type_param = version.VersionParameter(
            parameterKey=instance_type_param.get("ParameterKey"),
            parameterConstraints=version.ParameterConstraints(
                allowedValues=instance_type_param.get("ParameterConstraints").get("AllowedValues")
            ),
            isTechnicalParameter=False,
        )
        return supported_instance_type_param

    def get_provisioned_product_outputs(
        self, provisioned_product_id: str, user_id: str, aws_account_id: str, region: str
    ) -> list[provisioned_product_output.ProvisionedProductOutput]:
        sc_client = self._sc_boto_client_provider(aws_account_id, region, user_id)

        result = sc_client.describe_provisioned_product(Id=provisioned_product_id)

        if not result or not result.get("ProvisionedProductDetail"):
            raise adapter_exception.AdapterException(f"Unable to fetch provisioned product {provisioned_product_id}")

        last_provisioning_record_id = result.get("ProvisionedProductDetail").get("LastProvisioningRecordId")

        response = sc_client.describe_record(Id=last_provisioning_record_id)
        if not response or not response.get("RecordOutputs"):
            raise adapter_exception.AdapterException(
                f"Unable to fetch record outputs for {last_provisioning_record_id}"
            )

        stack_arn = next(
            (
                record_output.get("OutputValue")
                for record_output in response.get("RecordOutputs")
                if record_output.get("OutputKey") == "CloudformationStackARN"
            ),
            None,
        )

        if not stack_arn:
            raise adapter_exception.AdapterException(
                f"Unable to fetch CloudFormation stack ARN for {provisioned_product_id}"
            )

        return self.__fetch_cloud_formation_stack_outputs(
            user_id=user_id,
            aws_account_id=aws_account_id,
            region=region,
            stack_arn=stack_arn,
        )

    def __fetch_cloud_formation_stack_outputs(
        self,
        user_id: str,
        aws_account_id: str,
        region: str,
        stack_arn: str,
    ):
        cf_client = self._cf_boto_client_provider(aws_account_id, region, user_id)
        try:
            response = cf_client.describe_stacks(StackName=stack_arn)
        except exceptions.ClientError as error:
            # if stack does not exist, a ValidationError is returned.
            if error.response["Error"]["Code"] == "ValidationError":
                raise not_found_exception.NotFoundException(f"CloudFormation stack {stack_arn} does not exist")
            raise error

        if not response or not response.get("Stacks"):
            raise adapter_exception.AdapterException(f"Stack {stack_arn} does not exist")

        if len(response.get("Stacks")) > 1:
            raise adapter_exception.AdapterException("More than 1 stack was found")

        outputs = [
            provisioned_product_output.ProvisionedProductOutput(
                outputKey=output.get("OutputKey"),
                outputValue=output.get("OutputValue"),
                description=output.get("Description"),
            )
            for output in response["Stacks"][0].get("Outputs", [])
            if output.get("OutputKey") != "CloudformationStackARN"
        ]
        return outputs

    def provision_product(
        self,
        user_id: str,
        aws_account_id: str,
        sc_product_id: str,
        sc_provisioning_artifact_id: str,
        provisioning_parameters: list[provisioning_parameter.ProvisioningParameter],
        name: str,
        region: str,
        tags: list[dict[str, str]],
    ) -> str:
        sc_client = self._sc_boto_client_provider(aws_account_id, region, user_id)

        if not provisioning_parameters:
            provisioning_parameters = []

        # Get launch path id
        result = sc_client.list_launch_paths(ProductId=sc_product_id)

        launch_path_id = result["LaunchPathSummaries"][0]["Id"]
        provisioning_token_suffix = str(uuid.uuid4())
        result = sc_client.provision_product(
            ProductId=sc_product_id,
            ProvisioningArtifactId=sc_provisioning_artifact_id,
            PathId=launch_path_id,
            ProvisionedProductName=name,
            Tags=tags,
            ProvisioningParameters=[{"Key": param.key, "Value": param.value} for param in provisioning_parameters],
            ProvisionToken=f"{name}-{provisioning_token_suffix}",
        )

        return result["RecordDetail"]["ProvisionedProductId"]

    def deprovision_product(self, user_id: str, aws_account_id: str, provisioned_product_id: str, region: str) -> None:
        sc_client = self._sc_boto_client_provider(aws_account_id, region, user_id)

        return_msg = sc_client.terminate_provisioned_product(
            ProvisionedProductId=provisioned_product_id,
        )
        self._logger.debug({"type": "TERMINATE_PROVISIONED_PRODUCT", "response": return_msg})

    def update_product(
        self,
        user_id: str,
        aws_account_id: str,
        sc_provisioned_product_id: str,
        sc_product_id: str,
        sc_provisioning_artifact_id: str,
        provisioning_parameters: list[provisioning_parameter.ProvisioningParameter],
        region: str,
    ) -> str:
        sc_client = self._sc_boto_client_provider(aws_account_id, region, user_id)

        if not provisioning_parameters:
            provisioning_parameters = []

        update_token_suffix = str(uuid.uuid4())

        response = sc_client.update_provisioned_product(
            ProvisionedProductId=sc_provisioned_product_id,
            ProvisioningParameters=[
                {
                    "Key": param.key,
                    # Cannot specify usePreviousValue as true and non empty value for a parameter
                    "Value": "" if param.usePreviousValue else param.value,
                    "UsePreviousValue": param.usePreviousValue,
                }
                for param in provisioning_parameters
            ],
            ProvisioningArtifactId=sc_provisioning_artifact_id,
            ProductId=sc_product_id,
            UpdateToken=f"{sc_provisioned_product_id}_{sc_provisioning_artifact_id}_{update_token_suffix}",
        )

        if not response or not response.get("RecordDetail"):
            raise adapter_exception.AdapterException("Invalid Service Catalog response")

        return response["RecordDetail"].get("Status")

    def get_provisioned_product_details(
        self, provisioned_product_id: str, user_id: str, aws_account_id: str, region: str
    ) -> provisioned_product_details.ProvisionedProductDetails | None:
        sc_client = self._sc_boto_client_provider(aws_account_id, region, user_id)

        response = sc_client.search_provisioned_products(
            AccessLevelFilter={"Key": "Account", "Value": "self"},
            Filters={"SearchQuery": [f"id:{provisioned_product_id}"]},
        )

        if not response or not response.get("ProvisionedProducts"):
            return None

        return provisioned_product_details.ProvisionedProductDetails.model_validate(
            response.get("ProvisionedProducts").pop()
        )
