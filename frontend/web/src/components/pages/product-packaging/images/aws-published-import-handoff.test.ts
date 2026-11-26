// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// The listing id arrives in the URL and is therefore untrusted. These tests
// pin the validation down as strictly as the Marketplace product-id hand-off.

import { describe, it, expect } from 'vitest';
import {
  AWS_PUBLISHED_SOURCE_VALUE,
  buildAwsPublishedImportSearch,
  isValidMarketplaceListingId,
  parseAwsPublishedImportHandoff,
} from './aws-published-import-handoff';

const params = (search: string) => new URLSearchParams(search);

describe('isValidMarketplaceListingId', () => {
  it('accepts a well-formed listing id', () => {
    expect(isValidMarketplaceListingId('prodview-abc123DEF456')).toBe(true);
  });

  it('rejects anything that is not a prodview- id', () => {
    // A product id is not a listing id: the resolve endpoint takes a LISTING,
    // and the backend reads the product back from it.
    expect(isValidMarketplaceListingId('prod-abc123')).toBe(false);
    expect(isValidMarketplaceListingId('prodview-')).toBe(false);
    expect(isValidMarketplaceListingId('')).toBe(false);
    expect(isValidMarketplaceListingId(null)).toBe(false);
    expect(isValidMarketplaceListingId(undefined)).toBe(false);
  });

  it('rejects ids carrying separators or markup', () => {
    expect(isValidMarketplaceListingId('prodview-abc/../x')).toBe(false);
    expect(isValidMarketplaceListingId('prodview-abc?x=1')).toBe(false);
    expect(isValidMarketplaceListingId('prodview-<script>')).toBe(false);
    expect(isValidMarketplaceListingId('prodview-abc def')).toBe(false);
  });

  it('is anchored, so a valid id embedded in junk is still rejected', () => {
    expect(isValidMarketplaceListingId('xprodview-abc')).toBe(false);
    expect(isValidMarketplaceListingId('prodview-abc\nprodview-def')).toBe(false);
  });
});

describe('buildAwsPublishedImportSearch', () => {
  it('builds a search carrying the source and the listing id', () => {
    const search = buildAwsPublishedImportSearch({ listingId: 'prodview-abc123' });
    expect(search).toBe(`?source=${AWS_PUBLISHED_SOURCE_VALUE}&listingId=prodview-abc123`);
  });

  it('returns null when there is no usable listing id', () => {
    // Without a listing there is nothing to resolve, so the caller must not
    // offer the action at all.
    expect(buildAwsPublishedImportSearch({ listingId: null })).toBeNull();
    expect(buildAwsPublishedImportSearch({ listingId: 'not-a-listing' })).toBeNull();
    expect(buildAwsPublishedImportSearch(null)).toBeNull();
    expect(buildAwsPublishedImportSearch(undefined)).toBeNull();
  });
});

describe('parseAwsPublishedImportHandoff', () => {
  it('reads the listing id when the source matches', () => {
    expect(parseAwsPublishedImportHandoff(
      params(`?source=${AWS_PUBLISHED_SOURCE_VALUE}&listingId=prodview-abc123`),
    )).toEqual({ listingId: 'prodview-abc123' });
  });

  it('returns null unless the source names this entry point', () => {
    // The post-purchase Marketplace hand-off shares the `source` param; only
    // its value distinguishes them, so a marketplace link must not be read
    // as an AWS-published one.
    expect(parseAwsPublishedImportHandoff(
      params('?source=marketplace&listingId=prodview-abc123'),
    )).toBeNull();
    expect(parseAwsPublishedImportHandoff(
      params('?listingId=prodview-abc123'),
    )).toBeNull();
  });

  it('returns null, not a partial object, for a malformed listing id', () => {
    expect(parseAwsPublishedImportHandoff(
      params(`?source=${AWS_PUBLISHED_SOURCE_VALUE}&listingId=prod-abc123`),
    )).toBeNull();
    expect(parseAwsPublishedImportHandoff(
      params(`?source=${AWS_PUBLISHED_SOURCE_VALUE}`),
    )).toBeNull();
  });

  it('round-trips what buildAwsPublishedImportSearch produced', () => {
    const search = buildAwsPublishedImportSearch({ listingId: 'prodview-abc123' });
    expect(parseAwsPublishedImportHandoff(params(search as string)))
      .toEqual({ listingId: 'prodview-abc123' });
  });
});
