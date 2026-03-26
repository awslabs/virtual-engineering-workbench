import json
from typing import Any, Callable, Optional

import boto3
from mypy_boto3_servicecatalog import client

from app.publishing.domain.ports import catalog_service
from app.shared.api import sts_api

SESSION_USER = "ProductPublishingProcess"


class ServiceCatalogService(catalog_service.CatalogService):
    def __init__(
        self,
        admin_role: str,
        use_case_role: str,
        launch_constraint_role: str,
        notification_constraint_topic_arn_resolver: Callable[[str], str],
        resource_update_constraint_allowed: str,
        tools_aws_account_id: str,
        bucket_name: str,
        boto_session: Any = None,
    ):
        self._admin_role = admin_role
        self._use_case_role = use_case_role
        self._launch_constraint_role = launch_constraint_role
        self._notification_constraint_topic_arn_resolver = notification_constraint_topic_arn_resolver
        self._resource_update_constraint_allowed = resource_update_constraint_allowed
        self._tools_aws_account_id = tools_aws_account_id
        self._bucket_name = bucket_name
        self._boto_session = boto_session

    def create_portfolio(self, region: str, portfolio_id: str, portfolio_name: str, portfolio_provider: str) -> str:
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
            response = sc_client.create_portfolio(
                DisplayName=portfolio_name, ProviderName=portfolio_provider, IdempotencyToken=portfolio_id
            )

        return response["PortfolioDetail"]["Id"]

    def share_portfolio(self, region: str, sc_portfolio_id: str, aws_account_id: str) -> None:
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
            sc_client.create_portfolio_share(
                PortfolioId=sc_portfolio_id,
                AccountId=aws_account_id,
            )

    def accept_portfolio_share(self, region: str, sc_portfolio_id: str, aws_account_id: str) -> None:
        # Get STS temp credentials
        with sts_api.STSAPI(aws_account_id, region, self._use_case_role, SESSION_USER, self._boto_session) as sts:
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
            sc_client.accept_portfolio_share(PortfolioId=sc_portfolio_id)

    def associate_role_with_portfolio(
        self,
        region: str,
        sc_portfolio_id: str,
        role_name: str,
        aws_account_id: Optional[str] = None,
    ) -> None:
        # Set the target account and role
        sts_aws_account_id = self._tools_aws_account_id
        sts_role = self._admin_role
        if aws_account_id:
            sts_aws_account_id = aws_account_id
            sts_role = self._use_case_role

        # Get STS temp credentials
        with sts_api.STSAPI(sts_aws_account_id, region, sts_role, SESSION_USER, self._boto_session) as sts:
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
            sc_client.associate_principal_with_portfolio(
                PortfolioId=sc_portfolio_id,
                PrincipalARN=f"arn:aws:iam::{sts_aws_account_id}:role/{role_name}",
                PrincipalType="IAM",
            )

    def disassociate_role_from_portfolio(
        self,
        region: str,
        sc_portfolio_id: str,
        role_name: str,
        aws_account_id: Optional[str] = None,
    ) -> None:
        # Set the target account and role
        sts_aws_account_id = self._tools_aws_account_id
        sts_role = self._admin_role
        if aws_account_id:
            sts_aws_account_id = aws_account_id
            sts_role = self._use_case_role

        # Get STS temp credentials
        with sts_api.STSAPI(sts_aws_account_id, region, sts_role, SESSION_USER, self._boto_session) as sts:
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
            sc_client.disassociate_principal_from_portfolio(
                PortfolioId=sc_portfolio_id,
                PrincipalARN=f"arn:aws:iam::{sts_aws_account_id}:role/{role_name}",
                PrincipalType="IAM",
            )

    def list_roles_for_portfolio(
        self,
        region: str,
        sc_portfolio_id: str,
        aws_account_id: Optional[str] = None,
    ) -> list[str]:
        # Set the target account and role
        sts_aws_account_id = self._tools_aws_account_id
        sts_role = self._admin_role
        if aws_account_id:
            sts_aws_account_id = aws_account_id
            sts_role = self._use_case_role

        # Get STS temp credentials
        with sts_api.STSAPI(sts_aws_account_id, region, sts_role, SESSION_USER, self._boto_session) as sts:
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
            principal_arns: str = []
            args = {"PortfolioId": sc_portfolio_id}
            while "Principals" in (response := sc_client.list_principals_for_portfolio(**args)):
                principal_arns = [
                    r.get("PrincipalARN") for r in response.get("Principals", []) if r.get("PrincipalType") == "IAM"
                ]
                if (next_token := response.get("NextPageToken", None)) is not None:
                    args["PageToken"] = next_token
                else:
                    break

            return [principal_arn.split(":role/")[1] for principal_arn in principal_arns if ":role/" in principal_arn]

    def create_provisioning_artifact(
        self, region: str, version_id: str, version_name: str, sc_product_id: str, description: str, template_path: str
    ) -> str:
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
            idempotency_token = (f"{sc_product_id}-{version_id}-{version_name}").replace(".", "-")
            result = sc_client.create_provisioning_artifact(
                ProductId=sc_product_id,
                Parameters={
                    "Name": version_name,
                    "Description": description,
                    "Info": {"LoadTemplateFromURL": f"https://{self._bucket_name}.s3.amazonaws.com/{template_path}"},
                    "Type": "CLOUD_FORMATION_TEMPLATE",
                },
                IdempotencyToken=idempotency_token,
            )

            # Return the provisioning artifact id
            return result["ProvisioningArtifactDetail"]["Id"]

    def create_product(
        self,
        region: str,
        product_name: str,
        owner: str,
        product_description: str,
        version_id: str,
        version_name: str,
        version_description: str,
        template_path: str,
    ) -> tuple[str, str]:
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
            idempotency_token = (f"{product_name}-{version_id}-{version_name}").replace(".", "-")
            result = sc_client.create_product(
                Name=product_name,
                Owner=owner,
                ProductType="CLOUD_FORMATION_TEMPLATE",
                IdempotencyToken=idempotency_token,
                Description=product_description,
                Distributor=SESSION_USER,
                ProvisioningArtifactParameters={
                    "Name": version_name,
                    "Description": version_description,
                    "Info": {"LoadTemplateFromURL": f"https://{self._bucket_name}.s3.amazonaws.com/{template_path}"},
                    "Type": "CLOUD_FORMATION_TEMPLATE",
                },
            )

            # Return product id and provisioning artifact id
            return (
                result["ProductViewDetail"]["ProductViewSummary"]["ProductId"],
                result["ProvisioningArtifactDetail"]["Id"],
            )

    def associate_product_with_portfolio(self, region: str, sc_portfolio_id: str, sc_product_id: str) -> None:
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
            sc_client.associate_product_with_portfolio(ProductId=sc_product_id, PortfolioId=sc_portfolio_id)

    def create_launch_constraint(self, region: str, sc_portfolio_id: str, sc_product_id: str) -> None:
        params = f'{{"LocalRoleName": "{self._launch_constraint_role}"}}'
        self._create_constraint(region, sc_portfolio_id, sc_product_id, "LAUNCH", params)

    def create_resource_update_constraint(self, region: str, sc_portfolio_id: str, sc_product_id: str) -> None:
        params = {
            "Version": "2.0",
            "Properties": {"TagUpdateOnProvisionedProduct": self._resource_update_constraint_allowed},
        }
        self._create_constraint(region, sc_portfolio_id, sc_product_id, "RESOURCE_UPDATE", json.dumps(params))

    def create_notification_constraint(
        self,
        region: str,
        sc_portfolio_id: str,
        sc_product_id: str,
    ) -> None:
        params = f'{{"NotificationArns": ["{self._notification_constraint_topic_arn_resolver(region)}"]}}'
        self._create_constraint(region, sc_portfolio_id, sc_product_id, "NOTIFICATION", params)

    def _create_constraint(
        self, region: str, sc_portfolio_id: str, sc_product_id: str, constraint_type: str, parameters: str
    ) -> None:
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
            sc_client.create_constraint(
                PortfolioId=sc_portfolio_id,
                ProductId=sc_product_id,
                IdempotencyToken=f"{sc_product_id}-{constraint_type}",
                Type=constraint_type,
                Parameters=parameters,
            )

    def delete_provisioning_artifact(self, region: str, sc_product_id: str, sc_provisioning_artifact_id: str) -> None:
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
            sc_client.delete_provisioning_artifact(
                ProductId=sc_product_id, ProvisioningArtifactId=sc_provisioning_artifact_id
            )

    def update_provisioning_artifact_name(
        self, region: str, sc_product_id: str, sc_provisioning_artifact_id: str, new_name: str
    ) -> str:
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
            result = sc_client.update_provisioning_artifact(
                ProductId=sc_product_id, ProvisioningArtifactId=sc_provisioning_artifact_id, Name=new_name
            )
            # literal "AVAILABLE" | "CREATING" | "FAILED"
            return result["Status"]

    def disassociate_product_from_portfolio(self, region: str, sc_portfolio_id: str, sc_product_id: str) -> None:
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
                sc_client.disassociate_product_from_portfolio(ProductId=sc_product_id, PortfolioId=sc_portfolio_id)
            except sc_client.exceptions.ResourceNotFoundException:
                pass  # Product is not associated with the portfolio

    def delete_product(self, region: str, sc_product_id: str) -> None:
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
            sc_client.delete_product(Id=sc_product_id)
