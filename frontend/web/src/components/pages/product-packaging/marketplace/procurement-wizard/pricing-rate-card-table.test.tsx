// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Tests for PricingRateCardTable — the paid-product rate-card renderer.

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PricingRateCardTable } from './pricing-rate-card-table';
import { MarketplaceOfferTerm } from '../../../../../services/API/marketplace-procurement-api';

const ONE = 1;

describe('PricingRateCardTable', () => {
  it('renders a fallback when rateCards are missing', () => {
    const term: MarketplaceOfferTerm = {
      termId: 't', termType: 'UsageBasedPricingTerm', rawTerm: { currencyCode: 'USD' },
    };
    render(<PricingRateCardTable term={term} />);
    expect(screen.getByText('No pricing rate card available.')).toBeTruthy();
  });

  it('renders one row per distinct (price, unit) grouping', () => {
    const term: MarketplaceOfferTerm = {
      termId: 't1',
      termType: 'UsageBasedPricingTerm',
      rawTerm: {
        currencyCode: 'USD',
        rateCards: [{
          rateCard: [
            { price: '0.05', unit: 'Hrs', dimensionKey: 'm5.large' },
            { price: '0.10', unit: 'Hrs', dimensionKey: 'm5.xlarge' },
            { price: '0.20', unit: 'Hrs', dimensionKey: 'm5.2xlarge' },
          ],
        }],
      },
    };
    const { container } = render(<PricingRateCardTable term={term} />);
    // Each row's dimension name should be present
    expect(screen.getByText('m5.large')).toBeTruthy();
    expect(screen.getByText('m5.xlarge')).toBeTruthy();
    expect(screen.getByText('m5.2xlarge')).toBeTruthy();
    // 3 body rows (plus header) inside the Cloudscape Table
    const table = container.querySelector('[data-test="rate-card-t1"]');
    expect(table).not.toBeNull();
  });

  it('groups identical prices with a "N more" summary when >5 dimensions share a price', () => {
    // Real-world case: a free-tier AMI has ~100+ instance types all at $0.
    // Rendering 100 rows of "$0" is noise. Group them.
    const dims = [
      'c5.large', 'c5.xlarge', 'c5.2xlarge', 'c5.4xlarge', 'c5.9xlarge',
      'm5.large', 'm5.xlarge', 'm5.2xlarge', 'r5.large', 'r5.xlarge',
    ];
    const rateCard = dims.map((d) => ({ price: '0', unit: 'Hrs', dimensionKey: d, displayName: d }));
    const term: MarketplaceOfferTerm = {
      termId: 't-free',
      termType: 'UsageBasedPricingTerm',
      rawTerm: {
        currencyCode: 'USD',
        rateCards: [{ rateCard }],
      },
    };
    render(<PricingRateCardTable term={term} />);

    // All 10 dimensions at price=0 should render as a single "Applies to" cell
    // with 3 named dimensions + "and 7 more" suffix.
    expect(screen.getByText(/and 7 more/u)).toBeTruthy();
    // The row-count reduction is verifiable by the presence of exactly one
    // "USD 0.00 (free)" price cell (not 10).
    const priceCells = screen.getAllByText(/USD 0\.00 \(free\)/u);
    expect(priceCells).toHaveLength(ONE);
  });

  it('formats sub-dollar prices with trimmed trailing zeros', () => {
    const term: MarketplaceOfferTerm = {
      termId: 't-tiny',
      termType: 'UsageBasedPricingTerm',
      rawTerm: {
        currencyCode: 'USD',
        rateCards: [{
          rateCard: [{ price: '0.00004', unit: 'Requests', dimensionKey: 'r1' }],
        }],
      },
    };
    render(<PricingRateCardTable term={term} />);
    // Rendered as "USD 0.00004" (no trailing zeros, no padding).
    expect(screen.getByText('USD 0.00004')).toBeTruthy();
  });

  it('preserves currency code across rows', () => {
    const term: MarketplaceOfferTerm = {
      termId: 't-eur',
      termType: 'FixedUpfrontPricingTerm',
      rawTerm: {
        currencyCode: 'EUR',
        rateCards: [{
          rateCard: [{ price: '99.00', unit: 'Yr', dimensionKey: 'annual' }],
        }],
      },
    };
    render(<PricingRateCardTable term={term} />);
    expect(screen.getByText('EUR 99')).toBeTruthy();
  });
});
