import json
import typing

from mypy_boto3_ssm.client import SSMClient
from mypy_boto3_sts.client import STSClient

from app.provisioning.domain.model import session_credentials
from app.provisioning.domain.ports import session_credentials_service


class SSMSessionCredentialsService(session_credentials_service.SessionCredentialsService):
    def __init__(
        self,
        sts_client: STSClient,
        ssm_boto_client_provider: typing.Callable[[str, str, str], SSMClient],
        role_name: str,
    ):
        self._sts_client = sts_client
        self._ssm_boto_client_provider = ssm_boto_client_provider
        self._role_name = role_name

    def get_session_credentials(
        self, aws_account_id: str, region: str, user_id: str, instance_id: str
    ) -> session_credentials.SessionCredentials | None:
        ssm = self._ssm_boto_client_provider(aws_account_id, region, user_id)
        if ssm.get_connection_status(Target=instance_id).get("Status") != "connected":
            return None

        # The session policy narrows the role to this one instance, so the credentials cannot use the rest of it.
        # Session Manager names a session after the role session name, the user ID here.
        session_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "ssm:StartSession",
                    "Resource": [
                        f"arn:aws:ec2:{region}:{aws_account_id}:instance/{instance_id}",
                        f"arn:aws:ssm:{region}:{aws_account_id}:document/SSM-SessionManagerRunShell",
                    ],
                },
                {
                    "Effect": "Allow",
                    "Action": ["ssm:TerminateSession", "ssm:ResumeSession", "ssmmessages:OpenDataChannel"],
                    "Resource": f"arn:aws:ssm:*:*:session/{user_id}-*",
                },
            ],
        }
        credentials = self._sts_client.assume_role(
            RoleArn=f"arn:aws:iam::{aws_account_id}:role/{self._role_name}",
            RoleSessionName=user_id,
            Tags=[{"Key": "UserId", "Value": user_id}],
            Policy=json.dumps(session_policy),
        )["Credentials"]

        return session_credentials.SessionCredentials(
            accessKeyId=credentials["AccessKeyId"],
            secretAccessKey=credentials["SecretAccessKey"],
            sessionToken=credentials["SessionToken"],
            instanceId=instance_id,
            region=region,
        )
