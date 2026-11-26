// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Hand-off from a completed Marketplace purchase to the Import Image wizard.
//
// After an agreement is accepted, the procurement wizard links to the import
// wizard with the purchased product's AWS Marketplace product id in the query
// string, so the import wizard can preselect the matching subscription.
//
// The match uses the product id alone: a subscription is preselected only
// when exactly one listed subscription carries that `productId`. Product
// names are not unique across sellers, so they are never used to match.
//
// The product id comes from the URL and is therefore untrusted. It is
// format-checked here and only ever compared against data the backend
// returned; nothing from the URL is rendered or sent to an API.

import { DiscoveredMarketplaceSubscription } from
  '../../../../services/API/proserve-wb-packaging-api';

export const MARKETPLACE_SOURCE_PARAM = 'source';
export const MARKETPLACE_SOURCE_VALUE = 'marketplace';
export const MARKETPLACE_PRODUCT_ID_PARAM = 'productId';

/** AWS Marketplace product ids look like `prod-abc123DEF456`. */
const PRODUCT_ID_PATTERN = /^prod-[A-Za-z0-9]{1,64}$/u;
const SINGLE_MATCH = 1;

export interface MarketplaceImportHandoff {
  productId: string,
}

export const isValidMarketplaceProductId = (value: string | null | undefined): value is string =>
  typeof value === 'string' && PRODUCT_ID_PATTERN.test(value);

/**
 * Query string for the import wizard. Returns only `source=marketplace` when
 * the product id is missing or malformed, so the import wizard still opens on
 * the Marketplace picker.
 */
export const buildMarketplaceImportSearch = (
  product: { productId?: string | null } | null | undefined,
): string => {
  const params = new URLSearchParams({ [MARKETPLACE_SOURCE_PARAM]: MARKETPLACE_SOURCE_VALUE });
  if (isValidMarketplaceProductId(product?.productId)) {
    params.set(MARKETPLACE_PRODUCT_ID_PARAM, product.productId);
  }
  return `?${params.toString()}`;
};

/**
 * Read the hand-off from the import wizard's URL. `null` unless the URL asks
 * for the Marketplace source AND carries a well-formed product id.
 */
export const parseMarketplaceImportHandoff = (
  searchParams: URLSearchParams,
): MarketplaceImportHandoff | null => {
  if (searchParams.get(MARKETPLACE_SOURCE_PARAM) !== MARKETPLACE_SOURCE_VALUE) { return null; }
  const productId = searchParams.get(MARKETPLACE_PRODUCT_ID_PARAM);
  if (!isValidMarketplaceProductId(productId)) { return null; }
  return { productId };
};

/**
 * The subscription the hand-off refers to, or `null` unless exactly one
 * subscription has the hand-off's product id. Subscriptions without a
 * `productId` never match.
 */
export const findHandoffSubscription = (
  subscriptions: readonly DiscoveredMarketplaceSubscription[],
  handoff: MarketplaceImportHandoff,
): DiscoveredMarketplaceSubscription | null => {
  const matches = subscriptions.filter((s) => s.productId === handoff.productId);
  return matches.length === SINGLE_MATCH ? matches[0] : null;
};
