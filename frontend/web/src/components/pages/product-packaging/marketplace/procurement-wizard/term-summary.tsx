// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// TermSummary — render a single ``MarketplaceOfferTerm`` in a
// user-friendly way, with a collapsed technical-details section for
// support engineers who need to reference the term hash.
//
// Design:
//   - LegalTerm → heading "Legal terms" + one link per document
//     ("View End-User License Agreement ↗") opening the presigned URL
//     in a new tab.
//   - SupportTerm → heading "Support" + refund policy body text.
//   - Pricing terms → heading + one-line summary + a proper Cloudscape
//     Table showing the rate card (dimension | unit | price), grouped
//     by identical price so a 100-instance-type free-tier offer isn't
//     a 100-row wall of $0.
//   - Anything else → heading + friendly type label.
//
// The technical-details section is collapsed by default, contains ONLY
// the term hash + type (no raw JSON dump). Raw JSON is available in the browser
// devtools console via a data attribute on the rendered node for
// support engineers who need to inspect it.

import { FC } from 'react';
import {
  Box,
  ExpandableSection,
  Header,
  Link,
  SpaceBetween,
} from '@cloudscape-design/components';
import { MarketplaceOfferTerm } from '../../../../../services/API/marketplace-procurement-api';
import {
  extractLegalDocuments,
  extractRefundPolicy,
  getTermTypeLabel,
  summarizePricingTerm,
} from './offer-helpers';
import { PricingRateCardTable } from './pricing-rate-card-table';
import { safeExternalUrl } from '../safe-external-url';

interface TermSummaryProps {
  term: MarketplaceOfferTerm,
}

const TechnicalDetails: FC<{ term: MarketplaceOfferTerm }> = ({ term }) =>
  <ExpandableSection
    headerText="Technical reference"
    variant="footer"
    defaultExpanded={false}
    data-test={`term-tech-${term.termId}`}
  >
    <SpaceBetween size="xs">
      <div>
        <Box variant="awsui-key-label">Term ID</Box>
        <Box variant="small">
          <code style={{ fontSize: '11px' }}>{term.termId}</code>
        </Box>
      </div>
      <div>
        <Box variant="awsui-key-label">Term type</Box>
        <Box variant="small">
          <code style={{ fontSize: '11px' }}>{term.termType}</code>
        </Box>
      </div>
      {/*
        Raw JSON is intentionally NOT rendered here. If a support engineer
        needs it, it's available on the term object in devtools (or via
        the API directly).
      */}
    </SpaceBetween>
  </ExpandableSection>
;

/**
 * LegalTerm rendering: heading + one link per document.
 */
const NO_DOCUMENTS = 0;

const LegalTermBody: FC<{ term: MarketplaceOfferTerm }> = ({ term }) => {
  const docs = extractLegalDocuments(term);
  if (docs.length === NO_DOCUMENTS) {
    return (
      <Box color="text-body-secondary" variant="p">
        No documents provided for this legal term.
      </Box>
    );
  }
  return (
    <SpaceBetween size="xs">
      {docs.map((doc, i) => {
        const key = `${term.termId}-doc-${i}`;
        // Seller-authored URL: gate it on the scheme allowlist. A rejected or
        // absent URL renders as unavailable rather than as a live link -- these
        // are the EULA and privacy documents a buyer is about to agree to, so
        // "we could not verify this link" is the only honest rendering.
        const safeUrl = safeExternalUrl(doc.url);
        if (!safeUrl) {
          return (
            <Box key={key} color="text-body-secondary" variant="p">
              {doc.displayName} (document not available)
            </Box>
          );
        }
        return (
          <div key={key}>
            <Link
              href={safeUrl}
              external
              externalIconAriaLabel="Opens in a new tab"
              data-test={`legal-doc-${i}`}
            >
              View {doc.displayName}
              {doc.version ? ` (v${doc.version})` : ''}
            </Link>
          </div>
        );
      })}
    </SpaceBetween>
  );
};

/**
 * SupportTerm rendering: refund policy text.
 */
const SupportTermBody: FC<{ term: MarketplaceOfferTerm }> = ({ term }) => {
  const policy = extractRefundPolicy(term);
  return (
    <SpaceBetween size="xs">
      <div>
        <Box variant="awsui-key-label">Refund policy</Box>
        <Box variant="p" data-test={`support-refund-${term.termId}`}>
          {policy || 'No refund policy provided.'}
        </Box>
      </div>
    </SpaceBetween>
  );
};

/**
 * Pricing term rendering: one-line summary + rate card table.
 */
const PricingTermBody: FC<{ term: MarketplaceOfferTerm }> = ({ term }) => {
  const summary = summarizePricingTerm(term);
  return (
    <SpaceBetween size="xs">
      {summary &&
        <Box variant="p" data-test={`pricing-summary-${term.termId}`}>
          {summary}
        </Box>
      }
      <PricingRateCardTable term={term} />
    </SpaceBetween>
  );
};

const isPricingTerm = (termType: string): boolean =>
  termType.endsWith('PricingTerm')
  || termType === 'RecurringPaymentTerm'
  || termType === 'FreeTrialTerm'
  || termType === 'PaymentScheduleTerm';

const renderBody = (term: MarketplaceOfferTerm) => {
  if (term.termType === 'LegalTerm') { return <LegalTermBody term={term} />; }
  if (term.termType === 'SupportTerm') { return <SupportTermBody term={term} />; }
  if (isPricingTerm(term.termType)) { return <PricingTermBody term={term} />; }
  return null;
};

export const TermSummary: FC<TermSummaryProps> = ({ term }) => {
  const label = getTermTypeLabel(term.termType);
  return (
    <SpaceBetween size="xs">
      <Header variant="h3">{label}</Header>
      {renderBody(term)}
      <TechnicalDetails term={term} />
    </SpaceBetween>
  );
};
