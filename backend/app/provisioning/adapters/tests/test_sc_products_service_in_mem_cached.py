from unittest import mock

import assertpy
import boto3

from app.provisioning.adapters.services import sc_products_service_in_mem_cached
from app.provisioning.domain.ports import products_service


class DictCtxProvider:

    context: dict

    def __init__(self):
        self.context = {}

    def append_context(self, **additional_context):
        self.context.update(**additional_context)


def mocked_search_provisioned_products_response(
    id: str = "pp-123",
    next_page_token: str | None = None,
    count: int = 5,
):
    return {
        "ProvisionedProducts": [
            {
                "Id": f"{id}-{c}",
                "Status": "AVAILABLE",
                "Tags": [
                    {"Key": "key-string", "Value": "value-string"},
                ],
                "ProvisioningArtifactId": "pa-123",
            }
            for c in range(count)
        ],
        "TotalResultsCount": 123,
        "NextPageToken": next_page_token,
    }


def test_get_provisioned_product_details_should_cache_all_provisioned_products_in_account_region(
    mock_moto_calls,
    mock_search_provisioned_products,
):
    # ARRANGE
    mock_search_provisioned_products.side_effect = [
        mocked_search_provisioned_products_response(id="pp-123", next_page_token="page-1"),
        mocked_search_provisioned_products_response(id="pp-321", next_page_token=None),
    ]
    products_service_mock = mock.create_autospec(spec=products_service.ProductsService)

    sc_client_provider = mock.MagicMock(return_value=boto3.client("servicecatalog", region_name="us-east-1"))

    ctx = DictCtxProvider()

    cached_products_service = sc_products_service_in_mem_cached.ServiceCatalogProductsServiceCachedInMemory(
        inner=products_service_mock,
        sc_boto_client_provider=sc_client_provider,
        request_context_manager=ctx,
    )

    # ACT
    pp_1 = cached_products_service.get_provisioned_product_details(
        "pp-123-0", user_id="test", aws_account_id="001234567890", region="us-east-1"
    )
    pp_2 = cached_products_service.get_provisioned_product_details(
        "pp-321-0", user_id="test", aws_account_id="001234567890", region="us-east-1"
    )
    pp_3 = cached_products_service.get_provisioned_product_details(
        "pp-123-1", user_id="test", aws_account_id="001234567890", region="us-east-1"
    )
    pp_4 = cached_products_service.get_provisioned_product_details(
        "pp-321-1", user_id="test", aws_account_id="001234567890", region="us-east-1"
    )

    # ASSERT
    assertpy.assert_that(pp_1).is_not_none()
    assertpy.assert_that(pp_1.id).is_equal_to("pp-123-0")
    assertpy.assert_that(pp_2).is_not_none()
    assertpy.assert_that(pp_2.id).is_equal_to("pp-321-0")
    assertpy.assert_that(pp_3).is_not_none()
    assertpy.assert_that(pp_3.id).is_equal_to("pp-123-1")
    assertpy.assert_that(pp_4).is_not_none()
    assertpy.assert_that(pp_4.id).is_equal_to("pp-321-1")
    assertpy.assert_that(mock_search_provisioned_products.call_count).is_equal_to(2)
    sc_client_provider.assert_called_once_with("001234567890", "us-east-1", "test")
    assertpy.assert_that(sc_client_provider.call_count).is_equal_to(1)


def test_get_provisioned_product_details_should_extend_cache_when_another_account_region_requested(
    mock_moto_calls,
    mock_search_provisioned_products,
):
    # ARRANGE
    mock_search_provisioned_products.side_effect = [
        mocked_search_provisioned_products_response(id="pp-123", next_page_token=None),
        mocked_search_provisioned_products_response(id="pp-321", next_page_token=None),
    ]
    products_service_mock = mock.create_autospec(spec=products_service.ProductsService)

    sc_client_provider = mock.MagicMock(return_value=boto3.client("servicecatalog", region_name="us-east-1"))
    ctx = DictCtxProvider()

    cached_products_service = sc_products_service_in_mem_cached.ServiceCatalogProductsServiceCachedInMemory(
        inner=products_service_mock,
        sc_boto_client_provider=sc_client_provider,
        request_context_manager=ctx,
    )

    # ACT
    pp_1 = cached_products_service.get_provisioned_product_details(
        "pp-123-0", user_id="test", aws_account_id="001234567890", region="us-east-1"
    )
    pp_2 = cached_products_service.get_provisioned_product_details(
        "pp-321-0", user_id="test", aws_account_id="012345678900", region="us-east-1"
    )
    pp_3 = cached_products_service.get_provisioned_product_details(
        "pp-123-1", user_id="test", aws_account_id="001234567890", region="us-east-1"
    )
    pp_4 = cached_products_service.get_provisioned_product_details(
        "pp-321-1", user_id="test", aws_account_id="012345678900", region="us-east-1"
    )

    # ASSERT
    assertpy.assert_that(pp_1).is_not_none()
    assertpy.assert_that(pp_1.id).is_equal_to("pp-123-0")
    assertpy.assert_that(pp_2).is_not_none()
    assertpy.assert_that(pp_2.id).is_equal_to("pp-321-0")
    assertpy.assert_that(pp_3).is_not_none()
    assertpy.assert_that(pp_3.id).is_equal_to("pp-123-1")
    assertpy.assert_that(pp_4).is_not_none()
    assertpy.assert_that(pp_4.id).is_equal_to("pp-321-1")
    assertpy.assert_that(mock_search_provisioned_products.call_count).is_equal_to(2)
    sc_client_provider.assert_any_call("001234567890", "us-east-1", "test")
    sc_client_provider.assert_any_call("012345678900", "us-east-1", "test")
    assertpy.assert_that(sc_client_provider.call_count).is_equal_to(2)
