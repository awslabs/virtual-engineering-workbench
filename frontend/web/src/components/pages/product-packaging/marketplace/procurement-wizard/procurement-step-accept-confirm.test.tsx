// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import { RecoilRoot, SetRecoilState } from 'recoil';
import { describe, it, expect, vi } from 'vitest';
import { ProcurementStepAcceptConfirm } from './procurement-step-accept-confirm';
import { selectedProjectState } from '../../../../../state';
import { GetMarketplaceOfferResponse } from '../../../../../services/API/marketplace-procurement-api';

const CurrentLocation = () => {
  const loc = useLocation();
  return <div data-testid="current-location">{loc.pathname + loc.search}</div>;
};

const makeOffer = (
  overrides: Partial<GetMarketplaceOfferResponse> = {},
): GetMarketplaceOfferResponse => ({
  offerId: 'offer-1',
  catalog: 'AWSMarketplace',
  agreementProposalId: 'ap-1',
  offerName: 'Ubuntu Noble',
  associatedProducts: [{ productId: 'prod-1', productName: 'Ubuntu 24.04 LTS' }],
  terms: [],
  ...overrides,
});

// Default props used by tests that don't care about identity/flow copy.
const defaultProps = {
  offer: null,
  wizardFlow: 'USAGE' as const,
};

const renderStep = (props: React.ComponentProps<typeof ProcurementStepAcceptConfirm>) => {
  const initializeState = ({ set }: { set: SetRecoilState }) => {
    set(selectedProjectState, { projectId: 'proj-1', projectName: 'Test' });
  };
  return render(
    <MemoryRouter initialEntries={['/wizard']}>
      <RecoilRoot initializeState={initializeState}>
        <Routes>
          <Route path="/wizard" element={
            <>
              <ProcurementStepAcceptConfirm {...props} />
              <CurrentLocation />
            </>
          }
          />
          <Route path="*" element={<CurrentLocation />} />
        </Routes>
      </RecoilRoot>
    </MemoryRouter>,
  );
};

describe('ProcurementStepAcceptConfirm — post-accept handoff', () => {
  it('renders both Import this AMI and Go to agreements buttons on success', () => {
    renderStep({
      ...defaultProps,
      acceptance: { agreementId: 'agmt-123' },
      isLoading: false,
      error: null,
      onAccept: vi.fn(),
    });

    expect(screen.getByText('Import this AMI')).toBeTruthy();
    expect(screen.getByText('Go to agreements')).toBeTruthy();
    // Success alert with agreement id.
    expect(screen.getByText('agmt-123')).toBeTruthy();
  });

  it('Import this AMI button navigates to /images/import?source=marketplace', () => {
    renderStep({
      ...defaultProps,
      acceptance: { agreementId: 'agmt-456' },
      isLoading: false,
      error: null,
      onAccept: vi.fn(),
    });

    fireEvent.click(screen.getByText('Import this AMI'));

    // The router lands on the Import Image path with the deep-link query.
    // The path template contains a literal ":projectId" because the codebase
    // navigates via literal-param URLs (project id is stored in Recoil, not
    // read from useParams for this route).
    const loc = screen.getByTestId('current-location');
    expect(loc.textContent).toBe('/projects/:projectId/images/import?source=marketplace');
  });

  it('Import this AMI carries the purchased product id, not its name', () => {
    renderStep({
      ...defaultProps,
      offer: makeOffer({
        associatedProducts: [{ productId: 'prod-Abc123', productName: 'Ubuntu 24.04 LTS' }],
      }),
      acceptance: { agreementId: 'agmt-456' },
      isLoading: false,
      error: null,
      onAccept: vi.fn(),
    });

    fireEvent.click(screen.getByText('Import this AMI'));

    expect(screen.getByTestId('current-location').textContent)
      .toBe('/projects/:projectId/images/import?source=marketplace&productId=prod-Abc123');
  });

  it('renders next-steps hint text explaining subscription discovery lag', () => {
    renderStep({
      ...defaultProps,
      acceptance: { agreementId: 'agmt-789' },
      isLoading: false,
      error: null,
      onAccept: vi.fn(),
    });
    expect(screen.getByText(/subscription will appear in the Marketplace/u)).toBeTruthy();
  });

  it('does not render the buttons on the pristine (no acceptance yet) state', () => {
    renderStep({
      ...defaultProps,
      acceptance: null,
      isLoading: false,
      error: null,
      onAccept: vi.fn(),
    });
    expect(screen.queryByText('Import this AMI')).toBeNull();
    expect(screen.queryByText('Go to agreements')).toBeNull();
  });
});

describe('ProcurementStepAcceptConfirm — commit step (pristine)', () => {
  // Pristine state: user just landed on the Accept & Confirm step. The
  // component should show identity + a flow-specific "what Finish does"
  // description. No rate cards, no legal doc list — those were on step 2.

  it('renders the product identity + pricing model badge for USAGE offers', () => {
    renderStep({
      acceptance: null,
      isLoading: false,
      error: null,
      onAccept: vi.fn(),
      offer: makeOffer({ pricingModelType: 'USAGE' }),
      wizardFlow: 'USAGE',
    });

    // Identity line — product name is preferred over offer name.
    expect(screen.getByText('Ubuntu 24.04 LTS')).toBeTruthy();
    // Pricing model badge.
    expect(screen.getByText('Pay-as-you-go')).toBeTruthy();
    // Flow-specific commit description.
    expect(screen.getByText(/AWS bills you per hour based on the EC2 instance type/u)).toBeTruthy();
    // No upfront commitment language.
    expect(screen.getByText(/no upfront commitment/u)).toBeTruthy();
  });

  it('renders the FREE badge + FREE-specific description for FREE offers', () => {
    renderStep({
      acceptance: null,
      isLoading: false,
      error: null,
      onAccept: vi.fn(),
      offer: makeOffer({ pricingModelType: 'FREE' }),
      wizardFlow: 'FREE',
    });

    expect(screen.getByText('Free')).toBeTruthy();
    // FREE-specific hint — still pay AWS for EC2 compute.
    expect(screen.getByText(/There is no software licence fee/u)).toBeTruthy();
    expect(screen.getByText(/you still pay AWS for the EC2 instance itself/u)).toBeTruthy();
  });

  it('renders the BYOL badge + BYOL-specific description for BYOL offers', () => {
    renderStep({
      acceptance: null,
      isLoading: false,
      error: null,
      onAccept: vi.fn(),
      offer: makeOffer({ pricingModelType: 'BYOL' }),
      wizardFlow: 'BYOL',
    });

    expect(screen.getByText('Bring your own license')).toBeTruthy();
    expect(screen.getByText(/grants your account permission to launch/u)).toBeTruthy();
  });

  it('does NOT re-render a rate card, legal doc list, or pricing summary on pristine state', () => {
    // The Review Terms step is the
    // single source of truth for pricing detail. The commit step is
    // deliberately terse — no rate cards, no legal doc list, no
    // per-instance-type pricing.
    renderStep({
      acceptance: null,
      isLoading: false,
      error: null,
      onAccept: vi.fn(),
      offer: makeOffer({ pricingModelType: 'USAGE' }),
      wizardFlow: 'USAGE',
    });

    // These are labels used only on the Review Terms step. If any of them
    // appear on Accept & Confirm we're duplicating information.
    expect(screen.queryByText('Legal terms')).toBeNull();
    expect(screen.queryByText(/rate card/iu)).toBeNull();
    expect(screen.queryByText(/Refund policy/iu)).toBeNull();
    // No charge summary WITHOUT a quote prop. The guard is about not
    // duplicating Review Terms' pricing *detail* (rate cards, per-instance
    // pricing); it is NOT a licence to hide the quoted total, which is
    // rendered when `quote` is supplied — see the CONTRACT test below.
    expect(screen.queryByText(/Estimated agreement value/iu)).toBeNull();
    expect(document.querySelector('[data-test="commit-quote-summary"]')).toBeNull();
  });

  it('shows the quoted total before Finish, so a CONTRACT commit is never blind', () => {
    // The CONTRACT flow replaces step 3's ProcurementStepGetQuote with
    // ProcurementStepConfigurePricing, so the only component that renders the
    // charge fields never appears. Without this a buyer could commit to a
    // priced annual contract having never been shown what AWS would charge.
    renderStep({
      acceptance: null,
      isLoading: false,
      error: null,
      onAccept: vi.fn(),
      offer: makeOffer({ pricingModelType: 'CONTRACT' }),
      wizardFlow: 'CONTRACT',
      quote: {
        agreementRequestId: 'ar-test-1',
        estimatedAgreementValue: '400.00',
        estimatedAgreementValueAfterTax: '476.00',
        estimatedCurrencyCode: 'USD',
      },
    });

    const panel = document.querySelector('[data-test="commit-quote-summary"]');
    expect(panel).toBeTruthy();
    const value = document.querySelector('[data-test="commit-estimated-value"]');
    expect(value?.textContent).toContain('400.00');
    expect(value?.textContent).toContain('USD');
    expect(document.querySelector('[data-test="commit-estimated-value-after-tax"]')?.textContent)
      .toContain('476.00');
    expect(document.querySelector('[data-test="commit-agreement-request-id"]')?.textContent)
      .toContain('ar-test-1');
  });

  it('says "usage-based" rather than a fake zero when AWS returns no estimate', () => {
    // Hourly/usage offers legitimately carry no concrete estimate. Rendering
    // "0.00" there would invent a price; an em-dash reads as a bug.
    renderStep({
      acceptance: null,
      isLoading: false,
      error: null,
      onAccept: vi.fn(),
      offer: makeOffer({ pricingModelType: 'USAGE' }),
      wizardFlow: 'USAGE',
      quote: {
        agreementRequestId: 'ar-test-2',
        estimatedAgreementValue: null,
        estimatedAgreementValueAfterTax: null,
        estimatedCurrencyCode: null,
      },
    });

    const usageValue = document.querySelector('[data-test="commit-estimated-value"]');
    expect(usageValue?.textContent).toContain('Usage-based pricing');
    expect(usageValue?.textContent).not.toContain('0.00');
  });

  it('gracefully handles a null offer prop (edge case: initial-offer flow before fetch)', () => {
    // If somehow the wizard reaches step 3 without a resolved offer, we
    // still want to render the flow-specific description — just no
    // identity line.
    renderStep({
      acceptance: null,
      isLoading: false,
      error: null,
      onAccept: vi.fn(),
      offer: null,
      wizardFlow: 'USAGE',
    });

    expect(screen.getByText(/AWS bills you per hour/u)).toBeTruthy();
    // No identity line rendered — safe fallback.
    expect(screen.queryByText('Ubuntu 24.04 LTS')).toBeNull();
  });
});

describe('ProcurementStepAcceptConfirm — quote money display', () => {
  const quoteWith = (
    estimatedAgreementValue: string | null,
    estimatedCurrencyCode: string | null,
  ) => ({
    agreementRequestId: 'ar-money',
    estimatedAgreementValue,
    estimatedAgreementValueAfterTax: estimatedAgreementValue,
    estimatedCurrencyCode,
  });
  const valueCell = () =>
    document.querySelector('[data-test="commit-estimated-value"]')?.textContent;

  it('flags a CONTRACT quote without an estimate instead of calling it usage-based', () => {
    renderStep({
      acceptance: null,
      isLoading: false,
      error: null,
      onAccept: vi.fn(),
      offer: makeOffer({ pricingModelType: 'CONTRACT' }),
      wizardFlow: 'CONTRACT',
      quote: quoteWith(null, null),
    });

    expect(valueCell()).toContain('Estimate unavailable');
    expect(valueCell()).not.toContain('Usage-based');
    expect(screen.getByText('No estimated total from AWS')).toBeInTheDocument();
    expect(screen.getByText(/so it cannot be accepted/u)).toBeInTheDocument();
  });

  it('offers a new quote when a CONTRACT quote has no estimate', () => {
    const onRequestNewQuote = vi.fn();
    renderStep({
      acceptance: null,
      isLoading: false,
      error: null,
      onAccept: vi.fn(),
      onRequestNewQuote,
      offer: makeOffer({ pricingModelType: 'CONTRACT' }),
      wizardFlow: 'CONTRACT',
      quote: quoteWith(null, null),
    });

    const button = document.querySelector('[data-test="estimate-get-new-quote-btn"]');
    expect(button?.textContent).toBe('Get a new quote');
    fireEvent.click(button as Element);
    expect(onRequestNewQuote).toHaveBeenCalledOnce();
  });

  it('shows a value that arrived without a currency', () => {
    renderStep({
      acceptance: null,
      isLoading: false,
      error: null,
      onAccept: vi.fn(),
      offer: makeOffer({ pricingModelType: 'CONTRACT' }),
      wizardFlow: 'CONTRACT',
      quote: quoteWith('400.00', null),
    });

    expect(valueCell()).toContain('400.00 (currency unknown)');
    expect(screen.queryByText('No estimated total from AWS')).toBeNull();
  });

  it('keeps "usage-based" for a USAGE quote without an estimate, with no warning', () => {
    renderStep({
      acceptance: null,
      isLoading: false,
      error: null,
      onAccept: vi.fn(),
      offer: makeOffer({ pricingModelType: 'USAGE' }),
      wizardFlow: 'USAGE',
      quote: quoteWith(null, null),
    });

    expect(valueCell()).toContain('Usage-based pricing');
    expect(screen.queryByText('No estimated total from AWS')).toBeNull();
  });
});
