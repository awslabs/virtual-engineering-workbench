import json
from unittest import mock

import assertpy

from app.provisioning.adapters.services import ssm_session_credentials_service


def _make_service(connection_status: str):
    sts_client = mock.MagicMock()
    sts_client.assume_role.return_value = {
        "Credentials": {"AccessKeyId": "AKIA", "SecretAccessKey": "secret", "SessionToken": "token"}
    }
    ssm_client = mock.MagicMock()
    ssm_client.get_connection_status.return_value = {"Target": "i-0123", "Status": connection_status}
    service = ssm_session_credentials_service.SSMSessionCredentialsService(
        sts_client=sts_client,
        ssm_boto_client_provider=mock.MagicMock(return_value=ssm_client),
        role_name="ProvisioningRole",
    )
    return service, sts_client


def _get_session_credentials(service):
    return service.get_session_credentials(
        aws_account_id="001234567890", region="eu-west-1", user_id="T0011AA", instance_id="i-0123"
    )


def test_get_session_credentials_assumes_the_role_narrowed_to_the_instance():
    # ARRANGE
    service, sts_client = _make_service("connected")

    # ACT
    credentials = _get_session_credentials(service)

    # ASSERT
    assertpy.assert_that(credentials.model_dump()).is_equal_to(
        {
            "accessKeyId": "AKIA",
            "secretAccessKey": "secret",
            "sessionToken": "token",
            "instanceId": "i-0123",
            "region": "eu-west-1",
        }
    )
    assume_role = sts_client.assume_role.call_args.kwargs
    assertpy.assert_that(assume_role["RoleArn"]).is_equal_to("arn:aws:iam::001234567890:role/ProvisioningRole")
    assertpy.assert_that(assume_role["RoleSessionName"]).is_equal_to("T0011AA")
    assertpy.assert_that(assume_role["Tags"]).is_equal_to([{"Key": "UserId", "Value": "T0011AA"}])
    assertpy.assert_that(json.loads(assume_role["Policy"])["Statement"]).is_equal_to(
        [
            {
                "Effect": "Allow",
                "Action": "ssm:StartSession",
                "Resource": [
                    "arn:aws:ec2:eu-west-1:001234567890:instance/i-0123",
                    "arn:aws:ssm:eu-west-1:001234567890:document/SSM-SessionManagerRunShell",
                ],
            },
            {
                "Effect": "Allow",
                "Action": ["ssm:TerminateSession", "ssm:ResumeSession", "ssmmessages:OpenDataChannel"],
                "Resource": "arn:aws:ssm:*:*:session/T0011AA-*",
            },
        ]
    )


def test_get_session_credentials_returns_none_while_the_ssm_agent_is_not_connected():
    # ARRANGE
    service, sts_client = _make_service("notconnected")

    # ACT
    credentials = _get_session_credentials(service)

    # ASSERT
    assertpy.assert_that(credentials).is_none()
    sts_client.assume_role.assert_not_called()
