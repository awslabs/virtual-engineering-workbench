// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { describe, it, expect } from 'vitest';
import {
  buildMarketplaceImportSearch,
  findHandoffSubscription,
  parseMarketplaceImportHandoff,
} from './marketplace-import-handoff';

const MAX_ID_SUFFIX_LENGTH = 64;
const OVERLONG_ID_SUFFIX_LENGTH = 65;

describe('buildMarketplaceImportSearch', () => {
  it('carries the product id and nothing else', () => {
    const search = buildMarketplaceImportSearch({ productId: 'prod-abc123' });
    const params = new URLSearchParams(search);
    expect(params.get('source')).toBe('marketplace');
    expect(params.get('productId')).toBe('prod-abc123');
    expect([...params.keys()]).toEqual(['source', 'productId']);
  });

  it('does not put the product name in the URL', () => {
    const product = { productId: 'prod-abc123', productName: 'Ubuntu Noble' };
    expect(buildMarketplaceImportSearch(product)).not.toContain('Ubuntu');
  });

  it.each([
    [null],
    [{ productId: '' }],
    [{ productId: null }],
    [{ productId: 'PROD-ABC' }],
    [{ productId: 'prod-' }],
  ])('falls back to the bare source for a missing or malformed id %#', (product) => {
    expect(buildMarketplaceImportSearch(product)).toBe('?source=marketplace');
  });
});

describe('parseMarketplaceImportHandoff', () => {
  it('round-trips what buildMarketplaceImportSearch produced', () => {
    const search = buildMarketplaceImportSearch({ productId: 'prod-abc123' });
    expect(parseMarketplaceImportHandoff(new URLSearchParams(search))).toEqual({
      productId: 'prod-abc123',
    });
  });

  it.each([
    ['prod-ABC123def'],
    [`prod-${'a'.repeat(MAX_ID_SUFFIX_LENGTH)}`],
  ])('accepts %s', (productId) => {
    const search = `source=marketplace&productId=${productId}`;
    expect(parseMarketplaceImportHandoff(new URLSearchParams(search))).toEqual({ productId });
  });

  it.each([
    ['source=other&productId=prod-abc123'],
    ['source=marketplace'],
    ['source=marketplace&productId=PROD-abc'],
    ['source=marketplace&productId=prod-abc%2F..'],
    ['source=marketplace&productId=prod-abc_123'],
    [`source=marketplace&productId=prod-${'a'.repeat(OVERLONG_ID_SUFFIX_LENGTH)}`],
  ])('rejects %s', (search) => {
    expect(parseMarketplaceImportHandoff(new URLSearchParams(search))).toBeNull();
  });
});

describe('findHandoffSubscription', () => {
  const handoff = { productId: 'prod-abc123' };

  it('matches on the product id', () => {
    const match = findHandoffSubscription(
      [
        { productId: 'prod-other', productCode: 'c0' },
        { productId: 'prod-abc123', productCode: 'c1' },
      ],
      handoff,
    );
    expect(match?.productCode).toBe('c1');
  });

  it('ignores a same-named subscription for another product', () => {
    expect(findHandoffSubscription(
      [{ productId: 'prod-other', productName: 'Ubuntu Noble' }],
      handoff,
    )).toBeNull();
  });

  it('never matches a subscription without a product id', () => {
    expect(findHandoffSubscription([{ productName: 'Ubuntu Noble' }], handoff)).toBeNull();
  });

  it('refuses to guess between two subscriptions with the same id', () => {
    expect(findHandoffSubscription(
      [{ productId: 'prod-abc123' }, { productId: 'prod-abc123' }],
      handoff,
    )).toBeNull();
  });
});
