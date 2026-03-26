import json

import assertpy


def test_ami_sharing_copy_path(start_execution, wait_for_execution, mocked_test_event):
    # ARRANGE

    # ACT
    execution_arn = start_execution(test_name="CopyPath", test_event=mocked_test_event)
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("SUCCEEDED")
    assertpy.assert_that(output).is_not_none()
    output_parsed = json.loads(output)
    assertpy.assert_that(output_parsed["succeedAmiSharingResponse"]["eventType"]).is_equal_to(
        "SucceedAmiSharingResponse"
    )


def test_ami_sharing_share_path(start_execution, wait_for_execution, mocked_test_event):
    # ARRANGE

    # ACT
    execution_arn = start_execution(test_name="SharePath", test_event=mocked_test_event)
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("SUCCEEDED")
    assertpy.assert_that(output).is_not_none()
    output_parsed = json.loads(output)
    assertpy.assert_that(output_parsed["succeedAmiSharingResponse"]["eventType"]).is_equal_to(
        "SucceedAmiSharingResponse"
    )


def test_ami_sharing_done_path(start_execution, wait_for_execution, mocked_test_event):
    # ARRANGE

    # ACT
    execution_arn = start_execution(test_name="DonePath", test_event=mocked_test_event)
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("SUCCEEDED")
    assertpy.assert_that(output).is_not_none()
    output_parsed = json.loads(output)
    assertpy.assert_that(output_parsed["succeedAmiSharingResponse"]["eventType"]).is_equal_to(
        "SucceedAmiSharingResponse"
    )


def test_container_path(start_execution, wait_for_execution, mocked_test_event):
    # ARRANGE

    # ACT
    execution_arn = start_execution(test_name="NotRequiredPath", test_event=mocked_test_event(product_type="CONTAINER"))
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("SUCCEEDED")
    assertpy.assert_that(output).is_not_none()
    output_parsed = json.loads(output)
    assertpy.assert_that(output_parsed["succeedAmiSharingResponse"]["eventType"]).is_equal_to(
        "SucceedAmiSharingResponse"
    )
