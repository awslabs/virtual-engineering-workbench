from unittest import mock

import assertpy
import pytest
from pydantic import ValidationError
from requests import HTTPError

from app.provisioning.adapters.exceptions import adapter_exception
from app.provisioning.adapters.query_services import publishing_api_query_service
from app.provisioning.domain.read_models import version


@mock.patch("app.shared.api.aws_api.AWSAPI")
def test_get_available_product_versions_returns_versions(mock_api, mock_logger, get_sample_version):
    # ARRANGE

    publishing_api_qry_srv = publishing_api_query_service.PublishingApiQueryService(api=mock_api, logger=mock_logger)
    mock_api.call_api.return_value = {
        "availableProductVersions": [
            get_sample_version().dict(),
            get_sample_version(version_id="vers-2").dict(),
            get_sample_version(version_id="vers-3").dict(),
        ]
    }

    # ACT
    versions = publishing_api_qry_srv.get_available_product_versions(product_id="prod-1")

    # ASSERT
    mock_api.call_api.assert_called_once_with(
        path="internal/available-products/prod-1/versions",
        http_method="GET",
    )
    assertpy.assert_that(versions).is_not_none()
    assertpy.assert_that(versions).is_length(3)
    assertpy.assert_that(versions[0]).is_equal_to(get_sample_version())


@mock.patch("app.shared.api.aws_api.AWSAPI")
def test_get_available_product_versions_rais_exception_if_error(mock_api, mock_logger, get_sample_version):
    # ARRANGE

    publishing_api_qry_srv = publishing_api_query_service.PublishingApiQueryService(api=mock_api, logger=mock_logger)
    mock_api.call_api.side_effect = Exception()

    # ACT && ASSERT

    with pytest.raises(adapter_exception.AdapterException) as e:
        versions = publishing_api_qry_srv.get_available_product_versions(product_id="prod-1")

        mock_api.call_api.assert_called_once_with(
            path="internal/available-products/prod-1/versions",
            http_method="GET",
        )
        assertpy.assert_that(versions).is_none()
        assertpy.assert_that(str(e)).is_equal_to("Unable to fetch product versions for product prod-1")


@mock.patch("app.shared.api.aws_api.AWSAPI")
def test_get_version_returns_version(mock_api, mock_logger, get_sample_version):
    # ARRANGE

    publishing_api_qry_srv = publishing_api_query_service.PublishingApiQueryService(api=mock_api, logger=mock_logger)
    mock_api.call_api.return_value = {"version": get_sample_version().dict()}

    # ACT
    version = publishing_api_qry_srv.get_version(product_id="prod-1", version_id="vers-1", account_id="001234567890")

    # ASSERT
    mock_api.call_api.assert_called_once_with(
        path="internal/products/prod-1/versions/vers-1",
        http_method="GET",
        query_params={
            "awsAccountId": "001234567890",
        },
    )
    assertpy.assert_that(version).is_not_none()
    assertpy.assert_that(version).is_equal_to(get_sample_version())


@mock.patch("app.shared.api.aws_api.AWSAPI")
@pytest.mark.parametrize(
    "error,error_message",
    (
        (HTTPError(), "Unable to fetch version: vers-1 for product: prod-1"),
        (
            ValidationError(
                errors=["Error message"],
                model=version.GetProductVersionInternalResponse,
            ),
            "Unable to parse version: vers-1 for product: prod-1",
        ),
    ),
)
def test_get_version_rais_exception_if_response_error(mock_api, error, error_message, mock_logger, get_sample_version):
    # ARRANGE

    publishing_api_qry_srv = publishing_api_query_service.PublishingApiQueryService(api=mock_api, logger=mock_logger)
    mock_api.call_api.side_effect = error

    # ACT && ASSERT

    with pytest.raises(adapter_exception.AdapterException) as e:
        version = publishing_api_qry_srv.get_version(
            product_id="prod-1", version_id="vers-1", account_id="001234567890"
        )

        mock_api.call_api.assert_called_once_with(
            path="internal/products/prod-1/versions/vers-1",
            http_method="GET",
            query_params={
                "awsAccountId": "001234567890",
            },
        )
        assertpy.assert_that(version).is_none()
        assertpy.assert_that(str(e)).is_equal_to(error_message)
