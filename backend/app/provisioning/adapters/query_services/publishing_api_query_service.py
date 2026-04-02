from aws_lambda_powertools import logging
from pydantic import ValidationError
from requests import HTTPError

from app.provisioning.adapters.exceptions import adapter_exception
from app.provisioning.domain.ports import publishing_query_service
from app.provisioning.domain.read_models import version
from app.shared.api import aws_api


class PublishingApiQueryService(publishing_query_service.PublishingQueryService):
    def __init__(
        self,
        api: aws_api.AWSAPI,
        logger: logging.Logger,
    ):
        self._aws_api = api
        self._logger = logger

    def get_available_product_versions(
        self,
        product_id: str,
    ) -> list[version.Version]:
        try:
            # Call publishing bounded context's internal API gateway to get available product versions
            resp = self._aws_api.call_api(path=f"internal/available-products/{product_id}/versions", http_method="GET")

            parsed_resp = version.GetAvailableProductVersionsInternalResponse.model_validate(resp)
        except Exception as e:
            raise adapter_exception.AdapterException(
                f"Unable to fetch product versions for product {product_id}"
            ) from e

        return parsed_resp.availableProductVersions

    def get_version(
        self,
        product_id: str,
        version_id: str,
        account_id: str,
    ) -> version.Version | None:
        try:
            # Call publishing bounded context's internal API gateway to get product version
            resp = self._aws_api.call_api(
                path=f"internal/products/{product_id}/versions/{version_id}",
                http_method="GET",
                query_params={
                    "awsAccountId": account_id,
                },
            )

            parsed_resp = version.GetProductVersionInternalResponse.model_validate(resp)
            return parsed_resp.version
        except HTTPError as e:
            raise adapter_exception.AdapterException(
                f"Unable to fetch version: {version_id} for product: {product_id}"
            ) from e
        except ValidationError as e:
            raise adapter_exception.AdapterException(
                f"Unable to parse version: {version_id} for product: {product_id}"
            ) from e
