import json

import assertpy
import pytest


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
            "GrantAfterShareChoice",
            "PassNoGrantAfterShare",
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
            "GrantAfterShareChoice",
            "PassNoGrantAfterShare",
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


GRANT_REFUSED_FALLBACK_STATES = [
    "StartState",
    "CheckOldVersionIdChoice",
    "PassAssignOldVersionId",
    "DecideActionLambda",
    "DecideActionChoice",
    "PassLicenseGrant",
    "CreateLicenseGrantLambda",
    "VerifyExternalGrantLambda",
    "VerifyExternalGrantChoice",
    "VerifyLaunchPermissionLambda",
    "VerifyLaunchPermissionChoice",
    "PassMarketplaceAmi",
    "GrantAfterShareChoice",
    "PassNoGrantAfterShare",
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


def _assert_fail_lambda_ran(history: list[dict]) -> None:
    """The Fail lambda must complete. If it cannot resolve $.error, Step Functions fails the
    execution with States.Runtime before the lambda runs, so the version is never marked Failed."""
    exited = [e["stateExitedEventDetails"]["name"] for e in history if e.get("stateExitedEventDetails")]
    assertpy.assert_that(exited).contains("FailAmiSharingLambda")
    runtime_errors = [e for e in history if "States.Runtime" in json.dumps(e, default=str)]
    assertpy.assert_that(runtime_errors).is_empty()


def _assert_succeeded(status, output):
    assertpy.assert_that(status).is_equal_to("SUCCEEDED")
    assertpy.assert_that(output).is_not_none()
    output_parsed = json.loads(output)
    assertpy.assert_that(output_parsed["succeedAmiSharingResponse"]["eventType"]).is_equal_to(
        "SucceedAmiSharingResponse"
    )


# Images built on a Marketplace AMI: our own AMI is shared or copied first, then the
# spoke gets the parent's license.


@pytest.mark.parametrize(
    "test_name,share_states",
    (
        ("ShareThenLicenseGrantPath", ["PassShare", "ShareAmiLambda"]),
        ("CopyThenLicenseGrantPath", ["CopyAmiLambda", "VerifyCopyLambda", "ShareAmiLambda"]),
    ),
)
def test_pipeline_image_on_marketplace_ami_is_shared_then_granted(
    start_execution, wait_for_execution, mocked_test_event, test_name, share_states
):
    # ACT: our own AMI built on a Marketplace AMI
    execution_arn = start_execution(test_name=test_name, test_event=mocked_test_event())
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT: shared/copied first, then the license is granted and the launch checked in the spoke
    _assert_succeeded(status, output)
    entered = _entered_states(history)
    expected_order = share_states + [
        "CreateLicenseGrantAfterShareLambda",
        "AcceptLicenseGrantAfterShareLambda",
        "VerifyLaunchPermissionAfterShareLambda",
        "SucceedAmiSharingLambda",
    ]
    assertpy.assert_that([s for s in entered if s in expected_order]).is_equal_to(expected_order)
    assertpy.assert_that(entered).does_not_contain("CreateLicenseGrantLambda", "PassNoGrantAfterShare")


def test_pipeline_image_on_externally_managed_marketplace_ami_verifies_the_grant(
    start_execution, wait_for_execution, mocked_test_event
):
    # ACT
    execution_arn = start_execution(test_name="DoneThenVerifyExternalGrantPath", test_event=mocked_test_event())
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    _assert_succeeded(status, output)
    entered = _entered_states(history)
    assertpy.assert_that(entered).contains(
        "PassDone", "VerifyExternalGrantAfterShareLambda", "VerifyLaunchPermissionAfterShareLambda"
    )
    assertpy.assert_that(entered).does_not_contain("CreateLicenseGrantAfterShareLambda")


def test_pipeline_image_on_marketplace_ami_fails_without_external_grant(
    start_execution, wait_for_execution, mocked_test_event
):
    # ACT
    execution_arn = start_execution(test_name="DoneThenVerifyExternalGrantNotFoundPath", test_event=mocked_test_event())
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("FAILED")
    assertpy.assert_that(_entered_states(history)).contains("PassGrantNotVerifiedError", "FailAmiSharingLambda")
    _assert_fail_lambda_ran(history)


def test_pipeline_image_on_marketplace_ami_fails_when_the_spoke_cannot_see_it(
    start_execution, wait_for_execution, mocked_test_event
):
    # ACT
    execution_arn = start_execution(test_name="ShareThenLicenseGrantNotAccessiblePath", test_event=mocked_test_event())
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("FAILED")
    entered = _entered_states(history)
    assertpy.assert_that(entered).contains(
        "VerifyLaunchPermissionAfterShareChoice", "PassLaunchPermissionDeniedAfterShareError", "FailAmiSharingLambda"
    )
    assertpy.assert_that(entered).does_not_contain("SucceedAmiSharingLambda")
    _assert_fail_lambda_ran(history)


def test_pipeline_image_falls_back_to_the_spoke_grant_when_aws_refuses_the_grant(
    start_execution, wait_for_execution, mocked_test_event
):
    # ACT
    execution_arn = start_execution(
        test_name="ShareThenLicenseGrantRejectedFallbackPath", test_event=mocked_test_event()
    )
    status, output, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT: the same safety net as the direct LICENSE_GRANT path
    _assert_succeeded(status, output)
    assertpy.assert_that(json.loads(output)["licenseGrantError"]["Error"]).is_equal_to("LicenseGrantRejectedException")
    entered = _entered_states(history)
    assertpy.assert_that(entered).contains(
        "CreateLicenseGrantAfterShareLambda",
        "VerifyExternalGrantAfterShareLambda",
        "VerifyLaunchPermissionAfterShareLambda",
    )
    assertpy.assert_that(entered).does_not_contain("AcceptLicenseGrantAfterShareLambda", "FailAmiSharingLambda")


def test_pipeline_image_fails_when_aws_refuses_the_grant_and_the_spoke_has_none(
    start_execution, wait_for_execution, mocked_test_event
):
    # ACT
    execution_arn = start_execution(
        test_name="ShareThenLicenseGrantRejectedNoSpokeGrantPath", test_event=mocked_test_event()
    )
    status, _, history = wait_for_execution(execution_arn=execution_arn)

    # ASSERT
    assertpy.assert_that(status).is_equal_to("FAILED")
    assertpy.assert_that(_entered_states(history)).contains(
        "VerifyExternalGrantAfterShareLambda", "PassGrantNotVerifiedError", "FailAmiSharingLambda"
    )
    _assert_fail_lambda_ran(history)
