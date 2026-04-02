import assertpy

from app.provisioning.domain.model import additional_configuration
from app.provisioning.entrypoints.provisioned_product_configuration_event_handler.model import step_function_model


def test_handle_start_provisioned_product_configuration(
    mock_dependencies, lambda_context, mock_start_provisioned_product_configuration_command_handler
):
    # ARRANGE
    from app.provisioning.entrypoints.provisioned_product_configuration_event_handler import handler

    handler.dependencies = mock_dependencies
    request = step_function_model.StartProvisionedProductConfigurationRequest(provisionedProductId="pp-123")

    # ACT
    result = handler.handler(request.model_dump(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    mock_start_provisioned_product_configuration_command_handler.assert_called_once()


def test_handle_get_provisoned_product_configuration_status(mock_dependencies, lambda_context):
    # ARRANGE
    from app.provisioning.entrypoints.provisioned_product_configuration_event_handler import handler

    handler.dependencies = mock_dependencies
    request = step_function_model.GetProvisionedProductConfigurationStatusRequest(provisionedProductId="pp-123")

    # ACT
    result = handler.handler(request.model_dump(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["status"]).is_equal_to(
        additional_configuration.AdditionalConfigurationRunStatus.Success
    )
    assertpy.assert_that(result["reason"]).is_equal_to("Success")


def test_handle_fail_provisioned_product_configuration(
    mock_dependencies, lambda_context, mock_fail_provisioned_product_configuration_command_handler
):
    # ARRANGE
    from app.provisioning.entrypoints.provisioned_product_configuration_event_handler import handler

    handler.dependencies = mock_dependencies
    request = step_function_model.FailProvisionedProductConfigurationRequest(
        provisionedProductId="pp-123", reason="Failed"
    )

    # ACT
    result = handler.handler(request.model_dump(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    mock_fail_provisioned_product_configuration_command_handler.assert_called_once()


def test_handle_complete_provisioned_product_configuration(
    mock_dependencies, lambda_context, mock_complete_provisioned_product_configuration_command_handler
):
    # ARRANGE
    from app.provisioning.entrypoints.provisioned_product_configuration_event_handler import handler

    handler.dependencies = mock_dependencies
    request = step_function_model.CompleteProvisionedProductConfigurationRequest(provisionedProductId="pp-123")

    # ACT
    result = handler.handler(request.model_dump(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    mock_complete_provisioned_product_configuration_command_handler.assert_called_once()


def test_handle_is_provisioned_product_ready(mock_dependencies, lambda_context):
    # ARRANGE
    from app.provisioning.entrypoints.provisioned_product_configuration_event_handler import handler

    handler.dependencies = mock_dependencies
    request = step_function_model.IsProvisionedProductReadyRequest(provisionedProductId="pp-123")

    # ACT
    result = handler.handler(request.model_dump(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["isReady"]).is_true()
