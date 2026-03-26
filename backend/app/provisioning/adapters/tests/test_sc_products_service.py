from unittest import mock

import assertpy
import boto3
import pytest
from botocore import exceptions

from app.provisioning.adapters.exceptions import adapter_exception
from app.provisioning.adapters.services import sc_products_service
from app.provisioning.domain.model import (
    provisioned_product_output,
    provisioning_parameter,
)


@mock.patch("uuid.uuid4", mock.MagicMock(return_value="123"))
def test_sc_products_service_provision_product_should_provision_a_product(
    mock_moto_calls,
    mock_provision_product_request,
):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("servicecatalog", region_name="us-east-1"))

    service = sc_products_service.ServiceCatalogProductsService(
        sc_boto_client_provider=client_provider,
        cf_boto_client_provider=mock.MagicMock(),
        logger=mock.MagicMock(),
    )

    # ACT
    service.provision_product(
        user_id="T0011AA",
        aws_account_id="001234567890",
        sc_product_id="prod-123",
        sc_provisioning_artifact_id="pa-123",
        provisioning_parameters=[provisioning_parameter.ProvisioningParameter(key="param-name", value="param-value")],
        name="test-name",
        region="us-east-1",
        tags=[
            {
                "key": "a",
                "value": "b",
            }
        ],
    )

    # ASSERT
    mock_provision_product_request.assert_called_once_with(
        ProductId="prod-123",
        ProvisioningArtifactId="pa-123",
        PathId="path-1",
        ProvisionedProductName="test-name",
        Tags=[{"key": "a", "value": "b"}],
        ProvisioningParameters=[{"Key": "param-name", "Value": "param-value"}],
        ProvisionToken="test-name-123",
    )
    client_provider.assert_called_once_with("001234567890", "us-east-1", "T0011AA")


@mock.patch("uuid.uuid4", mock.MagicMock(return_value="123"))
def test_sc_products_service_update_provisioned_product_should_update_a_product(
    mock_moto_calls,
    mock_update_provisioned_product_request,
):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("servicecatalog", region_name="us-east-1"))

    service = sc_products_service.ServiceCatalogProductsService(
        sc_boto_client_provider=client_provider,
        cf_boto_client_provider=mock.MagicMock(),
        logger=mock.MagicMock(),
    )

    # ACT
    service.update_product(
        user_id="T0011AA",
        aws_account_id="001234567890",
        sc_provisioned_product_id="sc-pp-123",
        sc_product_id="prod-123",
        sc_provisioning_artifact_id="pa-123",
        provisioning_parameters=[provisioning_parameter.ProvisioningParameter(key="param-name", value="param-value")],
        region="us-east-1",
    )

    # ASSERT
    mock_update_provisioned_product_request.assert_called_once_with(
        ProvisionedProductId="sc-pp-123",
        ProductId="prod-123",
        ProvisioningArtifactId="pa-123",
        ProvisioningParameters=[{"Key": "param-name", "Value": "param-value", "UsePreviousValue": False}],
        UpdateToken="sc-pp-123_pa-123_123",
    )
    client_provider.assert_called_once_with("001234567890", "us-east-1", "T0011AA")


def test_sc_products_service_get_outputs_should_return_outputs_from_catalog(
    mock_moto_calls,
    mock_provision_product_request,
):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("servicecatalog", region_name="us-east-1"))
    cf_client_provider = mock.MagicMock(return_value=boto3.client("cloudformation", region_name="us-east-1"))

    service = sc_products_service.ServiceCatalogProductsService(
        sc_boto_client_provider=client_provider,
        cf_boto_client_provider=cf_client_provider,
        logger=mock.MagicMock(),
    )

    # ACT
    outputs = service.get_provisioned_product_outputs(
        provisioned_product_id="pp-123",
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="us-east-1",
    )

    # ASSERT

    assertpy.assert_that(outputs).is_length(1)
    assertpy.assert_that(outputs).contains(
        provisioned_product_output.ProvisionedProductOutput(
            outputKey="some-output-key",
            outputValue="some-output-value",
            description="some-description",
        )
    )


def test_sc_products_service_get_provisioned_product_details_returns_product_tags(
    mock_moto_calls, mock_search_provisioned_products
):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("servicecatalog", region_name="us-east-1"))

    service = sc_products_service.ServiceCatalogProductsService(
        sc_boto_client_provider=client_provider,
        cf_boto_client_provider=mock.MagicMock(),
        logger=mock.MagicMock(),
    )

    # ACT
    resp = service.get_provisioned_product_details(
        provisioned_product_id="pp-123",
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="us-east-1",
    )

    # ASSERT
    assertpy.assert_that(resp).is_not_none()
    assertpy.assert_that(resp.dict()).is_equal_to(
        {
            "id": "pp-q4qjlwuha5arw",
            "status": "AVAILABLE",
            "tags": [{"key": "key-string", "value": "value-string"}],
            "provisioning_artifact_id": "string",
        }
    )
    mock_search_provisioned_products.assert_called_once_with(
        AccessLevelFilter={"Key": "Account", "Value": "self"},
        Filters={"SearchQuery": ["id:pp-123"]},
    )
    client_provider.assert_called_once_with("001234567890", "us-east-1", "T0011AA")


def test_sc_products_service_terminate_provisioned_product_should_terminate(
    mock_moto_calls,
    mock_terminate_provisioned_product_request,
):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("servicecatalog", region_name="us-east-1"))

    service = sc_products_service.ServiceCatalogProductsService(
        sc_boto_client_provider=client_provider,
        cf_boto_client_provider=mock.MagicMock(),
        logger=mock.MagicMock(),
    )

    # ACT
    service.deprovision_product(
        user_id="T0011AA",
        aws_account_id="001234567890",
        provisioned_product_id="pp-123",
        region="us-east-1",
    )

    # ASSERT
    mock_terminate_provisioned_product_request.assert_called_once_with(
        ProvisionedProductId="pp-123",
    )
    client_provider.assert_called_once_with("001234567890", "us-east-1", "T0011AA")


def test_sc_products_service_gets_supported_instance_type_param(
    mock_moto_calls,
    mock_get_template_summary_request,
):
    # ARRANGE
    sc_client_provider = mock.MagicMock(return_value=boto3.client("servicecatalog", region_name="us-east-1"))
    cf_client_provider = mock.MagicMock(return_value=boto3.client("cloudformation", region_name="us-east-1"))

    service = sc_products_service.ServiceCatalogProductsService(
        sc_boto_client_provider=sc_client_provider,
        cf_boto_client_provider=cf_client_provider,
        logger=mock.MagicMock(),
    )

    # ACT
    version_parameter = service.get_provisioned_product_supported_instance_type_param(
        user_id="T0011AA",
        aws_account_id="001234567890",
        provisioned_product_id="pp-123",
        region="us-east-1",
    )

    # ASSERT
    assertpy.assert_that(version_parameter.parameterConstraints.allowedValues).is_equal_to(["m6x.large", "m6x.small"])


@pytest.mark.parametrize("instance_type,output", (("c8g.metal-24xl", True), ("m8g.metal-24xl", False)))
def test_has_provisioned_product_insufficient_capacity_error_return_flag(
    instance_type,
    output,
    mock_moto_calls,
    mock_describe_stack_events_request,
):
    # ARRANGE
    sc_client_provider = mock.MagicMock(return_value=boto3.client("servicecatalog", region_name="us-east-1"))
    cf_client_provider = mock.MagicMock(return_value=boto3.client("cloudformation", region_name="us-east-1"))

    service = sc_products_service.ServiceCatalogProductsService(
        sc_boto_client_provider=sc_client_provider,
        cf_boto_client_provider=cf_client_provider,
        logger=mock.MagicMock(),
    )

    # ACT
    has_error = service.has_provisioned_product_insufficient_capacity_error(
        user_id="T0011AA",
        aws_account_id="001234567890",
        provisioned_product_id="pp-123",
        region="us-east-1",
        provisioned_instance_type=instance_type,
    )

    # ASSERT
    assertpy.assert_that(bool(has_error)).is_equal_to(output)


def test_has_provisioned_product_insufficient_capacity_error_raise_exception_when_no_stack_events(
    mock_moto_calls,
    mock_describe_stack_events_request,
):
    # ARRANGE
    sc_client_provider = mock.MagicMock(return_value=boto3.client("servicecatalog", region_name="us-east-1"))
    cf_client_provider = mock.MagicMock(return_value=boto3.client("cloudformation", region_name="us-east-1"))
    mock_describe_stack_events_request.return_value = {"StackEvents": []}
    service = sc_products_service.ServiceCatalogProductsService(
        sc_boto_client_provider=sc_client_provider,
        cf_boto_client_provider=cf_client_provider,
        logger=mock.MagicMock(),
    )
    # ACT && ASSERT
    with pytest.raises(adapter_exception.AdapterException) as e:
        service.has_provisioned_product_insufficient_capacity_error(
            user_id="T0011AA",
            aws_account_id="001234567890",
            provisioned_product_id="pp-123",
            region="us-east-1",
            provisioned_instance_type="c8g.metal-24xl",
        )

    assertpy.assert_that(str(e.value)).is_equal_to(
        "There is no events for stack arn:aws:cloudformation:us-east-1:001234567890:stack/sc-prov-prod/aaa"
    )


def test_has_provisioned_product_insufficient_capacity_return_false_when_no_record(
    mock_moto_calls, mock_describe_record_request, mock_logger
):
    # ARRANGE
    sc_client_provider = mock.MagicMock(return_value=boto3.client("servicecatalog", region_name="us-east-1"))
    cf_client_provider = mock.MagicMock(return_value=boto3.client("cloudformation", region_name="us-east-1"))
    mock_describe_record_request.return_value = {"RecordOutputs": []}
    service = sc_products_service.ServiceCatalogProductsService(
        sc_boto_client_provider=sc_client_provider,
        cf_boto_client_provider=cf_client_provider,
        logger=mock_logger,
    )
    # ACT && ASSERT
    has_capacity_error = service.has_provisioned_product_insufficient_capacity_error(
        user_id="T0011AA",
        aws_account_id="001234567890",
        provisioned_product_id="pp-123",
        region="us-east-1",
        provisioned_instance_type="c8g.metal-24xl",
    )
    mock_logger.info.assert_called_once_with("Unable to fetch record outputs for rec-123")
    mock_logger.error.assert_called_once_with("Unable to fetch CloudFormation stack ARN for pp-123")
    assertpy.assert_that(has_capacity_error).is_equal_to(False)


def test_has_provisioned_product_missing_removal_signal_error_return_flag(
    mock_moto_calls,
    mock_describe_stack_events_request,
    mocked_describe_stack_events_missing_remove_signal_response,
):
    # ARRANGE
    mock_describe_stack_events_request.return_value = mocked_describe_stack_events_missing_remove_signal_response
    sc_client_provider = mock.MagicMock(return_value=boto3.client("servicecatalog", region_name="us-east-1"))
    cf_client_provider = mock.MagicMock(return_value=boto3.client("cloudformation", region_name="us-east-1"))

    service = sc_products_service.ServiceCatalogProductsService(
        sc_boto_client_provider=sc_client_provider,
        cf_boto_client_provider=cf_client_provider,
        logger=mock.MagicMock(),
    )

    # ACT
    has_error = service.has_provisioned_product_missing_removal_signal_error(
        user_id="T0011AA",
        aws_account_id="001234567890",
        provisioned_product_id="pp-123",
        region="us-east-1",
    )

    # ASSERT
    assertpy.assert_that(bool(has_error)).is_equal_to(True)


def test_has_provisioned_product_missing_removal_signal_error_raise_exception(
    mock_moto_calls,
    mock_describe_stack_events_request,
):
    # ARRANGE
    sc_client_provider = mock.MagicMock(return_value=boto3.client("servicecatalog", region_name="us-east-1"))
    cf_client_provider = mock.MagicMock(return_value=boto3.client("cloudformation", region_name="us-east-1"))
    mock_describe_stack_events_request.return_value = {"StackEvents": []}
    service = sc_products_service.ServiceCatalogProductsService(
        sc_boto_client_provider=sc_client_provider,
        cf_boto_client_provider=cf_client_provider,
        logger=mock.MagicMock(),
    )
    # ACT && ASSERT
    with pytest.raises(adapter_exception.AdapterException) as e:
        service.has_provisioned_product_missing_removal_signal_error(
            user_id="T0011AA",
            aws_account_id="001234567890",
            provisioned_product_id="pp-123",
            region="us-east-1",
        )
    assertpy.assert_that(str(e.value)).is_equal_to(
        "There is no events for stack arn:aws:cloudformation:us-east-1:001234567890:stack/sc-prov-prod/aaa"
    )


def test_has_provisioned_product_missing_removal_signal_error_logs_error_message_if_can_not_describe_events(
    mock_moto_calls, mock_describe_stack_events_request, mock_logger
):
    # ARRANGE
    error_response = {
        "Error": {
            "Code": "ValidationError",
            "Message": "An error occurred (ValidationError) when calling the DescribeStackEvents operation: Stack [test_stack_arn] does not exist",
        }
    }

    sc_client_provider = mock.MagicMock(return_value=boto3.client("servicecatalog", region_name="us-east-1"))
    cf_client_provider = mock.MagicMock(return_value=boto3.client("cloudformation", region_name="us-east-1"))
    mock_describe_stack_events_request.side_effect = mock.MagicMock(
        side_effect=(
            exceptions.ClientError(
                error_response=error_response,
                operation_name="DescribeStackEvents",
            )
        )
    )
    service = sc_products_service.ServiceCatalogProductsService(
        sc_boto_client_provider=sc_client_provider,
        cf_boto_client_provider=cf_client_provider,
        logger=mock_logger,
    )
    # ACT
    has_signal_error = service.has_provisioned_product_missing_removal_signal_error(
        user_id="T0011AA",
        aws_account_id="001234567890",
        provisioned_product_id="pp-123",
        region="us-east-1",
    )

    # ASSERT
    mock_logger.error.assert_called_once_with("Failed to describe stack events")
    assertpy.assert_that(has_signal_error).is_equal_to(False)


def test_has_provisioned_product_insufficient_capacity_error_logs_error_message_if_can_not_describe_events(
    mock_moto_calls, mock_describe_stack_events_request, mock_logger
):
    # ARRANGE
    error_response = {
        "Error": {
            "Code": "ValidationError",
            "Message": "An error occurred (ValidationError) when calling the DescribeStackEvents operation: Stack [test_stack_arn] does not exist",
        }
    }

    sc_client_provider = mock.MagicMock(return_value=boto3.client("servicecatalog", region_name="us-east-1"))
    cf_client_provider = mock.MagicMock(return_value=boto3.client("cloudformation", region_name="us-east-1"))
    mock_describe_stack_events_request.side_effect = mock.MagicMock(
        side_effect=(
            exceptions.ClientError(
                error_response=error_response,
                operation_name="DescribeStackEvents",
            )
        )
    )
    service = sc_products_service.ServiceCatalogProductsService(
        sc_boto_client_provider=sc_client_provider,
        cf_boto_client_provider=cf_client_provider,
        logger=mock_logger,
    )
    # ACT
    has_insufficient_capacity_error = service.has_provisioned_product_insufficient_capacity_error(
        user_id="T0011AA",
        aws_account_id="001234567890",
        provisioned_product_id="pp-123",
        region="us-east-1",
        provisioned_instance_type="c8g.metal-24xl",
    )

    # ASSERT
    mock_logger.error.assert_called_once_with("Failed to describe stack events")
    assertpy.assert_that(has_insufficient_capacity_error).is_equal_to(False)


def test_has_provisioned_product_missing_removal_signal_error_return_false_when_no_record(
    mock_moto_calls, mock_describe_record_request, mock_logger
):
    # ARRANGE
    sc_client_provider = mock.MagicMock(return_value=boto3.client("servicecatalog", region_name="us-east-1"))
    cf_client_provider = mock.MagicMock(return_value=boto3.client("cloudformation", region_name="us-east-1"))
    mock_describe_record_request.return_value = {"RecordOutputs": []}
    service = sc_products_service.ServiceCatalogProductsService(
        sc_boto_client_provider=sc_client_provider,
        cf_boto_client_provider=cf_client_provider,
        logger=mock_logger,
    )
    # ACT && ASSERT
    has_signal_error = service.has_provisioned_product_missing_removal_signal_error(
        user_id="T0011AA",
        aws_account_id="001234567890",
        provisioned_product_id="pp-123",
        region="us-east-1",
    )
    mock_logger.info.assert_called_once_with("Unable to fetch record outputs for rec-123")
    mock_logger.error.assert_called_once_with("Unable to fetch CloudFormation stack ARN for pp-123")
    assertpy.assert_that(has_signal_error).is_equal_to(False)
