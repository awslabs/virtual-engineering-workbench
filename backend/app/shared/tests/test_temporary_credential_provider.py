from unittest import mock

import assertpy
import boto3
import botocore
import pytest

from app.shared.adapters.auth import temporary_credential_provider

orig = botocore.client.BaseClient._make_api_call


@pytest.fixture()
def mock_moto_calls(
    mock_assume_role,
):
    invocations = {
        "AssumeRole": mock_assume_role,
    }

    def _interceptor(self, operation_name, kwarg):
        if operation_name in invocations:
            return invocations[operation_name](**kwarg)

        return orig(self, operation_name, kwarg)

    with mock.patch("botocore.client.BaseClient._make_api_call", new=_interceptor):
        yield invocations


@pytest.fixture()
def mock_assume_role():
    return mock.MagicMock(
        return_value={
            "Credentials": {
                "AccessKeyId": "access-key-id",
                "SecretAccessKey": "secret-access-key",
                "SessionToken": "session-token",
                "Expiration": "2023-01-01",
            },
            "AssumedRoleUser": {
                "AssumedRoleId": "ARO123EXAMPLE123:Bob",
                "Arn": "arn:aws:sts::123456789012:assumed-role/demo/Bob",
            },
            "PackedPolicySize": 123,
            "SourceIdentity": "string",
        }
    )


class DictCtxProvider:
    def __init__(self):
        self._dict = {}

    def append_context(self, **additional_context):
        self._dict.update(**additional_context)

    @property
    def context(self) -> dict:
        return self._dict


def test_temporary_credential_provider_when_credential_does_not_exist_should_fetch_from_sts(
    mock_moto_calls, mock_assume_role
):
    # ARRANGE
    ctx = DictCtxProvider()

    cred_provider = temporary_credential_provider.TemporaryCredentialProvider(
        sts_client=boto3.client("sts", region_name="us-east-1"),
        ctx=ctx,
    )

    # ACT
    key, secret, token = cred_provider.get_for("001234567890", "Role", "UserId")

    # ASSERT
    mock_assume_role.assert_called_once_with(
        RoleArn="arn:aws:iam::001234567890:role/Role",
        RoleSessionName="UserId",
        Tags=[{"Key": "UserId", "Value": "UserId"}],
        TransitiveTagKeys=["UserId"],
    )
    assertpy.assert_that(key).is_equal_to("access-key-id")
    assertpy.assert_that(secret).is_equal_to("secret-access-key")
    assertpy.assert_that(token).is_equal_to("session-token")
    assertpy.assert_that(ctx.context).contains_entry(
        {"temp_creds": {"001234567890#Role#UserId": ("access-key-id", "secret-access-key", "session-token")}}
    )


def test_temporary_credential_provider_when_credential_exists_should_fetch_from_context(
    mock_moto_calls, mock_assume_role
):
    # ARRANGE
    ctx = DictCtxProvider()

    cred_provider = temporary_credential_provider.TemporaryCredentialProvider(
        sts_client=boto3.client("sts", region_name="us-east-1"),
        ctx=ctx,
    )
    cred_provider.get_for("001234567890", "Role", "UserId")
    mock_assume_role.reset_mock()

    # ACT
    key, secret, token = cred_provider.get_for("001234567890", "Role", "UserId")

    # ASSERT
    mock_assume_role.assert_not_called()
    assertpy.assert_that(key).is_equal_to("access-key-id")
    assertpy.assert_that(secret).is_equal_to("secret-access-key")
    assertpy.assert_that(token).is_equal_to("session-token")
