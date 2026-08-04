import logging
from unittest import mock

import assertpy
import boto3
import moto
import pytest

from app.projects.adapters.services import cognito_user_directory_service

TEST_REGION = "us-east-1"


@pytest.fixture
def cognito_client():
    with moto.mock_aws():
        yield boto3.client("cognito-idp", region_name=TEST_REGION)


@pytest.fixture
def user_pool(cognito_client):
    pool = cognito_client.create_user_pool(
        PoolName="test-pool",
        Schema=[
            {
                "Name": "user_tid",
                "AttributeDataType": "String",
                "Mutable": True,
                "Required": False,
            },
            {
                "Name": "email",
                "AttributeDataType": "String",
                "Mutable": True,
                "Required": True,
            },
        ],
        UsernameAttributes=["email"],
    )
    return pool["UserPool"]


def _create_user(cognito_client, user_pool_id, email, user_tid):
    cognito_client.admin_create_user(
        UserPoolId=user_pool_id,
        Username=email,
        UserAttributes=[
            {"Name": "email", "Value": email},
            {"Name": "email_verified", "Value": "true"},
            {"Name": "custom:user_tid", "Value": user_tid},
        ],
        MessageAction="SUPPRESS",
    )


def test_returns_email_when_user_tid_matches(cognito_client, user_pool):
    # Arrange
    _create_user(cognito_client, user_pool["Id"], "alice@example.com", "ALICE")
    _create_user(cognito_client, user_pool["Id"], "bob@example.com", "BOB")

    service = cognito_user_directory_service.CognitoUserDirectoryService(
        cognito_client=cognito_client,
        user_pool_id=user_pool["Id"],
        logger=logging.getLogger("test"),
    )

    # Act & Assert
    assertpy.assert_that(service.get_user_email("ALICE")).is_equal_to("alice@example.com")
    assertpy.assert_that(service.get_user_email("BOB")).is_equal_to("bob@example.com")


def test_returns_none_when_user_tid_not_found(cognito_client, user_pool):
    # Arrange
    _create_user(cognito_client, user_pool["Id"], "alice@example.com", "ALICE")

    service = cognito_user_directory_service.CognitoUserDirectoryService(
        cognito_client=cognito_client,
        user_pool_id=user_pool["Id"],
        logger=logging.getLogger("test"),
    )

    # Act & Assert
    assertpy.assert_that(service.get_user_email("DOES_NOT_EXIST")).is_none()


def test_returns_none_for_empty_user_tid(cognito_client, user_pool):
    service = cognito_user_directory_service.CognitoUserDirectoryService(
        cognito_client=cognito_client,
        user_pool_id=user_pool["Id"],
        logger=logging.getLogger("test"),
    )

    assertpy.assert_that(service.get_user_email("")).is_none()


def test_match_is_case_sensitive_on_user_tid(cognito_client, user_pool):
    # Cognito stores custom attributes verbatim; different casings are
    # different values. Callers upstream already canonicalise to uppercase
    # before persisting, so this guards that contract.
    _create_user(cognito_client, user_pool["Id"], "alice@example.com", "ALICE")

    service = cognito_user_directory_service.CognitoUserDirectoryService(
        cognito_client=cognito_client,
        user_pool_id=user_pool["Id"],
        logger=logging.getLogger("test"),
    )

    assertpy.assert_that(service.get_user_email("ALICE")).is_equal_to("alice@example.com")
    assertpy.assert_that(service.get_user_email("alice")).is_none()


def test_returns_none_and_logs_when_cognito_raises():
    # Simulate an unavailable IdP — the adapter must degrade gracefully so
    # user onboarding is not blocked by a transient Cognito outage.
    broken_client = mock.MagicMock()
    broken_client.get_paginator.side_effect = RuntimeError("cognito is down")
    logger = mock.MagicMock(spec=logging.Logger)

    service = cognito_user_directory_service.CognitoUserDirectoryService(
        cognito_client=broken_client,
        user_pool_id="us-east-1_fake",
        logger=logger,
    )

    assertpy.assert_that(service.get_user_email("ALICE")).is_none()
    logger.exception.assert_called_once()
