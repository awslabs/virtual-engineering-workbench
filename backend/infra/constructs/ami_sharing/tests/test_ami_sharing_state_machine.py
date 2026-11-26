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
            "PassMarketplaceAmi",
            "LicenseDecisionChoice",
            "CreateLicenseGrantLambda",
            "AcceptLicenseGrantLambda",
            "VerifyLaunchPermissionLambda",
            "VerifyLaunchPermissionChoice",
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
            "PassMarketplaceAmi",
            "LicenseDecisionChoice",
            "VerifyExternalGrantLambda",
            "VerifyExternalGrantChoice",
            "VerifyLaunchPermissionLambda",
            "VerifyLaunchPermissionChoice",
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
    """A spoke that cannot launch the regional Marketplace AMI must fail, not succeed."""
    # ARRANGE

    # ACT
    execution_arn = start_execution(test_name="LaunchPermissionDeniedPath", test_event=mocked_test_event())
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("FAILED")
    entered = [event["stateEnteredEventDetails"]["name"] for event in history if event.get("stateEnteredEventDetails")]
    assertpy.assert_that(entered).contains("FailAmiSharingLambda")
    assertpy.assert_that(entered).does_not_contain("SucceedAmiSharingLambda")


def test_ami_sharing_built_image_copy_then_license_grant_path(start_execution, wait_for_execution, mocked_test_event):
    """An image built on a Marketplace AMI is copied and shared first, then licensed."""
    # ARRANGE

    # ACT
    execution_arn = start_execution(test_name="BuiltImageCopyLicenseGrantPath", test_event=mocked_test_event())
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("SUCCEEDED")
    assertpy.assert_that(_entered_states(history)).is_equal_to(
        [
            "StartState",
            "CheckOldVersionIdChoice",
            "PassAssignOldVersionId",
            "DecideActionLambda",
            "DecideActionChoice",
            "CopyAmiLambda",
            "PassCopy",
            "VerifyCopyLambda",
            "VerifyCopyChoice",
            "ShareAmiLambda",
            "LicenseDecisionChoice",
            "CreateLicenseGrantLambda",
            "AcceptLicenseGrantLambda",
            "VerifyLaunchPermissionLambda",
            "VerifyLaunchPermissionChoice",
            "SucceedAmiSharingLambda",
            "SuccessState",
        ]
    )


def test_ami_sharing_built_image_done_then_verify_external_grant_path(
    start_execution, wait_for_execution, mocked_test_event
):
    """An image built on a Marketplace AMI that is shared already still has its grant verified."""
    # ARRANGE

    # ACT
    execution_arn = start_execution(test_name="BuiltImageDoneVerifyExternalGrantPath", test_event=mocked_test_event())
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("SUCCEEDED")
    assertpy.assert_that(_entered_states(history)).is_equal_to(
        [
            "StartState",
            "CheckOldVersionIdChoice",
            "PassAssignOldVersionId",
            "DecideActionLambda",
            "DecideActionChoice",
            "PassDone",
            "LicenseDecisionChoice",
            "VerifyExternalGrantLambda",
            "VerifyExternalGrantChoice",
            "VerifyLaunchPermissionLambda",
            "VerifyLaunchPermissionChoice",
            "SucceedAmiSharingLambda",
            "SuccessState",
        ]
    )


GRANT_REFUSED_FALLBACK_STATES = [
    "StartState",
    "CheckOldVersionIdChoice",
    "PassAssignOldVersionId",
    "DecideActionLambda",
    "DecideActionChoice",
    "PassMarketplaceAmi",
    "LicenseDecisionChoice",
    "CreateLicenseGrantLambda",
    "VerifyExternalGrantLambda",
    "VerifyExternalGrantChoice",
    "VerifyLaunchPermissionLambda",
    "VerifyLaunchPermissionChoice",
    "SucceedAmiSharingLambda",
    "SuccessState",
]


def test_ami_sharing_falls_back_to_the_spoke_grant_when_aws_refuses_the_grant(
    start_execution, wait_for_execution, mocked_test_event
):
    # ACT
    execution_arn = start_execution(test_name="LicenseGrantRejectedFallbackPath", test_event=mocked_test_event())
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT — a refused grant ends like an externally managed image whose spoke has a grant
    assertpy.assert_that(status).is_equal_to("SUCCEEDED")
    assertpy.assert_that(json.loads(output)["licenseGrantError"]["Error"]).is_equal_to("LicenseGrantRejectedException")
    assertpy.assert_that(_entered_states(history)).is_equal_to(GRANT_REFUSED_FALLBACK_STATES)


def test_ami_sharing_fails_when_aws_refuses_the_grant_and_the_spoke_has_none(
    start_execution, wait_for_execution, mocked_test_event
):
    # ACT
    execution_arn = start_execution(test_name="LicenseGrantRejectedNoSpokeGrantPath", test_event=mocked_test_event())
    status, _, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("FAILED")
    entered = _entered_states(history)
    assertpy.assert_that(entered).contains(
        "VerifyExternalGrantLambda", "PassGrantNotVerifiedError", "FailAmiSharingLambda"
    )


def test_ami_sharing_falls_back_when_the_grant_never_reaches_the_spoke(
    start_execution, wait_for_execution, mocked_test_event
):
    # ACT
    execution_arn = start_execution(test_name="LicenseGrantNotDeliveredFallbackPath", test_event=mocked_test_event())
    # The accept step retries three times (10 s, 20 s, 40 s) before the catch applies.
    status, _, history = wait_for_execution(execution_arn=execution_arn, max_retries=25)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("SUCCEEDED")
    entered = _entered_states(history)
    assertpy.assert_that(entered).contains("AcceptLicenseGrantLambda", "VerifyExternalGrantLambda")
    assertpy.assert_that(entered).does_not_contain("FailAmiSharingLambda")


def test_ami_sharing_does_not_fall_back_on_a_transient_grant_error(
    start_execution, wait_for_execution, mocked_test_event
):
    # ACT — throttling is retryable later; hiding it behind the external check would mislead
    execution_arn = start_execution(test_name="LicenseGrantTransientErrorPath", test_event=mocked_test_event())
    status, _, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("FAILED")
    entered = _entered_states(history)
    assertpy.assert_that(entered).contains("FailAmiSharingLambda")
    assertpy.assert_that(entered).does_not_contain("VerifyExternalGrantLambda")
