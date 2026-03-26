import http

import jwt
import requests
from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit

from app.authorization.domain.ports import authentication_service


class CognitoService(authentication_service.AuthenticationService):
    def __init__(self, cognito_user_info_uri: str, jwk_client: jwt.PyJWKClient, logger: Logger, metrics: Metrics):
        self._cognito_user_info_uri = cognito_user_info_uri
        self._jwk_client = jwk_client
        self._logger = logger
        self._metrics = metrics

    def get_signing_key_from_jwt(self, auth_token_jwt: str) -> tuple[bool, jwt.api_jwk.PyJWK | None]:
        self._logger.debug("Getting signing key from JWT token.")

        try:
            signing_key = self._jwk_client.get_signing_key_from_jwt(auth_token_jwt)
            return True, signing_key

        except jwt.exceptions.PyJWKClientError:
            self._logger.exception("Failed to get signing key from JWT")
            self._metrics.add_metric(name="SigningKeyError", unit=MetricUnit.Count, value=1)
            return False, None
        except Exception:
            self._logger.exception("Unexpected error while getting signing key")
            self._metrics.add_metric(name="UnexpectedSigningKeyError", unit=MetricUnit.Count, value=1)
            return False, None

    def get_user_info(self, auth_token: str) -> dict:
        try:
            self._logger.debug("Calling Cognito UserInfo API")
            response = requests.get(url=self._cognito_user_info_uri, headers={"Authorization": auth_token}, timeout=3)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as http_err:
            if http_err.response.status_code == http.HTTPStatus.UNAUTHORIZED:
                self._logger.exception(
                    f"Cognito response code: {http_err.response.status_code} | Access token is expired, disabled, or deleted, or the user has globally signed out."
                )
                self._metrics.add_metric(name="CognitoInvalidToken", unit=MetricUnit.Count, value=1)
            elif http_err.response.status_code == http.HTTPStatus.BAD_REQUEST:
                self._logger.exception(
                    f"Cognito response code: {http_err.response.status_code} | The request is missing a required parameter, includes an unsupported parameter value, or is otherwise malformed."
                )
                self._metrics.add_metric(name="CognitoBadRequestMissingParams", unit=MetricUnit.Count, value=1)
        except requests.exceptions.Timeout:
            self._logger.error("Cognito UserInfo Timed out")
            self._metrics.add_metric(name="CognitoTimeOut", unit=MetricUnit.Count, value=1)
        except Exception:
            self._logger.exception("Unexpected error exception")
            self._metrics.add_metric(name="UnexpectedUserProfileError", unit=MetricUnit.Count, value=1)

        return {}

    def _get_jwks_cache(self) -> dict | None:
        if (
            not self._jwk_client.jwk_set_cache
            or not self._jwk_client.jwk_set_cache.jwk_set_with_timestamp
            or not self._jwk_client.jwk_set_cache.jwk_set_with_timestamp.jwk_set
        ):
            return None

        return self._jwk_client.jwk_set_cache.jwk_set_with_timestamp.jwk_set
