from unittest.mock import MagicMock

import assertpy
import boto3
from mypy_boto3_servicecatalog import client

from app.publishing.adapters.query_services import service_catalog_query_service


def test_does_portfolio_exist_in_sc_returns_true_if_portfolio_exists(mock_moto_calls, mock_logger):
    # ARRANGE
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    result = sc_qry_srv.does_portfolio_exist_in_sc("us-east-1", "port-12345")

    # ASSERT
    assertpy.assert_that(result).is_true()


def test_does_portfolio_exist_in_sc_returns_false_if_portfolio_does_not_exist(mock_moto_calls, mock_logger):
    # ARRANGE
    sc_client: client.ServiceCatalogClient = boto3.client("servicecatalog")
    mock_moto_calls["DescribePortfolio"] = MagicMock(
        side_effect=sc_client.exceptions.ResourceNotFoundException(
            {
                "Message": "There are no local or default portfolios with id port-12345",
                "Code": "ResourceNotFoundException",
            },
            "DescribePortfolio",
        )
    )
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    result = sc_qry_srv.does_portfolio_exist_in_sc("us-east-1", "port-12345")

    # ASSERT
    assertpy.assert_that(result).is_false()


def test_get_sc_product_id_returns_product_id_if_product_exists(mock_moto_calls, mock_logger):
    # ARRANGE
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    sc_prod_id = sc_qry_srv.get_sc_product_id("us-east-1", "prod-name")

    # ASSERT
    assertpy.assert_that(sc_prod_id).is_equal_to("prod-12345")


def test_get_sc_product_id_returns_none_if_product_does_not_exist(mock_moto_calls, mock_logger):
    # ARRANGE
    sc_client: client.ServiceCatalogClient = boto3.client("servicecatalog")
    mock_moto_calls["DescribeProductAsAdmin"] = MagicMock(
        side_effect=sc_client.exceptions.ResourceNotFoundException(
            {
                "Message": "Product with name prod-name not found",
                "Code": "ResourceNotFoundException",
            },
            "DescribeProductAsAdmin",
        )
    )
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    sc_prod_id = sc_qry_srv.get_sc_product_id("us-east-1", "prod-name")

    # ASSERT
    assertpy.assert_that(sc_prod_id).is_none()


def test_get_sc_provisioning_artifact_id_returns_provisioning_artifact_id_if_provisioning_artifact_exists(
    mock_moto_calls, mock_logger
):
    # ARRANGE
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    sc_prov_art_id = sc_qry_srv.get_sc_provisioning_artifact_id("us-east-1", "prod-12345", "1.0.0-rc.1")

    # ASSERT
    assertpy.assert_that(sc_prov_art_id).is_equal_to("pa-12345")


def test_get_sc_provisioning_artifact_id_returns_none_if_provisioning_artifact_does_not_exist(
    mock_moto_calls, mock_logger
):
    # ARRANGE
    sc_client: client.ServiceCatalogClient = boto3.client("servicecatalog")
    mock_moto_calls["DescribeProvisioningArtifact"] = MagicMock(
        side_effect=sc_client.exceptions.ResourceNotFoundException(
            {
                "Message": "There is no provisioning artifact",
                "Code": "ResourceNotFoundException",
            },
            "DescribeProvisioningArtifact",
        )
    )
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    sc_prov_art_id = sc_qry_srv.get_sc_provisioning_artifact_id("us-east-1", "prod-12345", "1.0.0-rc.1")

    # ASSERT
    assertpy.assert_that(sc_prov_art_id).is_none()


def test_get_launch_constraint_id_returns_launch_constraint_id_if_exists(mock_moto_calls, mock_logger):
    # ARRANGE
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    launch_constraint_id = sc_qry_srv.get_launch_constraint_id("us-east-1", "port-12345", "prod-12345")

    # ASSERT
    assertpy.assert_that(launch_constraint_id).is_equal_to("cons-12345")


def test_get_launch_constraint_id_returns_none_if_does_not_exist(mock_moto_calls, mock_logger):
    # ARRANGE
    mock_moto_calls["ListConstraintsForPortfolio"] = MagicMock(
        return_value={
            "ConstraintDetails": [],
        }
    )
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    launch_constraint_id = sc_qry_srv.get_launch_constraint_id("us-east-1", "port-12345", "prod-12345")

    # ASSERT
    assertpy.assert_that(launch_constraint_id).is_none()


def test_get_notification_constraint_id_returns_notification_constraint_id_if_exists(mock_moto_calls, mock_logger):
    # ARRANGE
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    launch_constraint_id = sc_qry_srv.get_notification_constraint_id("us-east-1", "port-12345", "prod-12345")

    # ASSERT
    assertpy.assert_that(launch_constraint_id).is_equal_to("cons-00000")


def test_get_notification_constraint_id_returns_none_if_does_not_exist(mock_moto_calls, mock_logger):
    # ARRANGE
    mock_moto_calls["ListConstraintsForPortfolio"] = MagicMock(
        return_value={
            "ConstraintDetails": [],
        }
    )
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    launch_constraint_id = sc_qry_srv.get_notification_constraint_id("us-east-1", "port-12345", "prod-12345")

    # ASSERT
    assertpy.assert_that(launch_constraint_id).is_none()


def test_get_resource_update_constraint_id_returns_resource_update_constraint_id_if_exists(
    mock_moto_calls, mock_logger
):
    # ARRANGE
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    resource_constraint_id = sc_qry_srv.get_resource_update_constraint_id("us-east-1", "port-12345", "prod-12345")

    # ASSERT
    assertpy.assert_that(resource_constraint_id).is_equal_to("cons-56789")


def test_get_resource_update_constraint_id_returns_none_if_does_not_exist(mock_moto_calls, mock_logger):
    # ARRANGE
    mock_moto_calls["ListConstraintsForPortfolio"] = MagicMock(
        return_value={
            "ConstraintDetails": [
                {
                    "ConstraintId": "cons-12345",
                    "Type": "LAUNCH",
                    "Description": "string",
                    "Owner": "string",
                    "ProductId": "string",
                    "PortfolioId": "string",
                },
                {
                    "ConstraintId": "cons-00000",
                    "Type": "NOTIFICATION",
                    "Description": "string",
                    "Owner": "string",
                    "ProductId": "string",
                    "PortfolioId": "string",
                },
            ]
        }
    )
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    resource_update_constraint_id = sc_qry_srv.get_resource_update_constraint_id(
        "us-east-1", "port-12345", "prod-12345"
    )

    # ASSERT
    assertpy.assert_that(resource_update_constraint_id).is_none()


def test_does_product_exist_in_sc_returns_true_if_product_exists(mock_moto_calls, mock_logger):
    # ARRANGE
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    result = sc_qry_srv.does_product_exist_in_sc("us-east-1", "prod-12345")

    # ASSERT
    assertpy.assert_that(result).is_true()


def test_does_product_exist_in_sc_returns_false_if_product_does_not_exist(mock_moto_calls, mock_logger):
    # ARRANGE
    sc_client: client.ServiceCatalogClient = boto3.client("servicecatalog")
    mock_moto_calls["DescribeProductAsAdmin"] = MagicMock(
        side_effect=sc_client.exceptions.ResourceNotFoundException(
            {
                "Message": "Product with name prod-name not found",
                "Code": "ResourceNotFoundException",
            },
            "DescribeProductAsAdmin",
        )
    )
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    result = sc_qry_srv.does_product_exist_in_sc("us-east-1", "prod-name")

    # ASSERT
    assertpy.assert_that(result).is_false()


def test_does_provisioning_artifact_exist_in_sc_returns_true_if_provisioning_artifact_exist(
    mock_moto_calls, mock_logger
):
    # ARRANGE
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    result = sc_qry_srv.does_provisioning_artifact_exist_in_sc("us-east-1", "prod-12345", "vers-12345")

    # ASSERT
    assertpy.assert_that(result).is_true()


def test_does_provisioning_artifact_exist_in_sc_returns_false_if_provisioning_artifact_does_not_exist(
    mock_moto_calls, mock_logger
):
    # ARRANGE
    sc_client: client.ServiceCatalogClient = boto3.client("servicecatalog")
    mock_moto_calls["DescribeProvisioningArtifact"] = MagicMock(
        side_effect=sc_client.exceptions.ResourceNotFoundException(
            {
                "Message": "There is no provisioning artifact",
                "Code": "ResourceNotFoundException",
            },
            "DescribeProvisioningArtifact",
        )
    )
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    result = sc_qry_srv.does_provisioning_artifact_exist_in_sc("us-east-1", "prod-12345", "vers-12345")

    # ASSERT
    assertpy.assert_that(result).is_false()


def test_get_provisioning_artifact_count_in_sc_returns_correct_count(mock_moto_calls, mock_logger):
    # ARRANGE
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    result = sc_qry_srv.get_provisioning_artifact_count_in_sc("us-east-1", "prod-12345")

    # ASSERT
    assertpy.assert_that(result).is_equal_to(1)


def test_get_provisioning_parameters_returns_correct_parameters(mock_moto_calls, mock_logger):
    # ARRANGE
    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    result, _ = sc_qry_srv.get_provisioning_parameters("us-east-1", "prod-12345", "vers-12345")

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result).is_length(7)
    assertpy.assert_that(result[0].parameterKey).is_equal_to("SubnetIdSSM")
    assertpy.assert_that(result[0].defaultValue).is_equal_to("/workbench/vpc/privatesubnet-id-balanced")
    assertpy.assert_that(result[0].isTechnicalParameter).is_true()
    assertpy.assert_that(result[3].parameterKey).is_equal_to("VolumeSize")
    assertpy.assert_that(result[3].defaultValue).is_equal_to("250")
    assertpy.assert_that(result[3].isTechnicalParameter).is_false()
    assertpy.assert_that(result[3].parameterConstraints.allowedValues).is_equal_to(["250", "350", "500"])
    assertpy.assert_that(result[3].parameterMetadata.label).is_equal_to("How much storage would you like to have?")
    assertpy.assert_that(result[3].parameterMetadata.optionLabels).is_equal_to(
        {"250": "Disk S - 250 GB Storage", "500": "Disk L - 500 GB Storage", "350": "Disk M - 350 GB Storage"}
    )
    assertpy.assert_that(result[3].parameterMetadata.optionWarnings).is_equal_to({"250": "Very expensive"})
    assertpy.assert_that(result[4].parameterKey).is_equal_to("OwnerTID")
    assertpy.assert_that(result[4].isTechnicalParameter).is_true()
    assertpy.assert_that(result[5].parameterKey).is_equal_to("SubnetId")
    assertpy.assert_that(result[5].isTechnicalParameter).is_true()
    assertpy.assert_that(result[6].parameterKey).is_equal_to("SubnetsIds")
    assertpy.assert_that(result[6].isTechnicalParameter).is_true()


def test_get_provisioning_parameters_returns_generic_version_metadata(mock_moto_calls, mock_logger):
    # ARRANGE
    # mock_moto_calls.get("DescribeProvisioningParameters").return_value =

    sc_qry_srv = service_catalog_query_service.ServiceCatalogQueryService(
        "admin", "usecase", ["OwnerTID"], "123456789012", mock_logger
    )

    # ACT
    _, meta = sc_qry_srv.get_provisioning_parameters("us-east-1", "prod-12345", "vers-12345")

    # ASSERT
    assertpy.assert_that(meta).is_not_none()
    assertpy.assert_that(meta).is_length(3)
    assertpy.assert_that(meta).contains("InstalledTools", "ReleaseNotes", "MainSoftware")
    assertpy.assert_that(meta).contains_entry(
        {
            "InstalledTools": {
                "label": "Installed Tools",
                "value": ["https://example.com"],
            }
        }
    )
