import json

import assertpy


def test_recipe_version_test_success(start_execution, wait_for_execution, mocked_test_event):
    # ARRANGE & ACT
    execution_arn = start_execution(test_name="RecipeVersionTestSuccess", test_event=mocked_test_event)
    status, output, history = wait_for_execution(execution_arn=execution_arn)  # ASSERT

    assertpy.assert_that(status).is_equal_to("SUCCEEDED")
    assertpy.assert_that(output).is_not_none()

    output_parsed = json.loads(output)

    assertpy.assert_that(output_parsed["testExecutionDetails"]["recipeVersionTestStatus"]).is_equal_to("SUCCESS")


def test_recipe_version_test_fail(start_execution, wait_for_execution, mocked_test_event):
    # ARRANGE & ACT
    execution_arn = start_execution(test_name="RecipeVersionTestFail", test_event=mocked_test_event)
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("FAILED")
