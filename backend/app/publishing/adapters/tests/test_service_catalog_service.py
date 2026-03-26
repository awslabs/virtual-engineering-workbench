from unittest.mock import MagicMock

import assertpy
import boto3
from mypy_boto3_servicecatalog import client

from app.publishing.adapters.services import service_catalog_service


def test_create_portfolio_creates_portfolio(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    sc_portfolio_id = sc_srv.create_portfolio("us-east-1", "port-00000", "my-portfolio", "myself")

    # ASSERT
    assertpy.assert_that(sc_portfolio_id).is_equal_to("sc-port-00000")
    mock_moto_calls["CreatePortfolio"].assert_called_once_with(
        DisplayName="my-portfolio", ProviderName="myself", IdempotencyToken="port-00000"
    )


def test_create_portfolio_share_shares_portfolio(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    sc_srv.share_portfolio("us-east-1", "sc-port-00000", "123456789013")

    # ASSERT
    mock_moto_calls["CreatePortfolioShare"].assert_called_once_with(
        PortfolioId="sc-port-00000",
        AccountId="123456789013",
    )


def test_accept_portfolio_share_accepts_portfolio_share(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    sc_srv.accept_portfolio_share("us-east-1", "sc-port-00000", "123456789013")

    # ASSERT
    mock_moto_calls["AcceptPortfolioShare"].assert_called_once_with(PortfolioId="sc-port-00000")


def test_associate_role_with_portfolio_associates_principal_with_portfolio(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    sc_srv.associate_role_with_portfolio("us-east-1", "sc-port-00000", "my-role")

    # ASSERT
    mock_moto_calls["AssociatePrincipalWithPortfolio"].assert_called_once_with(
        PortfolioId="sc-port-00000",
        PrincipalARN="arn:aws:iam::123456789012:role/my-role",
        PrincipalType="IAM",
    )


def test_associate_role_with_portfolio_associates_principal_with_portfolio_on_spoke_account(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    sc_srv.associate_role_with_portfolio("us-east-1", "sc-port-00000", "my-role", "123456789013")

    # ASSERT
    mock_moto_calls["AssociatePrincipalWithPortfolio"].assert_called_once_with(
        PortfolioId="sc-port-00000",
        PrincipalARN="arn:aws:iam::123456789013:role/my-role",
        PrincipalType="IAM",
    )


def test_disassociate_role_from_portfolio_disassociates_principal_from_portfolio(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    sc_srv.disassociate_role_from_portfolio("us-east-1", "sc-port-00000", "my-role")

    # ASSERT
    mock_moto_calls["DisassociatePrincipalFromPortfolio"].assert_called_once_with(
        PortfolioId="sc-port-00000",
        PrincipalARN="arn:aws:iam::123456789012:role/my-role",
        PrincipalType="IAM",
    )


def test_disassociate_role_from_portfolio_disassociates_principal_from_portfolio_on_spoke_account(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    sc_srv.disassociate_role_from_portfolio("us-east-1", "sc-port-00000", "my-role", "123456789013")

    # ASSERT
    mock_moto_calls["DisassociatePrincipalFromPortfolio"].assert_called_once_with(
        PortfolioId="sc-port-00000",
        PrincipalARN="arn:aws:iam::123456789013:role/my-role",
        PrincipalType="IAM",
    )


def test_list_roles_for_portfolio_returns_iam_role_names(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    resp = sc_srv.list_roles_for_portfolio("us-east-1", "sc-port-00000")

    # ASSERT
    mock_moto_calls["ListPrincipalsForPortfolio"].assert_called_once_with(PortfolioId="sc-port-00000")
    assertpy.assert_that(resp).contains_only("my-role")


def test_list_roles_for_portfolio_returns_iam_role_names_on_spoke_account(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    resp = sc_srv.list_roles_for_portfolio("us-east-1", "sc-port-00000", "123456789013")

    # ASSERT
    mock_moto_calls["ListPrincipalsForPortfolio"].assert_called_once_with(PortfolioId="sc-port-00000")
    assertpy.assert_that(resp).contains_only("my-role")


def test_create_provisioning_artifact_returns_provisioning_artifact_id(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    prov_art_id = sc_srv.create_provisioning_artifact(
        "us-east-1",
        "vers-12345abc",
        "1.0.0-rc.1",
        "sc-prod-00000",
        "my product version",
        "prod-12345abc/vers-12345abc/workbench-template.yml",
    )

    # ASSERT
    mock_moto_calls["CreateProvisioningArtifact"].assert_called_once_with(
        ProductId="sc-prod-00000",
        Parameters={
            "Name": "1.0.0-rc.1",
            "Description": "my product version",
            "Info": {
                "LoadTemplateFromURL": "https://my-bucket.s3.amazonaws.com/prod-12345abc/vers-12345abc/workbench-template.yml"
            },
            "Type": "CLOUD_FORMATION_TEMPLATE",
        },
        IdempotencyToken="sc-prod-00000-vers-12345abc-1-0-0-rc-1",
    )
    assertpy.assert_that(prov_art_id).is_equal_to("pa-12345")


def test_create_product_returns_product_id_and_provisioning_artifact_id(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    prod_id, prov_art_id = sc_srv.create_product(
        "us-east-1",
        "prod-name-12345",
        "owner",
        "my product",
        "vers-12345abc",
        "1.0.0-rc.1",
        "my product version",
        "prod-12345abc/vers-12345abc/workbench-template.yml",
    )

    # ASSERT
    mock_moto_calls["CreateProduct"].assert_called_once_with(
        Name="prod-name-12345",
        Owner="owner",
        ProductType="CLOUD_FORMATION_TEMPLATE",
        IdempotencyToken="prod-name-12345-vers-12345abc-1-0-0-rc-1",
        Description="my product",
        Distributor=service_catalog_service.SESSION_USER,
        ProvisioningArtifactParameters={
            "Name": "1.0.0-rc.1",
            "Description": "my product version",
            "Info": {
                "LoadTemplateFromURL": "https://my-bucket.s3.amazonaws.com/prod-12345abc/vers-12345abc/workbench-template.yml"
            },
            "Type": "CLOUD_FORMATION_TEMPLATE",
        },
    )
    assertpy.assert_that(prod_id).is_equal_to("prod-12345")
    assertpy.assert_that(prov_art_id).is_equal_to("pa-12345")


def test_associate_product_with_portfolio_associates_product_with_portfolio(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    sc_srv.associate_product_with_portfolio("us-east-1", "sc-port-00000", "sc-prod-00000")

    # ASSERT
    mock_moto_calls["AssociateProductWithPortfolio"].assert_called_once_with(
        ProductId="sc-prod-00000", PortfolioId="sc-port-00000"
    )


def test_create_launch_constraint_creates_launch_constraint(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    sc_srv.create_launch_constraint("us-east-1", "sc-port-00000", "sc-prod-00000")

    # ASSERT
    mock_moto_calls["CreateConstraint"].assert_called_once_with(
        PortfolioId="sc-port-00000",
        ProductId="sc-prod-00000",
        IdempotencyToken="sc-prod-00000-LAUNCH",
        Type="LAUNCH",
        Parameters='{"LocalRoleName": "launchconstraint"}',
    )


def test_create_resource_update_constraint_creates_resource_update_constraint(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    sc_srv.create_resource_update_constraint("us-east-1", "sc-port-00000", "sc-prod-00000")

    # ASSERT
    mock_moto_calls["CreateConstraint"].assert_called_once_with(
        PortfolioId="sc-port-00000",
        ProductId="sc-prod-00000",
        IdempotencyToken="sc-prod-00000-RESOURCE_UPDATE",
        Type="RESOURCE_UPDATE",
        Parameters='{"Version": "2.0", "Properties": {"TagUpdateOnProvisionedProduct": "ALLOWED"}}',
    )


def test_create_notification_constraint_creates_notification_constraint(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    sc_srv.create_notification_constraint("us-east-1", "sc-port-00000", "sc-prod-00000")

    # ASSERT
    mock_moto_calls["CreateConstraint"].assert_called_once_with(
        PortfolioId="sc-port-00000",
        ProductId="sc-prod-00000",
        IdempotencyToken="sc-prod-00000-NOTIFICATION",
        Type="NOTIFICATION",
        Parameters='{"NotificationArns": ["notification-arn-us-east-1"]}',
    )


def test_delete_provisioning_artifact_deletes_provisioning_artifact(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    sc_srv.delete_provisioning_artifact("us-east-1", "sc-prod-00000", "sc-pa-12345")

    # ASSERT
    mock_moto_calls["DeleteProvisioningArtifact"].assert_called_once_with(
        ProductId="sc-prod-00000", ProvisioningArtifactId="sc-pa-12345"
    )


def test_update_provisioning_artifact_name_renames_provisioning_artifact_name(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    result = sc_srv.update_provisioning_artifact_name("us-east-1", "prod-123", "vers-123", "1.0.0")

    # ASSERT
    mock_moto_calls["UpdateProvisioningArtifact"].assert_called_once_with(
        ProductId="prod-123", ProvisioningArtifactId="vers-123", Name="1.0.0"
    )
    assertpy.assert_that(result).is_equal_to("CREATING")


def test_disassociate_product_from_portfolio_disassociates_product_from_portfolio(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    sc_srv.disassociate_product_from_portfolio("us-east-1", "sc-port-00000", "sc-prod-00000")

    # ASSERT
    mock_moto_calls["DisassociateProductFromPortfolio"].assert_called_once_with(
        ProductId="sc-prod-00000", PortfolioId="sc-port-00000"
    )


def test_disassociate_product_from_portfolio_passes_if_product_is_not_associated(mock_moto_calls):
    # ARRANGE
    sc_client: client.ServiceCatalogClient = boto3.client("servicecatalog")
    mock_moto_calls["DisassociateProductFromPortfolio"] = MagicMock(
        side_effect=sc_client.exceptions.ResourceNotFoundException(
            {
                "Message": "Product sc-prod-00000 not found in portfolio sc-port-00000",
                "Code": "ResourceNotFoundException",
            },
            "DisassociateProductFromPortfolio",
        )
    )
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    sc_srv.disassociate_product_from_portfolio("us-east-1", "sc-port-00000", "sc-prod-00000")

    # ASSERT
    mock_moto_calls["DisassociateProductFromPortfolio"].assert_called_once_with(
        ProductId="sc-prod-00000", PortfolioId="sc-port-00000"
    )


def test_delete_product_deletes_product_in_sc(mock_moto_calls):
    # ARRANGE
    sc_srv = service_catalog_service.ServiceCatalogService(
        "admin",
        "usecase",
        "launchconstraint",
        lambda region: f"notification-arn-{region}",
        "ALLOWED",
        "123456789012",
        "my-bucket",
    )

    # ACT
    sc_srv.delete_product("us-east-1", "sc-prod-00000")

    # ASSERT
    mock_moto_calls["DeleteProduct"].assert_called_once_with(Id="sc-prod-00000")
