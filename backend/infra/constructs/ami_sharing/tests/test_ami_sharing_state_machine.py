import json

import assertpy


def _entered_states(history: list[dict]) -> list[str]:
    return [event["stateEnteredEventDetails"]["name"] for event in history if event.get("stateEnteredEventDetails")]


def test_ami_sharing_copy_path(start_execution, wait_for_execution, mocked_test_event):
    # ARRANGE

    # ACT
    execution_arn = start_execution(test_name="CopyPath", test_event=mocked_test_event())
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
    execution_arn = start_execution(test_name="SharePath", test_event=mocked_test_event())
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
    execution_arn = start_execution(test_name="DonePath", test_event=mocked_test_event())
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


def test_ami_sharing_license_grant_path(start_execution, wait_for_execution, mocked_test_event):
    # ARRANGE

    # ACT
    execution_arn = start_execution(test_name="LicenseGrantPath", test_event=mocked_test_event())
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("SUCCEEDED")
    assertpy.assert_that(output).is_not_none()
    output_parsed = json.loads(output)
    assertpy.assert_that(output_parsed["succeedAmiSharingResponse"]["eventType"]).is_equal_to(
        "SucceedAmiSharingResponse"
    )
    assertpy.assert_that(_entered_states(history)).is_equal_to(
        [
            "StartState",
            "CheckOldVersionIdChoice",
            "PassAssignOldVersionId",
            "DecideActionLambda",
            "DecideActionChoice",
            "PassLicenseGrant",
            "CreateLicenseGrantLambda",
            "AcceptLicenseGrantLambda",
            "VerifyLaunchPermissionLambda",
            "VerifyLaunchPermissionChoice",
            "PassMarketplaceAmi",
            "SucceedAmiSharingLambda",
            "SuccessState",
        ]
    )


def test_ami_sharing_verify_external_grant_path(start_execution, wait_for_execution, mocked_test_event):
    # ARRANGE

    # ACT
    execution_arn = start_execution(test_name="VerifyExternalGrantPath", test_event=mocked_test_event())
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("SUCCEEDED")
    assertpy.assert_that(output).is_not_none()
    output_parsed = json.loads(output)
    assertpy.assert_that(output_parsed["succeedAmiSharingResponse"]["eventType"]).is_equal_to(
        "SucceedAmiSharingResponse"
    )
    assertpy.assert_that(_entered_states(history)).is_equal_to(
        [
            "StartState",
            "CheckOldVersionIdChoice",
            "PassAssignOldVersionId",
            "DecideActionLambda",
            "DecideActionChoice",
            "VerifyExternalGrantLambda",
            "VerifyExternalGrantChoice",
            "VerifyLaunchPermissionLambda",
            "VerifyLaunchPermissionChoice",
            "PassMarketplaceAmi",
            "SucceedAmiSharingLambda",
            "SuccessState",
        ]
    )


def test_ami_sharing_verify_external_grant_not_found_path(start_execution, wait_for_execution, mocked_test_event):
    # ARRANGE

    # ACT
    execution_arn = start_execution(test_name="VerifyExternalGrantNotFoundPath", test_event=mocked_test_event())
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("FAILED")


def test_ami_sharing_launch_permission_denied_path(start_execution, wait_for_execution, mocked_test_event):
    """A spoke that cannot launch the regional Marketplace AMI must fail, not succeed.

    Before VerifyLaunchPermissionChoice existed, both Marketplace paths ran straight
    from VerifyLaunchPermission to SucceedAmiSharing, so isAccessible=false was
    recorded as a successful share.
    """
    # ARRANGE

    # ACT
    execution_arn = start_execution(test_name="LaunchPermissionDeniedPath", test_event=mocked_test_event())
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("FAILED")
    entered = [event["stateEnteredEventDetails"]["name"] for event in history if event.get("stateEnteredEventDetails")]
    assertpy.assert_that(entered).contains("FailAmiSharingLambda")
    assertpy.assert_that(entered).does_not_contain("SucceedAmiSharingLambda")
