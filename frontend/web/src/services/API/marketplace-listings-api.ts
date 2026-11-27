// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Marketplace listings (public-catalog browse) client.
//
// Wraps the search, detail and facets operations of the generated packaging
// client. The response types are the generated models, re-exported under the
// names the browse pages use.
import {
  GetMarketplaceFacetsResponse,
  GetMarketplaceListingResponse,
  MarketplaceFacetValueItem,
  MarketplaceListingAssociatedEntityItem,
  MarketplaceListingBadgeItem,
  MarketplaceListingCategoryItem,
  MarketplaceListingFulfillmentOptionSummaryItem,
  MarketplaceListingPricingModelItem,
  MarketplaceListingPublisherItem,
  MarketplaceListingResourceItem,
  MarketplaceListingReviewSourceItem,
  MarketplaceListingSummaryItem,
  SearchMarketplaceListingsResponse,
} from './proserve-wb-packaging-api';
import { callApi } from './marketplace-api-support';

export type {
  GetMarketplaceFacetsResponse,
  GetMarketplaceListingResponse,
  SearchMarketplaceListingsResponse,
};
export type MarketplaceListingPublisher = MarketplaceListingPublisherItem;
export type MarketplaceListingCategory = MarketplaceListingCategoryItem;
export type MarketplaceListingBadge = MarketplaceListingBadgeItem;
export type MarketplaceListingPricingModel = MarketplaceListingPricingModelItem;
export type MarketplaceListingFulfillmentOptionSummary = MarketplaceListingFulfillmentOptionSummaryItem;
export type MarketplaceListingReviewSource = MarketplaceListingReviewSourceItem;
export type MarketplaceListingResource = MarketplaceListingResourceItem;
export type MarketplaceListingAssociatedEntity = MarketplaceListingAssociatedEntityItem;
export type MarketplaceListingSummary = MarketplaceListingSummaryItem;
export type MarketplaceFacetValue = MarketplaceFacetValueItem;

/**
 * The values of one facet. The API types `facets` as a bare object (a map of
 * facet name to values), so the lookup narrows it here once.
 */
export const facetValuesOf = (
  response: GetMarketplaceFacetsResponse,
  facetKey: string,
): MarketplaceFacetValue[] =>
  ((response.facets ?? {}) as Record<string, MarketplaceFacetValue[] | undefined>)[facetKey] ?? [];

export interface SearchListingsParams {
  searchText?: string,
  category?: string[],
  pricingModel?: string[],
  publisher?: string[],
  rating?: string[],
  nextToken?: string,
  maxResults?: number,
}

/**
 * A filter with no values is "not set". The generated client serialises an
 * empty array as `category=`, which the backend would read as a blank value.
 */
const nonEmpty = (values?: string[]): string[] | undefined => {
  const present = (values ?? []).filter((v) => v.trim() !== '');
  return present.length ? present : undefined;
};

class ListingsApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = 'ListingsApiError';
    this.status = status;
    this.code = code;
  }
}

const makeError = (message: string, status: number, code?: string) =>
  new ListingsApiError(message, status, code);

export const marketplaceListingsAPI = {
  searchListings: (
    projectId: string,
    params: SearchListingsParams = {},
  ): Promise<SearchMarketplaceListingsResponse> =>
    callApi(
      (api, authorization) => api.searchMarketplaceListings({
        authorization,
        projectId,
        // An empty search text or page size is "not set", not a filter value.
        searchText: params.searchText || undefined,
        category: nonEmpty(params.category),
        pricingModel: nonEmpty(params.pricingModel),
        publisher: nonEmpty(params.publisher),
        rating: nonEmpty(params.rating),
        nextToken: params.nextToken || undefined,
        maxResults: params.maxResults || undefined,
      }),
      makeError,
    ),

  getListing: (projectId: string, listingId: string): Promise<GetMarketplaceListingResponse> =>
    callApi(
      (api, authorization) => api.getMarketplaceListing({ authorization, projectId, listingId }),
      makeError,
    ),

  getFacets: (projectId: string): Promise<GetMarketplaceFacetsResponse> =>
    callApi(
      (api, authorization) => api.getMarketplaceFacets({ authorization, projectId }),
      makeError,
    ),
};

export type MarketplaceListingsAPI = typeof marketplaceListingsAPI;

export { ListingsApiError };
