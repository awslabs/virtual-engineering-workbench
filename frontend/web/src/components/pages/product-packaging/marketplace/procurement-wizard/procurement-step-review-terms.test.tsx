// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ProcurementStepReviewTerms } from './procurement-step-review-terms';
import { i18n } from './procurement-wizard.translations';
import { GetMarketplaceOfferResponse } from '../../../../../services/API/marketplace-procurement-api';

const OFFER = {
  offerId: 'offer-1',
  pricingModelType: 'FREE',
  terms: [{ termId: 'term-legal', termType: 'LegalTerm', rawTerm: {} }],
} as unknown as GetMarketplaceOfferResponse;

const renderStep = (quoteBlockedMessage?: string | null) => render(
  <ProcurementStepReviewTerms
    offer={OFFER}
    isLoading={false}
    error={null}
    agreedToTerms
    setAgreedToTerms={vi.fn()}
    onRetry={vi.fn()}
    quoteBlockedMessage={quoteBlockedMessage}
  />,
);

describe('ProcurementStepReviewTerms', () => {
  it('shows why the request was refused', () => {
    renderStep(i18n.freeOfferChargesError);
    expect(screen.getByText(i18n.freeOfferChargesError)).toBeInTheDocument();
  });

  it('shows no refusal when the request was not refused', () => {
    renderStep(null);
    expect(screen.queryByText(i18n.freeOfferChargesError)).not.toBeInTheDocument();
  });
});
