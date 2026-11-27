// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
/* eslint-disable no-script-url -- these tests assert that `javascript:`
   URLs are REJECTED. The literal hostile scheme is the input under test;
   removing it would delete the security assertion. Scoped to this file. */
// Tests for TermSummary rendering. Verifies:
// - LegalTerm renders a "View End-User License Agreement" link with the
//   presigned URL as href (not a JSON dump).
// - SupportTerm renders the refund policy text.
// - Pricing terms render the summarized one-liner + rate card table.
// - Term IDs are hidden by default (only in the collapsed technical
//   reference section).
// - Raw JSON is NOT rendered anywhere.

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { TermSummary } from './term-summary';
import { MarketplaceOfferTerm } from '../../../../../services/API/marketplace-procurement-api';

const NONE = 0;

describe('TermSummary', () => {
  it('renders a LegalTerm with a link to the EULA document', () => {
    const term: MarketplaceOfferTerm = {
      termId: 'term-legal-1',
      termType: 'LegalTerm',
      rawTerm: {
        id: 'term-legal-1',
        type: 'LegalTerm',
        documents: [
          {
            type: 'CustomEula',
            url: 'https://awsmp-legal.s3.us-east-1.amazonaws.com/eula.pdf?X-Amz-Signature=abc',
          },
        ],
      },
    };
    const { container } = render(<TermSummary term={term} />);

    // Friendly heading (not "LegalTerm" or the term-... hash)
    expect(screen.getByText('Legal terms')).toBeTruthy();

    // The EULA link is real and points at the presigned URL
    const link = container.querySelector('a[href*="eula.pdf"]');
    expect(link).not.toBeNull();
    expect(link?.textContent).toContain('View End-User License Agreement');

    // The technical-reference section exists as a collapsible.
    expect(screen.getByText('Technical reference')).toBeTruthy();
  });

  it('does NOT render raw JSON of the term payload anywhere on the page', () => {
    // JSON.stringify(rawTerm) must not reach the page, not even inside the
    // expandable.
    const term: MarketplaceOfferTerm = {
      termId: 'term-legal-1',
      termType: 'LegalTerm',
      rawTerm: {
        documents: [
          { type: 'CustomEula', url: 'https://awsmp-legal.example/eula.pdf' },
        ],
        opaqueMarker: 'RAW_JSON_MARKER_9d3f7a',
      },
    };
    const { container } = render(<TermSummary term={term} />);
    // Neither the field name nor its value should appear as text.
    expect(container.textContent).not.toContain('opaqueMarker');
    expect(container.textContent).not.toContain('RAW_JSON_MARKER_9d3f7a');
    // Nor should there be a <pre> element in the tree.
    expect(container.querySelector('pre')).toBeNull();
  });

  it('renders a SupportTerm with the refund policy text', () => {
    const term: MarketplaceOfferTerm = {
      termId: 'term-support-1',
      termType: 'SupportTerm',
      rawTerm: {
        id: 'term-support-1',
        type: 'SupportTerm',
        refundPolicy: 'No refunds will be issued for usage of this product.',
      },
    };
    render(<TermSummary term={term} />);

    expect(screen.getByText('Support')).toBeTruthy();
    expect(screen.getByText('Refund policy')).toBeTruthy();
    expect(
      screen.getByText('No refunds will be issued for usage of this product.'),
    ).toBeTruthy();
  });

  it('renders a UsageBasedPricingTerm with a free-tier summary and a rate table', () => {
    const term: MarketplaceOfferTerm = {
      termId: 'term-pricing-1',
      termType: 'UsageBasedPricingTerm',
      rawTerm: {
        id: 'term-pricing-1',
        type: 'UsageBasedPricingTerm',
        currencyCode: 'USD',
        rateCards: [{
          rateCard: [
            { price: '0', unit: 'Hrs', dimensionKey: 'i4i.xlarge', displayName: 'i4i.xlarge' },
            { price: '0', unit: 'Hrs', dimensionKey: 'm5.large', displayName: 'm5.large' },
          ],
        }],
      },
    };
    const { container } = render(<TermSummary term={term} />);

    expect(screen.getByText('Usage-based pricing')).toBeTruthy();
    // "free" appears in both the summary line and the rate card cell —
    // just assert that at least one match exists.
    expect(screen.getAllByText(/free/iu).length).toBeGreaterThan(NONE);
    // Rate card table is present (identified by data-test).
    const table = container.querySelector('[data-test="rate-card-term-pricing-1"]');
    expect(table).not.toBeNull();
  });

  it('renders a LegalTerm without documents with a helpful fallback', () => {
    const term: MarketplaceOfferTerm = {
      termId: 'term-legal-empty',
      termType: 'LegalTerm',
      rawTerm: { documents: [] },
    };
    render(<TermSummary term={term} />);
    expect(screen.getByText('Legal terms')).toBeTruthy();
    expect(
      screen.getByText('No documents provided for this legal term.'),
    ).toBeTruthy();
  });

  it('renders an unknown term type with just a titlecased heading', () => {
    const term: MarketplaceOfferTerm = {
      termId: 'term-unknown',
      termType: 'FancyNewTerm',
      rawTerm: { arbitrary: 'field' },
    };
    render(<TermSummary term={term} />);
    // "FancyNewTerm" → "Fancy New" (trailing "Term" stripped).
    expect(screen.getByText('Fancy New')).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// `documents[].url` is seller-controlled. Only allowlisted schemes may render
// as a live `<Link href=...>` on the screen where the buyer accepts the
// agreement.
// ---------------------------------------------------------------------------
describe('TermSummary — seller-supplied legal document URLs', () => {
  const legalTermWithUrl = (url: string): MarketplaceOfferTerm => ({
    termId: 'term-legal-x',
    termType: 'LegalTerm',
    rawTerm: {
      id: 'term-legal-x',
      type: 'LegalTerm',
      documents: [{ type: 'CustomEula', url }],
    },
  });

  it('renders an https document URL as a link', () => {
    const { container } = render(
      <TermSummary term={legalTermWithUrl('https://example.com/eula.pdf')} />,
    );
    const link = container.querySelector('a[href="https://example.com/eula.pdf"]');
    expect(link).not.toBeNull();
  });

  it('renders a javascript: document URL as unavailable, not as a link', () => {
    const { container } = render(
      <TermSummary term={legalTermWithUrl('javascript:alert(document.cookie)')} />,
    );
    expect(container.querySelector('a')).toBeNull();
    expect(screen.getByText(/document not available/iu)).toBeTruthy();
  });

  it('renders a data: document URL as unavailable, not as a link', () => {
    const { container } = render(
      <TermSummary term={legalTermWithUrl('data:text/html,<script>alert(1)</script>')} />,
    );
    expect(container.querySelector('a')).toBeNull();
    expect(screen.getByText(/document not available/iu)).toBeTruthy();
  });

  it('renders a plain http document URL as unavailable', () => {
    // A contract document a buyer may rely on is not silently fetched over
    // cleartext on the seller's behalf.
    const { container } = render(
      <TermSummary term={legalTermWithUrl('http://example.com/eula.pdf')} />,
    );
    expect(container.querySelector('a')).toBeNull();
  });

  it('leaves no anchor carrying a javascript: href', () => {
    const { container } = render(
      <TermSummary term={legalTermWithUrl('JaVaScRiPt:alert(1)')} />,
    );
    const hrefs = Array.from(container.querySelectorAll('a'))
      .map((a) => a.getAttribute('href') || '');
    expect(hrefs.some((h) => h.toLowerCase().includes('javascript:'))).toBe(false);
  });
});
