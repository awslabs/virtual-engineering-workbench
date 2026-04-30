import logging
from unittest import mock
from urllib import parse

import assertpy
import pytest
import responses

from app.shared.api import aws_api


@pytest.fixture
def mock_logger():
    return mock.create_autospec(spec=logging.Logger)


@pytest.fixture
def mock_requests():
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def api(mock_logger):
    return aws_api.AWSAPI(
        api_url=parse.urlparse("https://api.example.com/v1"), region="eu-central-1", logger=mock_logger
    )


def test_awsapi_inherits_awsapibase():
    # ASSERT
    assertpy.assert_that(issubclass(aws_api.AWSAPI, aws_api.AWSAPIBase)).is_true()


def test_call_api_returns_json_on_success(api, mock_requests):
    # ARRANGE
    mock_requests.get("https://api.example.com/v1/items", json={"items": [1, 2]}, status=200)

    # ACT
    result = api.call_api(path="/items", http_method="GET")

    # ASSERT
    assertpy.assert_that(result).is_equal_to({"items": [1, 2]})
    assertpy.assert_that(mock_requests.calls).is_length(1)


def test_call_api_returns_none_on_204(api, mock_requests):
    # ARRANGE
    mock_requests.delete("https://api.example.com/v1/items/1", status=204)

    # ACT
    result = api.call_api(path="/items/1", http_method="DELETE")

    # ASSERT
    assertpy.assert_that(result).is_none()


def test_call_api_retries_on_server_error(api, mock_requests):
    # ARRANGE
    mock_requests.get("https://api.example.com/v1/items", status=502)

    # ACT / ASSERT
    with pytest.raises(aws_api.RetryableServiceException):
        api.call_api(path="/items", http_method="GET")


def test_call_api_raises_on_client_error(api, mock_requests):
    # ARRANGE
    mock_requests.get("https://api.example.com/v1/items", status=404)

    # ACT / ASSERT
    with pytest.raises(Exception):
        api.call_api(path="/items", http_method="GET")


def test_call_api_sends_body_as_json(api, mock_requests):
    # ARRANGE
    mock_requests.post("https://api.example.com/v1/items", json={"id": "1"}, status=200)

    # ACT
    api.call_api(path="/items", http_method="POST", body={"name": "test"})

    # ASSERT
    assertpy.assert_that(mock_requests.calls[0].request.body).is_equal_to(b'{"name": "test"}')


def test_region_property(api):
    # ASSERT
    assertpy.assert_that(api.region).is_equal_to("eu-central-1")


def test_api_url_property(api):
    # ASSERT
    assertpy.assert_that(api.api_url.geturl()).is_equal_to("https://api.example.com/v1")
