import warnings

from mypy_boto3_sts import client

from app.shared.adapters.boto import boto_provider


class SupportsContextManager(boto_provider.SupportsContextManager):
    pass


class TemporaryCredentialProvider:
    def __init__(
        self,
        sts_client: client.STSClient,
        ctx: SupportsContextManager,
    ):
        warnings.warn("Use app/shared/adapters/boto/boto_provider.py instead.", DeprecationWarning)

        self._sts_client = sts_client
        self._ctx = ctx

    def get_for(self, aws_account_id: str, role_name: str, session_name: str) -> (str, str, str):
        if not self._ctx.context.get("temp_creds", None):
            self._ctx.append_context(temp_creds={})

        key = TemporaryCredentialProvider.__temp_credential_key(
            aws_account_id=aws_account_id, role_name=role_name, session_name=session_name
        )

        if key not in self._ctx.context.get("temp_creds"):
            assumed_role_object = self._sts_client.assume_role(
                RoleArn=f"arn:aws:iam::{aws_account_id}:role/{role_name}",
                RoleSessionName=session_name,
                Tags=[
                    {"Key": "UserId", "Value": session_name},
                ],
                TransitiveTagKeys=[
                    "UserId",
                ],
            )

            credentials = assumed_role_object["Credentials"]
            self._ctx.context.get("temp_creds")[key] = (
                credentials["AccessKeyId"],
                credentials["SecretAccessKey"],
                credentials["SessionToken"],
            )

        return self._ctx.context.get("temp_creds").get(key)

    @staticmethod
    def __temp_credential_key(aws_account_id: str, role_name: str, session_name: str):
        return f"{aws_account_id}#{role_name}#{session_name}"
