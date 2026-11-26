import json

import assertpy
import aws_cdk
import pytest
from aws_cdk import aws_lambda
from aws_cdk.assertions import Template

from infra import config
from infra.constructs.ami_sharing import ami_sharing_state_machine

# Where every path stores the AMI the spoke account launches, for the states after it to read.
COPIED_AMI_PATH = "$.copiedAmi"


@pytest.fixture(scope="module")
def definition() -> dict:
    app = aws_cdk.App()
    stack = aws_cdk.Stack(app, "AmiSharingTest", env=aws_cdk.Environment(account="111111111111", region="eu-west-1"))
    app_config = config.AppConfig(
        account="111111111111",
        region="eu-west-1",
        environment="dev",
        web_app_account="111111111111",
        component_name="publishing",
        environment_config=config.env_config["dev"],
        component_specific=config.publishing_app_config["dev"],
    )
    ami_sharing_lambda = aws_lambda.Function(
        stack,
        "AmiSharingLambda",
        runtime=aws_lambda.Runtime.PYTHON_3_13,
        handler="handler.handler",
        code=aws_lambda.Code.from_inline("def handler(event, context): pass"),
    )
    ami_sharing_state_machine.AmiSharingStateMachine(
        stack, "AmiSharing", app_config=app_config, ami_sharing_lambda=ami_sharing_lambda
    )

    (state_machine,) = Template.from_stack(stack).find_resources("AWS::StepFunctions::StateMachine").values()
    # The definition is an Fn::Join of literal JSON and the Lambda ARN tokens.
    parts = state_machine["Properties"]["DefinitionString"]["Fn::Join"][1]
    return json.loads("".join(part if isinstance(part, str) else "LAMBDA_ARN" for part in parts))


def _transitions(state: dict) -> list[str]:
    targets = [choice["Next"] for choice in state.get("Choices", [])]
    targets += [state[key] for key in ("Next", "Default") if key in state]
    targets += [catch["Next"] for catch in state.get("Catch", [])]
    return targets


def _choice_targets(state: dict, variable: str) -> dict[str, str]:
    return {choice["StringEquals"]: choice["Next"] for choice in state["Choices"] if choice["Variable"] == variable}


def _payload(state: dict) -> dict:
    return state["Parameters"]["Payload"]


def test_every_transition_targets_a_defined_state(definition):
    # ARRANGE
    states = definition["States"]

    # ACT
    targets = {target for state in states.values() for target in _transitions(state)}

    # ASSERT
    assertpy.assert_that(states).contains_key(definition["StartAt"])
    assertpy.assert_that(set(states)).contains(*targets)
    for name, state in states.items():
        if state["Type"] in ("Choice", "Succeed", "Fail"):
            assertpy.assert_that(state).described_as(name).does_not_contain_key("Next")
        else:
            assertpy.assert_that("Next" in state).described_as(name).is_not_equal_to(state.get("End", False))


def test_decide_action_routes_marketplace_products_past_copy_and_share(definition):
    # ARRANGE
    states = definition["States"]

    # ACT
    decisions = _choice_targets(states["DecideActionChoice"], "$.decideActionResponse.decision")

    # ASSERT
    assertpy.assert_that(decisions).is_equal_to(
        {
            "COPY": "CopyAmiLambda",
            "SHARE": "PassShare",
            "DONE": "PassDone",
            "NOT_REQUIRED": "PassDone",
            "LICENSE_GRANT": "PassMarketplaceAmi",
            "VERIFY_EXTERNAL_GRANT": "PassMarketplaceAmi",
        }
    )
    assertpy.assert_that(states["DecideActionChoice"]["Default"]).is_equal_to("PassUnexpectedDecisionError")
    assertpy.assert_that(states["PassMarketplaceAmi"]["Parameters"]).is_equal_to(
        {"copiedAmiId.$": "$.decideActionResponse.imageId"}
    )
    assertpy.assert_that(states["PassMarketplaceAmi"]["Next"]).is_equal_to("LicenseDecisionChoice")


def test_copy_share_and_done_continue_with_the_license_decision(definition):
    # ARRANGE
    states = definition["States"]

    # ACT
    license_decisions = _choice_targets(states["LicenseDecisionChoice"], "$.decideActionResponse.licenseDecision")

    # ASSERT
    assertpy.assert_that(states["VerifyCopyChoice"]["Choices"][0]["Next"]).is_equal_to("ShareAmiLambda")
    assertpy.assert_that(states["ShareAmiLambda"]["Next"]).is_equal_to("LicenseDecisionChoice")
    assertpy.assert_that(states["PassDone"]["Next"]).is_equal_to("LicenseDecisionChoice")
    assertpy.assert_that(license_decisions).is_equal_to(
        {
            "NOT_REQUIRED": "SucceedAmiSharingLambda",
            "LICENSE_GRANT": "CreateLicenseGrantLambda",
            "VERIFY_EXTERNAL_GRANT": "VerifyExternalGrantLambda",
        }
    )
    assertpy.assert_that(states["LicenseDecisionChoice"]["Default"]).is_equal_to("PassUnexpectedDecisionError")


def test_license_states_end_in_succeed_ami_sharing(definition):
    # ARRANGE
    states = definition["States"]

    # ACT & ASSERT
    assertpy.assert_that(states["CreateLicenseGrantLambda"]["Next"]).is_equal_to("AcceptLicenseGrantLambda")
    assertpy.assert_that(states["AcceptLicenseGrantLambda"]["Next"]).is_equal_to("VerifyLaunchPermissionLambda")
    assertpy.assert_that(states["VerifyExternalGrantLambda"]["Next"]).is_equal_to("VerifyExternalGrantChoice")
    assertpy.assert_that(states["VerifyExternalGrantChoice"]["Choices"][0]["Next"]).is_equal_to(
        "VerifyLaunchPermissionLambda"
    )
    assertpy.assert_that(states["VerifyExternalGrantChoice"]["Default"]).is_equal_to("PassGrantNotVerifiedError")
    assertpy.assert_that(states["VerifyLaunchPermissionLambda"]["Next"]).is_equal_to("VerifyLaunchPermissionChoice")
    assertpy.assert_that(states["VerifyLaunchPermissionChoice"]["Choices"][0]["Next"]).is_equal_to(
        "SucceedAmiSharingLambda"
    )
    assertpy.assert_that(states["VerifyLaunchPermissionChoice"]["Default"]).is_equal_to(
        "PassLaunchPermissionDeniedError"
    )
    assertpy.assert_that(states["SucceedAmiSharingLambda"]["Next"]).is_equal_to("SuccessState")


def test_the_license_grant_is_created_for_the_registered_ami(definition):
    # ARRANGE
    payload = _payload(definition["States"]["CreateLicenseGrantLambda"])

    # ACT & ASSERT
    assertpy.assert_that(payload).contains_entry({"imageId.$": "$.decideActionResponse.originalAmiId"})


def test_every_failing_choice_sets_the_error_the_fail_state_reads(definition):
    # ARRANGE
    states = definition["States"]

    # ACT
    error_passes = {name for name, state in states.items() if state.get("ResultPath") == "$.error"}
    defaults = {state["Default"] for state in states.values() if state["Type"] == "Choice" and "Default" in state}

    # ASSERT
    assertpy.assert_that(defaults).does_not_contain("FailAmiSharingLambda")
    for name in error_passes:
        assertpy.assert_that(states[name]["Next"]).described_as(name).is_equal_to("FailAmiSharingLambda")


def test_decide_action_selects_the_license_decision(definition):
    # ARRANGE
    result_selector = definition["States"]["DecideActionLambda"]["ResultSelector"]

    # ACT & ASSERT
    assertpy.assert_that(result_selector).contains_entry({"licenseDecision.$": "$.Payload.licenseDecision"})


def test_verify_launch_permission_checks_the_ami_the_spoke_launches(definition):
    # ARRANGE
    payload = _payload(definition["States"]["VerifyLaunchPermissionLambda"])

    # ACT & ASSERT
    assertpy.assert_that(payload).contains_entry({"amiId.$": "$.copiedAmi.copiedAmiId"})
    assertpy.assert_that(payload).contains_entry({"region.$": "$.decideActionResponse.region"})


def test_every_path_sets_the_copied_ami_before_a_state_reads_it(definition):
    # ARRANGE
    states = definition["States"]
    readers = {name for name, state in states.items() if COPIED_AMI_PATH in json.dumps(state.get("Parameters", {}))}
    writers = {name for name, state in states.items() if state.get("ResultPath") == COPIED_AMI_PATH}

    # ACT: walk every (state, copiedAmi set) pair reachable from the start
    unset_reads = set()
    visited = set()
    queue = [(definition["StartAt"], False)]
    while queue:
        name, is_set = queue.pop()
        if (name, is_set) in visited:
            continue
        visited.add((name, is_set))
        if name in readers and not is_set:
            unset_reads.add(name)
        is_set = is_set or name in writers
        queue.extend((target, is_set) for target in _transitions(states[name]))

    # ASSERT
    assertpy.assert_that(readers).contains(
        "ShareAmiLambda",
        "VerifyCopyLambda",
        "VerifyExternalGrantLambda",
        "VerifyLaunchPermissionLambda",
        "SucceedAmiSharingLambda",
    )
    assertpy.assert_that(unset_reads).is_empty()
