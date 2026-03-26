import warnings
from typing import Any, Tuple

import boto3


class STSAPI:
    """Secondary adapter for the AWS STS API."""

    def __init__(self, account_id: str, region: str, target_role: str, user_id: str, boto_session: Any = None):
        warnings.warn("Use app/shared/adapters/boto/boto_provider.py instead.", DeprecationWarning)

        self._account_id = account_id
        self._region = region
        self._target_role = target_role
        self._user_id = user_id
        self._sts_client = (
            boto_session.client("sts", region_name=region) if boto_session else boto3.client("sts", region_name=region)
        )

    def get_temp_creds(self) -> Tuple[str, str, str]:
        """Returns temporary credentials on the target account by assuming a role."""

        return self._access_key_id, self._secret_access_key, self._session_token

    def __enter__(self):
        assumed_role_object = self._sts_client.assume_role(
            RoleArn=f"arn:aws:iam::{self._account_id}:role/{self._target_role}",
            RoleSessionName=self._user_id,
            Tags=[
                {"Key": "UserId", "Value": self._user_id},
            ],
            TransitiveTagKeys=[
                "UserId",
            ],
        )

        credentials = assumed_role_object["Credentials"]
        self._access_key_id = credentials["AccessKeyId"]
        self._secret_access_key = credentials["SecretAccessKey"]
        self._session_token = credentials["SessionToken"]
        return self

    def __exit__(self, *args):
        self._access_key_id = None
        self._secret_access_key = None
        self._session_token = None
