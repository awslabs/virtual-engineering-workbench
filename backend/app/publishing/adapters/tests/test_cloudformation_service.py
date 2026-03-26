from unittest import mock

import assertpy
import boto3
from mypy_boto3_cloudformation import client

from app.publishing.adapters.services import cloud_formation_service


def test_validate_template_returns_true_when_valid(mock_moto_calls):
    # ARRANGE
    cf_srv = cloud_formation_service.CloudFormationService("admin", "tools_account_id", "us-east-1")

    # ACT
    is_valid, parameters, error_message = cf_srv.validate_template(template_body="valid template")

    # ASSERT
    assertpy.assert_that(is_valid).is_true()
    assertpy.assert_that(parameters).is_length(2)


def test_validate_template_returns_false_when_invalid(mock_moto_calls):
    # ARRANGE
    cf_client: client.CloudFormationClient = boto3.client("servicecatalog")
    mock_moto_calls["ValidateTemplate"] = mock.MagicMock(
        side_effect=cf_client.exceptions.ClientError(
            operation_name="ValidateTemplate",
            error_response={
                "Error": {
                    "Type": "Sender",
                    "Code": "ValidationError",
                    "Message": "Template format error: unsupported structure.",
                }
            },
        )
    )
    cf_srv = cloud_formation_service.CloudFormationService("admin", "tools_account_id", "us-east-1")

    # ACT
    is_valid, parameters, error_message = cf_srv.validate_template(template_body="invalid template")

    # ASSERT
    assertpy.assert_that(is_valid).is_false()
    assertpy.assert_that(error_message).is_equal_to("Template format error: unsupported structure.")
