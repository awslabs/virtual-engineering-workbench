import uuid
from typing import Optional

import boto3


class SecretsManagerAPI:
    """Secondary adapter for the AWS Secrets Manager API."""

    def __init__(
        self,
        region: str,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        session_token: Optional[str] = None,
        session=None,
    ):
        self._client = (
            session.client(
                "secretsmanager",
                region_name=region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                aws_session_token=session_token,
            )
            if session
            else boto3.client(
                "secretsmanager",
                region_name=region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                aws_session_token=session_token,
            )
        )

    def get_secret_value(self, secret_id: str) -> str:
        """Returns the secret value for the given secret id."""

        response = self._client.get_secret_value(SecretId=secret_id)
        return response.get("SecretString")

    def create_secret(self, name: str, value: str) -> str:
        """Puts a secret to the Secrets Manager for the given secret id and returns the secret ARN."""

        response = self._client.create_secret(Name=name, SecretString=value, ClientRequestToken=str(uuid.uuid4()))
        return response.get("ARN")
