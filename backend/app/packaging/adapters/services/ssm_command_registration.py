from datetime import datetime, timedelta, timezone

from botocore.exceptions import ClientError

SSM_INVOCATION_REGISTRATION_GRACE_PERIOD = timedelta(minutes=5)


def invocation_is_registering(error: ClientError, submitted_at: str | None) -> bool:
    if error.response.get("Error", {}).get("Code") != "InvocationDoesNotExist":
        raise error
    # Older executions without submission times retain the original failure behavior.
    if submitted_at is None:
        return False
    # Polling must not renew the registration grace period.
    age = datetime.now(timezone.utc) - datetime.fromisoformat(submitted_at)
    return age < SSM_INVOCATION_REGISTRATION_GRACE_PERIOD
