"""Turn a Step Functions error object into a short reason for a user to read.

`$.error` reaches FailAmiSharingLambda in one of two shapes:

* from a task `Catch`, where `Cause` is a JSON string carrying `errorType`,
  `errorMessage` and a `trace` array, or
* from one of the Pass states on a failing `Choice` branch, where `Cause` is
  already a plain sentence.

Only the type and the message are kept. The stack trace is never included: it is
long, it is of no use to the person looking at a failed product version, and it
exposes internal file paths. The result is capped so one failure cannot write an
unbounded string into the version record.
"""

import json
from typing import Any, Optional

MAX_REASON_LENGTH = 1000


def summarize(error: Optional[dict[str, Any]]) -> Optional[str]:
    """A single-line reason, or None when there is nothing useful to report."""
    if not error:
        return None

    name = _clean(error.get("Error"))
    detail = _detail_from_cause(error.get("Cause"))

    parts = [part for part in (name, detail) if part]
    if not parts:
        return None
    return ": ".join(parts)[:MAX_REASON_LENGTH]


def _detail_from_cause(cause: Any) -> Optional[str]:
    if not isinstance(cause, str) or not cause.strip():
        return None
    try:
        parsed = json.loads(cause)
    except (ValueError, TypeError):
        # Already a plain sentence, as the Choice-branch Pass states produce.
        return _clean(cause)

    if not isinstance(parsed, dict):
        return _clean(cause)

    # Deliberately ignores parsed.get("trace").
    fields = [_clean(parsed.get("errorType")), _clean(parsed.get("errorMessage"))]
    joined = " ".join(field for field in fields if field)
    return joined or None


def _clean(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    collapsed = " ".join(value.split())
    return collapsed or None
