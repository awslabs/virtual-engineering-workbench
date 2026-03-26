import http
from typing import Optional
from urllib import parse

import requests
import retry
from aws_lambda_powertools import logging, tracing
from aws_requests_auth import boto_utils

tracer = tracing.Tracer()


class RetryableServiceException(Exception):
    pass


class AWSAPI:
    """Wrapper class for making API Gateway calls."""

    def __init__(self, api_url: parse.ParseResult, region: str, logger: logging.Logger):
        self._api_url = api_url
        self._region = region
        self._logger = logger

    @tracer.capture_method
    @retry.retry(RetryableServiceException, tries=3, delay=1, backoff=2)
    def call_api(
        self,
        path: str,
        http_method: str,
        user_token: Optional[str] = None,
        body: Optional[dict] = None,
        query_params: Optional[dict] = None,
        service: Optional[str] = "execute-api",
        auth: Optional[requests.auth.AuthBase] = None,
    ) -> dict:
        """Invokes API Gateway API and returns the response."""

        headers = None
        if user_token:
            headers = {"Authorization": user_token}
            auth = None
        elif auth is None:
            auth = boto_utils.BotoAWSRequestsAuth(
                aws_host=self._api_url.hostname,
                aws_region=self._region,
                aws_service=service,
            )

        url = f"{self._api_url.geturl()}{path}"

        self._logger.info(
            f"Sending request to the API. URL: {url}, HTTP Method: {http_method}, Body: {body}. Query Parameters: {query_params}"
        )

        response = requests.request(
            http_method.lower(), url=url, params=query_params, json=body, headers=headers, auth=auth, timeout=30
        )

        # Retry for the following server errors
        if response.status_code in [
            http.HTTPStatus.INTERNAL_SERVER_ERROR,
            http.HTTPStatus.BAD_GATEWAY,
            http.HTTPStatus.SERVICE_UNAVAILABLE,
            http.HTTPStatus.GATEWAY_TIMEOUT,
        ]:
            self._logger.error(f"Error calling external API. HTTP Status: {response.status_code}. Retrying")
            raise RetryableServiceException

        self._logger.info(
            f"Received response from the API. URL: {url}, HTTP Method: {http_method}, HTTP Status: {response.status_code}"
        )

        # Raise an exception unless the service returned 2xx
        response.raise_for_status()

        # Parse the response body
        response_body = None
        if response.status_code != http.HTTPStatus.NO_CONTENT:
            response_body = response.json()
        self._logger.info(f"Received response body: {response_body}")

        return response_body

    @property
    def region(self):
        return self._region

    @property
    def api_url(self):
        return self._api_url
