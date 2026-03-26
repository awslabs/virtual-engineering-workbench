import typing

from mypy_boto3_servicecatalog import client

from app.provisioning.domain.model import provisioned_product_details, provisioned_product_output
from app.provisioning.domain.ports import products_service
from app.provisioning.domain.read_models import version
from app.shared.adapters.auth import temporary_credential_provider

MAX_SC_SEARCH_PROVISIONED_PRODUCTS_PAGE_SIZE = 100


class ServiceCatalogProductsServiceCachedInMemory(products_service.ProductsService):
    def __init__(
        self,
        inner: products_service.ProductsService,
        sc_boto_client_provider: typing.Callable[[str, str, str], client.ServiceCatalogClient],
        request_context_manager: temporary_credential_provider.SupportsContextManager,
        page_size: int = MAX_SC_SEARCH_PROVISIONED_PRODUCTS_PAGE_SIZE,
    ):
        self._inner = inner
        self._sc_boto_client_provider = sc_boto_client_provider
        self._request_context_manager = request_context_manager
        self._page_size = page_size

    def get_provisioned_product_supported_instance_type_param(self, **kwargs) -> version.VersionParameter | None:
        return self._inner.get_provisioned_product_supported_instance_type_param(**kwargs)

    def provision_product(self, **kwargs) -> str:
        return self._inner.provision_product(**kwargs)

    def deprovision_product(self, **kwargs) -> None:
        return self._inner.deprovision_product(**kwargs)

    def update_product(self, **kwargs) -> str:
        return self._inner.update_product(**kwargs)

    def get_provisioned_product_outputs(self, **kwargs) -> list[provisioned_product_output.ProvisionedProductOutput]:
        return self._inner.get_provisioned_product_outputs(**kwargs)

    def has_provisioned_product_insufficient_capacity_error(self, **kwargs) -> bool:
        return self._inner.has_provisioned_product_insufficient_capacity_error(**kwargs)

    def has_provisioned_product_missing_removal_signal_error(self, **kwargs) -> bool:
        return self._inner.has_provisioned_product_missing_removal_signal_error(**kwargs)

    def get_provisioned_product_details(
        self,
        provisioned_product_id: str,
        user_id: str,
        aws_account_id: str,
        region: str,
    ) -> provisioned_product_details.ProvisionedProductDetails | None:

        cache_key = self.__get_cache_key(aws_account_id=aws_account_id, region=region)

        if "cached_provisioned_products" not in self._request_context_manager.context:
            self._request_context_manager.append_context(cached_provisioned_products={})

        if cache_key not in self._request_context_manager.context.get("cached_provisioned_products"):
            sc_client = self._sc_boto_client_provider(aws_account_id, region, user_id)

            page_token = "0"
            provisioned_products = {}
            while page_token:
                result = sc_client.search_provisioned_products(
                    AccessLevelFilter={"Key": "Account", "Value": "self"},
                    SortBy="lastRecordId",
                    PageToken=page_token,
                    PageSize=self._page_size,
                )

                for item in result.get("ProvisionedProducts", []):
                    pp = provisioned_product_details.ProvisionedProductDetails.parse_obj(item)
                    provisioned_products[pp.id] = pp

                page_token = result.get("NextPageToken", None)

            self._request_context_manager.context.get("cached_provisioned_products")[cache_key] = provisioned_products

        return (
            self._request_context_manager.context.get("cached_provisioned_products")
            .get(cache_key)
            .get(provisioned_product_id, None)
        )

    def __get_cache_key(self, aws_account_id: str, region: str) -> str:
        return f"{aws_account_id}#{region}"
