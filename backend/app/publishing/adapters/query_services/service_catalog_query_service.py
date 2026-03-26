import json
import logging
from typing import Any

import boto3
from mypy_boto3_servicecatalog import client

from app.publishing.adapters.exceptions import adapter_exception
from app.publishing.domain.model import version
from app.publishing.domain.ports import catalog_query_service
from app.shared.api import sts_api
from app.shared.helpers import product_version_parameter_metadata

SESSION_USER = "ProductPublishingProcess"

METADATA_KEY_METADATA = "ProductVersionMetaData"
METADATA_KEY_LABEL = "Label"
METADATA_KEY_VALUE = "Value"

TECHNICAL_PARAMETER_TYPE_STRING = "AWS::"


class ServiceCatalogQueryService(catalog_query_service.CatalogQueryService):
    def __init__(
        self,
        admin_role: str,
        use_case_role: str,
        technical_parameters_names: list[str],
        tools_aws_account_id: str,
        logger: logging.Logger,
        boto_session: Any = None,
    ):
        self._admin_role = admin_role
        self._use_case_role = use_case_role
        self._technical_parameters_names = technical_parameters_names
        self._tools_aws_account_id = tools_aws_account_id
        self._logger = logger
        self._boto_session = boto_session

    def does_portfolio_exist_in_sc(self, region: str, sc_portfolio_id: str) -> bool:
        # Get STS temp credentials
        with sts_api.STSAPI(
            self._tools_aws_account_id, region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            # Create Service Catalog API instance cross-account
            sc_client: client.ServiceCatalogClient = (
                self._boto_session.client(
                    "servicecatalog",
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
                if self._boto_session
                else boto3.client(
                    "servicecatalog",
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
            )

            # Call the service catalog api
            try:
                sc_client.describe_portfolio(Id=sc_portfolio_id)
            except sc_client.exceptions.ResourceNotFoundException:
                return False

        return True

    def get_sc_product_id(self, region: str, sc_product_name: str) -> str | None:
        # Get STS temp credentials
        with sts_api.STSAPI(
            self._tools_aws_account_id, region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            # Create Service Catalog API instance cross-account
            sc_client: client.ServiceCatalogClient = (
                self._boto_session.client(
                    "servicecatalog",
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
                if self._boto_session
                else boto3.client(
                    "servicecatalog",
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
            )

            # Call the service catalog api
            try:
                result = sc_client.describe_product_as_admin(Name=sc_product_name)
            except sc_client.exceptions.ResourceNotFoundException:
                return None

        return result.get("ProductViewDetail").get("ProductViewSummary").get("ProductId")

    def get_sc_provisioning_artifact_id(self, region: str, sc_product_id: str, sc_version_name: str) -> str | None:
        # Get STS temp credentials
        with sts_api.STSAPI(
            self._tools_aws_account_id, region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            # Create Service Catalog API instance cross-account
            sc_client: client.ServiceCatalogClient = (
                self._boto_session.client(
                    "servicecatalog",
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
                if self._boto_session
                else boto3.client(
                    "servicecatalog",
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
            )

            # Call the service catalog api
            try:
                result = sc_client.describe_provisioning_artifact(
                    ProductId=sc_product_id, ProvisioningArtifactName=sc_version_name
                )
            except sc_client.exceptions.ResourceNotFoundException:
                return None

        return result.get("ProvisioningArtifactDetail").get("Id")

    def get_launch_constraint_id(self, region: str, sc_portfolio_id: str, sc_product_id: str) -> str | None:
        return self._get_constraint_id(region, sc_portfolio_id, sc_product_id, "LAUNCH")

    def get_notification_constraint_id(self, region: str, sc_portfolio_id: str, sc_product_id: str) -> str | None:
        return self._get_constraint_id(region, sc_portfolio_id, sc_product_id, "NOTIFICATION")

    def get_resource_update_constraint_id(self, region: str, sc_portfolio_id: str, sc_product_id: str) -> str | None:
        return self._get_constraint_id(region, sc_portfolio_id, sc_product_id, "RESOURCE_UPDATE")

    def _get_constraint_id(
        self, region: str, sc_portfolio_id: str, sc_product_id: str, constraint_type: str
    ) -> str | None:
        # Get STS temp credentials
        with sts_api.STSAPI(
            self._tools_aws_account_id, region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            # Create Service Catalog API instance cross-account
            sc_client: client.ServiceCatalogClient = (
                self._boto_session.client(
                    "servicecatalog",
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
                if self._boto_session
                else boto3.client(
                    "servicecatalog",
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
            )

            # Call the service catalog api
            result = sc_client.list_constraints_for_portfolio(PortfolioId=sc_portfolio_id, ProductId=sc_product_id)

        # Find and get the launch constraint id, if created
        details = result.get("ConstraintDetails", [])
        launch_constraint_id = next(
            iter([detail["ConstraintId"] for detail in details if detail["Type"] == constraint_type]), None
        )
        return launch_constraint_id

    def does_product_exist_in_sc(self, region: str, sc_product_id: str) -> bool:
        # Get STS temp credentials
        with sts_api.STSAPI(
            self._tools_aws_account_id, region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            # Create Service Catalog API instance cross-account
            sc_client: client.ServiceCatalogClient = (
                self._boto_session.client(
                    "servicecatalog",
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
                if self._boto_session
                else boto3.client(
                    "servicecatalog",
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
            )

            # Call the service catalog api
            try:
                sc_client.describe_product_as_admin(Id=sc_product_id)
            except sc_client.exceptions.ResourceNotFoundException:
                return False

        return True

    def does_provisioning_artifact_exist_in_sc(
        self, region: str, sc_product_id: str, sc_provisioning_artifact_id: str
    ) -> bool:
        # Get STS temp credentials
        with sts_api.STSAPI(
            self._tools_aws_account_id, region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            # Create Service Catalog API instance cross-account
            sc_client: client.ServiceCatalogClient = (
                self._boto_session.client(
                    "servicecatalog",
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
                if self._boto_session
                else boto3.client(
                    "servicecatalog",
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
            )

            # Call the service catalog api
            try:
                sc_client.describe_provisioning_artifact(
                    ProductId=sc_product_id, ProvisioningArtifactId=sc_provisioning_artifact_id
                )
            except sc_client.exceptions.ResourceNotFoundException:
                return False

        return True

    def get_provisioning_artifact_count_in_sc(self, region: str, sc_product_id: str) -> int:
        # Get STS temp credentials
        with sts_api.STSAPI(
            self._tools_aws_account_id, region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            # Create Service Catalog API instance cross-account
            sc_client: client.ServiceCatalogClient = (
                self._boto_session.client(
                    "servicecatalog",
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
                if self._boto_session
                else boto3.client(
                    "servicecatalog",
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
            )

            # Call the service catalog api
            try:
                result = sc_client.describe_product_as_admin(Id=sc_product_id)
            except sc_client.exceptions.ResourceNotFoundException:
                return 0

        # Return number of provisioning artifacts available in product
        provisioning_artifacts = result.get("ProvisioningArtifactSummaries", [])
        return len(provisioning_artifacts)

    def get_provisioning_parameters(
        self, region: str, sc_product_id: str, sc_provisioning_artifact_id: str
    ) -> tuple[list[version.VersionParameter], dict[str, version.ProductVersionMetadataItem] | None]:
        # Get STS temp credentials
        with sts_api.STSAPI(
            self._tools_aws_account_id, region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            # Create Service Catalog API instance cross-account
            sc_client: client.ServiceCatalogClient = (
                self._boto_session.client(
                    "servicecatalog",
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
                if self._boto_session
                else boto3.client(
                    "servicecatalog",
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
            )

            # Get launch paths
            launch_paths_result = sc_client.list_launch_paths(ProductId=sc_product_id)
            if not launch_paths_result.get("LaunchPathSummaries"):
                raise adapter_exception.AdapterException(
                    f"Could not fetch launch paths for the Service Catalog Product Id: {sc_product_id}"
                )

            # Get parameters
            result = sc_client.describe_provisioning_parameters(
                ProductId=sc_product_id,
                ProvisioningArtifactId=sc_provisioning_artifact_id,
                PathId=launch_paths_result["LaunchPathSummaries"][0]["Id"],
            )

            parameters = []
            for sc_param in result.get("ProvisioningArtifactParameters", []):
                constraints = None
                if sc_param.get("ParameterConstraints"):
                    sc_constraints = sc_param["ParameterConstraints"]
                    constraints = version.ParameterConstraints(
                        allowedPattern=sc_constraints.get("AllowedPattern"),
                        allowedValues=sc_constraints.get("AllowedValues"),
                        constraintDescription=sc_constraints.get("ConstraintDescription"),
                        maxLength=sc_constraints.get("MaxLength"),
                        maxValue=sc_constraints.get("MaxValue"),
                        minLength=sc_constraints.get("MinLength"),
                        minValue=sc_constraints.get("MinValue"),
                    )
                param = version.VersionParameter(
                    defaultValue=sc_param.get("DefaultValue"),
                    description=sc_param.get("Description"),
                    isNoEcho=sc_param.get("IsNoEcho"),
                    parameterKey=sc_param.get("ParameterKey"),
                    parameterType=sc_param.get("ParameterType"),
                    parameterConstraints=constraints,
                    parameterMetaData=None,
                    isTechnicalParameter=any(
                        [
                            sc_param.get("ParameterKey", "") in self._technical_parameters_names,
                            TECHNICAL_PARAMETER_TYPE_STRING in sc_param.get("ParameterType", ""),
                        ]
                    ),
                )
                parameters.append(param)

            metadata = next(iter([p["Value"] for p in result["UsageInstructions"] if p["Type"] == "metadata"]), None)
            generic_metadata = None

            if metadata:
                parameters = self.__add_parameter_metadata(parameters, json.loads(metadata))
                generic_metadata = self.__add_generic_metadata(json.loads(metadata))

            return parameters, generic_metadata

    def __add_parameter_metadata(
        self, parameters: list[version.VersionParameter], metadata: dict
    ) -> list[version.VersionParameter]:
        param_meta = product_version_parameter_metadata.from_cloud_formation_metadata_dict(
            logger=self._logger, metadata=metadata
        )

        for param in parameters:
            if param_meta.has_parameter_metadata(param.parameterKey):
                param.parameterMetadata = version.ParameterMetadata(
                    label=param_meta.get_user_friendly_name(param.parameterKey),
                    optionLabels=param_meta.get_parameter_option_labels(param.parameterKey),
                    optionWarnings=param_meta.get_parameter_warnings(param.parameterKey),
                )

        return parameters

    def __add_generic_metadata(self, metadata: dict | None):
        generic_metadata = None

        if metadata and METADATA_KEY_METADATA in metadata:
            try:
                generic_metadata = {
                    key: self.__parse_metadata_item(value) for (key, value) in metadata[METADATA_KEY_METADATA].items()
                }
            except:
                self._logger.exception("Unable to fetch generic metadata for product")

        return generic_metadata

    def __parse_metadata_item(self, value):
        label = None
        metadata_values = None

        if METADATA_KEY_LABEL in value:
            label = value[METADATA_KEY_LABEL]

        if METADATA_KEY_VALUE in value:
            metadata_values = value[METADATA_KEY_VALUE]

        return version.ProductVersionMetadataItem(label=label, value=self.__parse_metadata_value(metadata_values))

    def __parse_metadata_value(self, value: Any):
        if isinstance(value, list):
            return value
        else:
            return [value]
