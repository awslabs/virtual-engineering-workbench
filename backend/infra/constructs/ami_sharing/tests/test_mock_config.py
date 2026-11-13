import json
from pathlib import Path

MOCK_CONFIG = Path(__file__).with_name("MockConfigFile.json")
DECIDE_ACTION_FIELDS = {
    "eventType",
    "decision",
    "originalAmiId",
    "copiedAmiId",
    "region",
    "imageId",
    "projectId",
    "licenseArn",
    "homeRegion",
    "grantName",
}


def _config() -> dict:
    return json.loads(MOCK_CONFIG.read_text())


def test_every_decide_action_mock_supplies_the_unconditional_result_selector_fields():
    responses = _config()["MockedResponses"]
    decide_responses = {
        name: response["0"]["Return"]["Payload"]
        for name, response in responses.items()
        if name.startswith("MockedDecideActionLambda")
    }

    assert decide_responses
    for name, payload in decide_responses.items():
        assert set(payload) == DECIDE_ACTION_FIELDS, name


def test_create_grant_mock_uses_a_realistic_license_manager_grant_arn():
    payload = _config()["MockedResponses"]["MockedCreateLicenseGrantLambda"]["0"]["Return"]["Payload"]

    assert payload["grantArn"] == "arn:aws:license-manager:eu-west-3:123456789012:grant:g-12345"


def test_not_required_path_uses_a_genuine_not_required_decision():
    config = _config()
    test_case = config["StateMachines"]["AmiSharingStateMachine"]["TestCases"]["NotRequiredPath"]
    response_name = test_case["DecideActionLambda"]
    payload = config["MockedResponses"][response_name]["0"]["Return"]["Payload"]

    assert payload["decision"] == "NOT_REQUIRED"
