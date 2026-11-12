import json

import assertpy
import pytest

from app.publishing.entrypoints.ami_sharing import step_error


def test_returns_none_when_there_is_no_error():
    assertpy.assert_that(step_error.summarize(None)).is_none()
    assertpy.assert_that(step_error.summarize({})).is_none()


def test_reads_a_plain_cause_from_a_choice_branch():
    """The Pass states on the failing Choice branches set a plain sentence."""
    reason = step_error.summarize(
        {
            "Error": "LaunchPermissionDenied",
            "Cause": "The target account cannot launch the regional Marketplace AMI.",
        }
    )
    assertpy.assert_that(reason).is_equal_to(
        "LaunchPermissionDenied: The target account cannot launch the regional Marketplace AMI."
    )


def test_reads_type_and_message_from_a_lambda_catch():
    cause = json.dumps(
        {
            "errorType": "AdapterException",
            "errorMessage": "Failed to create license grant: AccessDeniedException",
            "trace": [
                '  File "/var/task/app/publishing/handler.py", line 42, in handle',
                "    raise AdapterException(...)",
            ],
        }
    )
    reason = step_error.summarize({"Error": "AdapterException", "Cause": cause})
    assertpy.assert_that(reason).contains("AdapterException")
    assertpy.assert_that(reason).contains("Failed to create license grant")


def test_never_includes_the_stack_trace():
    """A trace is long, useless to the person reading a failed version, and names
    internal file paths."""
    cause = json.dumps(
        {
            "errorType": "ValueError",
            "errorMessage": "boom",
            "trace": ['  File "/var/task/secret/path.py", line 1, in f', "    raise ValueError"],
        }
    )
    reason = step_error.summarize({"Error": "ValueError", "Cause": cause})
    assertpy.assert_that(reason).does_not_contain("/var/task")
    assertpy.assert_that(reason).does_not_contain("File \"")
    assertpy.assert_that(reason).does_not_contain("trace")


def test_caps_the_length():
    cause = json.dumps({"errorType": "E", "errorMessage": "x" * 5000})
    reason = step_error.summarize({"Error": "E", "Cause": cause})
    assertpy.assert_that(len(reason)).is_less_than_or_equal_to(step_error.MAX_REASON_LENGTH)


def test_collapses_whitespace_so_the_reason_stays_one_line():
    reason = step_error.summarize({"Error": "E", "Cause": "first line\n\nsecond   line"})
    assertpy.assert_that(reason).is_equal_to("E: first line second line")


@pytest.mark.parametrize("cause", [None, "", "   ", 17, {"not": "a string"}])
def test_tolerates_a_missing_or_odd_cause(cause):
    reason = step_error.summarize({"Error": "OnlyAName", "Cause": cause})
    assertpy.assert_that(reason).is_equal_to("OnlyAName")


def test_unparseable_cause_is_used_as_text():
    reason = step_error.summarize({"Error": "E", "Cause": "not json {"})
    assertpy.assert_that(reason).is_equal_to("E: not json {")
