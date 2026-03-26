import json

import assertpy

from infra.constructs.provisioned_product_configuration import provisioned_product_configuration_state_machine


def test_pp_configuration_success_path(start_execution, wait_for_execution, mocked_test_event):
    # ARRANGE

    # ACT
    execution_arn = start_execution(test_name="SuccessPath", test_event=mocked_test_event)
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("SUCCEEDED")
    assertpy.assert_that(output).is_not_none()
    output_parsed = json.loads(output)
    assertpy.assert_that(output_parsed["getProvisionedProductConfigurationStatusResponse"]["status"]).is_equal_to(
        provisioned_product_configuration_state_machine.AdditionalConfigurationRunStatus.Success
    )
    assertpy.assert_that(history["events"][-1]["type"]).is_equal_to("ExecutionSucceeded")


def test_pp_configuration_fail_path(start_execution, wait_for_execution, mocked_test_event):
    # ARRANGE

    # ACT
    execution_arn = start_execution(test_name="FailPath", test_event=mocked_test_event)
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to(
        provisioned_product_configuration_state_machine.AdditionalConfigurationRunStatus.Failed
    )
    assertpy.assert_that(output).is_none()
    assertpy.assert_that(history["events"][-1]["type"]).is_equal_to("ExecutionFailed")


def test_pp_configuration_retry_success_path(start_execution, wait_for_execution, mocked_test_event):
    # ARRANGE

    # ACT
    execution_arn = start_execution(test_name="RetrySuccessPath", test_event=mocked_test_event)
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("SUCCEEDED")
    assertpy.assert_that(output).is_not_none()
    output_parsed = json.loads(output)
    assertpy.assert_that(output_parsed["getProvisionedProductConfigurationStatusResponse"]["status"]).is_equal_to(
        provisioned_product_configuration_state_machine.AdditionalConfigurationRunStatus.Success
    )
    assertpy.assert_that(history["events"][-1]["type"]).is_equal_to("ExecutionSucceeded")
