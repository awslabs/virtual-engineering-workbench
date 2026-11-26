// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// PricingRateCardTable — renders the ``rateCards`` structure of a
// ``UsageBasedPricingTerm`` / ``FixedUpfrontPricingTerm`` /
// ``RecurringPaymentTerm`` / ``ConfigurableUpfrontPricingTerm`` as a
// real Cloudscape Table (dimension | unit | price).
//
// This is the "user-facing rate card" view. It complements the
// one-liner summary produced by ``summarizePricingTerm``: the summary
// answers "is this free? in what currency?"; the table answers
// "what would I actually pay per hour for m5.large?".
//
// If the term has no rate cards or a malformed shape, the component
// renders a "no pricing data" fallback instead of crashing.

import { FC, useMemo } from 'react';
import {
  Box,
  Table,
} from '@cloudscape-design/components';
import { MarketplaceOfferTerm } from '../../../../../services/API/marketplace-procurement-api';

interface PricingRateCardTableProps {
  term: MarketplaceOfferTerm,
}

interface RateRow {
  key: string,
  dimensionKey: string,
  dimensionLabel: string,
  unit: string,
  price: string,
  currency: string,
}

const ZERO_PRICE = 0;
const SUB_UNIT_THRESHOLD = 1;
/** Sub-dollar rates (e.g. $0.000004/request) need more than 2 decimals. */
const SMALL_PRICE_DECIMALS = 4;
const NO_ROWS = 0;
const SINGLE_DIMENSION = 1;
const FIRST_ITEM_INDEX = 0;
/** Above this many dimensions the list is truncated with "and N more". */
const MAX_DIMENSIONS_INLINE = 5;
const TRUNCATED_DIMENSIONS_SHOWN = 3;
const COL_WIDTH_PRICE = 160;
const COL_WIDTH_UNIT = 80;

const formatPrice = (price: string, currency: string): string => {
  const num = Number(price);
  if (!Number.isFinite(num)) { return `${price} ${currency}`; }
  if (num === ZERO_PRICE) { return `${currency} 0.00 (free)`; }
  // Preserve the seller's precision — some prices have 6 decimals
  // (e.g. per-request pricing at $0.000004). Trim trailing zeros beyond
  // the second decimal so common per-hour prices still look sane.
  const displayed = num < SUB_UNIT_THRESHOLD
    ? num.toString().replace(/(?<keep>\.\d*?)0+$/u, '$<keep>').replace(/\.$/u, '.0')
    : num.toFixed(SMALL_PRICE_DECIMALS).replace(/0+$/u, '').replace(/\.$/u, '');
  return `${currency} ${displayed}`;
};

const extractRows = (term: MarketplaceOfferTerm): RateRow[] => {
  const raw = term.rawTerm as Record<string, unknown>;
  const currency = typeof raw.currencyCode === 'string' ? raw.currencyCode : 'USD';
  const rateCards = raw.rateCards as Array<Record<string, unknown>> | undefined;
  if (!Array.isArray(rateCards)) { return []; }

  const rows: RateRow[] = [];
  rateCards.forEach((rc, cardIdx) => {
    const inner = rc?.rateCard as Array<Record<string, unknown>> | undefined;
    if (!Array.isArray(inner)) { return; }
    inner.forEach((r, rowIdx) => {
      const dimensionKey = typeof r.dimensionKey === 'string' ? r.dimensionKey : '';
      const displayName = typeof r.displayName === 'string' ? r.displayName : dimensionKey;
      const unit = typeof r.unit === 'string' ? r.unit : '';
      const price = typeof r.price === 'string'
        ? r.price
        // `r.price` comes off an untyped AWS rawTerm, so it may be a number,
        // null or absent. Both null and undefined mean "no price".
        : r.price !== null && r.price !== undefined ? String(r.price) : '';
      rows.push({
        key: `${cardIdx}-${rowIdx}-${dimensionKey}`,
        dimensionKey,
        dimensionLabel: displayName,
        unit,
        price,
        currency,
      });
    });
  });
  return rows;
};

/**
 * Deduplicate a rate card by "logical price row". AMI pricing often
 * lists 100+ EC2 instance types with the SAME price — showing them all
 * is noise. We group by (price, unit) and roll up the dimension list.
 */
interface GroupedRow {
  key: string,
  dimensions: string[],
  unit: string,
  price: string,
  currency: string,
}

const groupByPrice = (rows: RateRow[]): GroupedRow[] => {
  const groups = new Map<string, GroupedRow>();
  rows.forEach((r) => {
    const gkey = `${r.price}|${r.unit}|${r.currency}`;
    const existing = groups.get(gkey);
    if (existing) {
      existing.dimensions.push(r.dimensionLabel || r.dimensionKey);
    } else {
      groups.set(gkey, {
        key: gkey,
        dimensions: [r.dimensionLabel || r.dimensionKey],
        unit: r.unit,
        price: r.price,
        currency: r.currency,
      });
    }
  });
  return Array.from(groups.values());
};

export const PricingRateCardTable: FC<PricingRateCardTableProps> = ({ term }) => {
  const rows = useMemo(() => extractRows(term), [term]);
  const grouped = useMemo(() => groupByPrice(rows), [rows]);

  if (grouped.length === NO_ROWS) {
    return (
      <Box color="text-body-secondary" variant="small">
        No pricing rate card available.
      </Box>
    );
  }

  return (
    <Table
      variant="embedded"
      data-test={`rate-card-${term.termId}`}
      columnDefinitions={[
        {
          id: 'price',
          header: 'Price',
          cell: (item: GroupedRow) =>
            <strong>{formatPrice(item.price, item.currency)}</strong>,
          width: COL_WIDTH_PRICE,
        },
        {
          id: 'unit',
          header: 'Unit',
          cell: (item: GroupedRow) => item.unit || '—',
          width: COL_WIDTH_UNIT,
        },
        {
          id: 'dimensions',
          header: 'Applies to',
          cell: (item: GroupedRow) => {
            const count = item.dimensions.length;
            if (count === SINGLE_DIMENSION) { return item.dimensions[FIRST_ITEM_INDEX]; }
            if (count <= MAX_DIMENSIONS_INLINE) { return item.dimensions.join(', '); }
            return `${item.dimensions.slice(FIRST_ITEM_INDEX, TRUNCATED_DIMENSIONS_SHOWN).join(', ')}`
    + `, and ${count - TRUNCATED_DIMENSIONS_SHOWN} more`;
          },
        },
      ]}
      items={grouped}
      trackBy="key"
      empty={<Box color="text-body-secondary">No pricing rate card available.</Box>}
    />
  );
};
