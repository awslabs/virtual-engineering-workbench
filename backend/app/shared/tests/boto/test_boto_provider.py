from unittest import mock

import assertpy
import pytest

from app.shared.adapters.boto import boto_provider
from app.shared.adapters.exceptions.adapter_exception import AdapterException


def test_get_client_when_account_is_specified_should_assume_role(logger, mock_context_provider):
    # ARRANGE
    provider = boto_provider.BotoProvider(ctx=mock_context_provider, logger=logger)
    opts = boto_provider.BotoProviderOptions(
        aws_account_id="001234567890",
        aws_region="eu-central-1",
        aws_role_name="TestRole",
        aws_session_name="TestSession",
    )

    # ACT

    cl = provider.client("sts")(opts)

    # ASSERT
    assertpy.assert_that(cl.get_caller_identity().get("Account")).is_equal_to("001234567890")
    assertpy.assert_that(cl.get_caller_identity().get("Arn")).is_equal_to(
        "arn:aws:sts::001234567890:assumed-role/TestRole/TestSession"
    )


@pytest.mark.parametrize(
    "account_id,region,role_name,session_name",
    [
        ("001234567890", "eu-central-1", None, "Session"),
        ("001234567890", "eu-central-1", "RoleName", None),
    ],
)
def test_get_client_when_account_is_specified_should_validate_other_parameters(
    logger, mock_context_provider, account_id, region, role_name, session_name
):
    # ARRANGE
    provider = boto_provider.BotoProvider(ctx=mock_context_provider, logger=logger)
    opts = boto_provider.BotoProviderOptions(
        aws_account_id=account_id,
        aws_region=region,
        aws_role_name=role_name,
        aws_session_name=session_name,
    )

    # ACT
    with pytest.raises(AdapterException) as exc:
        provider.client("sts")(opts)

    # ASSERT
    assertpy.assert_that(str(exc.value)).is_equal_to(
        "BotoProvider: Assuming role requires full set of parameters: aws_role_name, aws_session_name"
    )


def test_get_client_when_account_is_not_specified_should_get_client_in_current_account(logger, mock_context_provider):
    # ARRANGE
    provider = boto_provider.BotoProvider(ctx=mock_context_provider, logger=logger)
    opts = boto_provider.BotoProviderOptions(
        aws_region="eu-central-1",
        aws_role_name="TestRole",
        aws_session_name="TestSession",
    )

    # ACT

    cl = provider.client("sts")(opts)

    # ASSERT
    assertpy.assert_that(cl.get_caller_identity().get("Account")).is_equal_to("123456789012")
    assertpy.assert_that(cl.get_caller_identity().get("Arn")).is_equal_to("arn:aws:sts::123456789012:user/moto")


def test_get_client_when_multiple_clients_requested_should_reuse_credentials(
    logger, mock_context_provider, mock_aws_client
):
    # ARRANGE
    provider = boto_provider.BotoProvider(ctx=mock_context_provider, logger=logger)
    provider._sts_client = mock.MagicMock()
    provider._sts_client.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "test",
            "SecretAccessKey": "test",
            "SessionToken": "test",
        }
    }

    opts = boto_provider.BotoProviderOptions(
        aws_account_id="001234567890",
        aws_region="eu-central-1",
        aws_role_name="TestRole",
        aws_session_name="TestSession",
    )

    # ACT
    provider.client("sts")(opts)
    provider.client("ec2")(opts)

    # ASSERT
    provider._sts_client.assume_role.assert_called_once()


def test_get_client_when_multiple_clients_requested_for_different_accounts_should_get_new_credentials(
    logger, mock_context_provider, mock_aws_client
):
    # ARRANGE
    provider = boto_provider.BotoProvider(ctx=mock_context_provider, logger=logger)
    provider._sts_client = mock.MagicMock()
    provider._sts_client.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "test",
            "SecretAccessKey": "test",
            "SessionToken": "test",
        }
    }

    opts1 = boto_provider.BotoProviderOptions(
        aws_account_id="001234567890",
        aws_region="eu-central-1",
        aws_role_name="TestRole",
        aws_session_name="TestSession",
    )
    opts2 = boto_provider.BotoProviderOptions(
        aws_account_id="123456789000",
        aws_region="eu-central-1",
        aws_role_name="TestRole",
        aws_session_name="TestSession",
    )

    # ACT
    provider.client("sts")(opts1)
    provider.client("ec2")(opts2)

    # ASSERT
    assertpy.assert_that(provider._sts_client.assume_role.call_count).is_equal_to(2)
