import json

import assertpy


def test_component_version_test_success(start_execution, wait_for_execution, mocked_test_event):
    # ARRANGE & ACT
    execution_arn = start_execution(test_name="ComponentVersionTestSuccess", test_event=mocked_test_event)
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("SUCCEEDED")
    assertpy.assert_that(output).is_not_none()

    output_parsed = json.loads(output)

    assertpy.assert_that(output_parsed["testExecutionDetails"]["componentVersionTestStatus"]).is_equal_to("SUCCESS")


def test_component_version_test_fail(start_execution, wait_for_execution, mocked_test_event):
    # ARRANGE & ACT
    execution_arn = start_execution(test_name="ComponentVersionTestFail", test_event=mocked_test_event)
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("FAILED")
