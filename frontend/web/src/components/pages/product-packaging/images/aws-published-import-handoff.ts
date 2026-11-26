// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Hand-off from an AWS-published Marketplace listing to the Import Image
// wizard.
//
// Products AWS sells itself have no agreement to create, so there is nothing
// to subscribe to and they never appear in the subscriptions list. The
// procurement wizard links straight here with the listing id in the query
// string, and the import wizard resolves that listing to an AMI.
//
// The listing id comes from the URL and is therefore untrusted. It is
// format-checked here and only ever sent to the resolve endpoint as a request
// field; it is never rendered. What the user sees is the product name and AMI
// the backend returned for it.

// The `source` param is shared with the post-purchase Marketplace hand-off;
// only its value distinguishes the two entry points.
import { MARKETPLACE_SOURCE_PARAM } from './marketplace-import-handoff';

export const AWS_PUBLISHED_SOURCE_VALUE = 'aws-published';
export const AWS_PUBLISHED_LISTING_ID_PARAM = 'listingId';

/** AWS Marketplace listing ids look like `prodview-abc123DEF456`. */
const LISTING_ID_PATTERN = /^prodview-[A-Za-z0-9]{1,64}$/u;

export interface AwsPublishedImportHandoff {
  listingId: string,
}

export const isValidMarketplaceListingId = (
  value: string | null | undefined,
): value is string =>
  typeof value === 'string' && LISTING_ID_PATTERN.test(value);

/**
 * Query string for the import wizard. Returns `null` when the listing id is
 * missing or malformed: without a listing there is nothing to resolve, so
 * there is no point opening the wizard on this source at all.
 */
export const buildAwsPublishedImportSearch = (
  listing: { listingId?: string | null } | null | undefined,
): string | null => {
  if (!isValidMarketplaceListingId(listing?.listingId)) { return null; }
  const params = new URLSearchParams({
    [MARKETPLACE_SOURCE_PARAM]: AWS_PUBLISHED_SOURCE_VALUE,
    [AWS_PUBLISHED_LISTING_ID_PARAM]: listing.listingId,
  });
  return `?${params.toString()}`;
};

/**
 * Read the hand-off from the import wizard's URL. `null` unless the URL asks
 * for the AWS-published source AND carries a well-formed listing id.
 */
export const parseAwsPublishedImportHandoff = (
  searchParams: URLSearchParams,
): AwsPublishedImportHandoff | null => {
  if (searchParams.get(MARKETPLACE_SOURCE_PARAM) !== AWS_PUBLISHED_SOURCE_VALUE) {
    return null;
  }
  const listingId = searchParams.get(AWS_PUBLISHED_LISTING_ID_PARAM);
  if (!isValidMarketplaceListingId(listingId)) { return null; }
  return { listingId };
};
