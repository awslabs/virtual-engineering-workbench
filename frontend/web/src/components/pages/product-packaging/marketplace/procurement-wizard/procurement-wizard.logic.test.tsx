// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from 'react';
import { renderHook, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { RecoilRoot, SetRecoilState } from 'recoil';
import { SWRConfig } from 'swr';
import { describe, it, expect, vi } from 'vitest';
import {
  useProcurementWizard,
  QUANTITY_QUOTE_DEBOUNCE_MS,
  STEP_BROWSE_OFFERS,
  STEP_REVIEW_TERMS,
  STEP_GET_QUOTE,
  STEP_ACCEPT_CONFIRM,
} from './procurement-wizard.logic';
import { i18n } from './procurement-wizard.translations';
import { selectedProjectState } from '../../../../../state';

const NO_DEDUPING = 0;
const NO_DELAY_MS = 0;
const LAST = -1;
const FOUR = 4;
const TEN = 10;
const ONCE = 1;
const TWICE = 2;
const tick = () => new Promise<void>((resolve) => { setTimeout(resolve, NO_DELAY_MS); });

// Mock the procurement API wrapper so no real network is hit.
vi.mock('../../../../../services/API/marketplace-procurement-api', async () => {
  const actual = await vi.importActual<typeof import(
    '../../../../../services/API/marketplace-procurement-api'
  )>('../../../../../services/API/marketplace-procurement-api');
  return {
    ...actual,
    marketplaceProcurementAPI: {
      listPurchaseOptions: vi.fn().mockResolvedValue({ purchaseOptions: [] }),
      getOffer: vi.fn().mockResolvedValue({ offerId: 'offer-1', terms: [] }),
      createAgreementRequest: vi.fn().mockResolvedValue({ agreementRequestId: 'ar-1' }),
      acceptAgreementRequest: vi.fn().mockResolvedValue({ agreementId: 'agmt-1' }),
      cancelAgreement: vi.fn(),
    },
  };
});

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const initializeState = ({ set }: { set: SetRecoilState }) => {
    set(selectedProjectState, { projectId: 'proj-1' });
  };
  return (
    <MemoryRouter>
      <RecoilRoot initializeState={initializeState}>
        <SWRConfig value={{ provider: () => new Map(), dedupingInterval: NO_DEDUPING }}>
          {children}
        </SWRConfig>
      </RecoilRoot>
    </MemoryRouter>
  );
};

const OPTION = {
  purchaseOptionId: 'po-1',
  purchaseOptionType: 'OFFER',
  catalog: 'AWSMarketplace',
  offerId: 'offer-1',
  productId: 'prod-1',
};

describe('useProcurementWizard.canProceedFromStep', () => {
  it('gates step 0 on productType and selectedOption', () => {
    const { result } = renderHook(() => useProcurementWizard(), { wrapper });
    expect(result.current.canProceedFromStep(STEP_BROWSE_OFFERS)).toBe(false); // no selection
  });

  it('gates step 3 (Finish) on having a successful quote', async () => {
    const { result } = renderHook(() => useProcurementWizard(), { wrapper });
    // Nothing done yet → cannot Finish.
    expect(result.current.canProceedFromStep(STEP_ACCEPT_CONFIRM)).toBe(false);

    // Select an offer → fetches the offer + resets any stale quote/acceptance.
    await act(async () => {
      await result.current.handleSelectPurchaseOption(OPTION);
    });
    expect(result.current.canProceedFromStep(STEP_ACCEPT_CONFIRM)).toBe(false);

    // Request a quote → now Finish is allowed.
    await act(async () => {
      await result.current.handleRequestQuote();
    });
    expect(result.current.canProceedFromStep(STEP_ACCEPT_CONFIRM)).toBe(true);
  });
});

describe('useProcurementWizard offer-switch resets stale state', () => {
  it('clears quote + acceptance when the user picks a different offer', async () => {
    const { result } = renderHook(() => useProcurementWizard(), { wrapper });

    await act(async () => {
      await result.current.handleSelectPurchaseOption(OPTION);
    });
    await act(async () => {
      await result.current.handleRequestQuote();
    });
    await act(async () => {
      await result.current.handleAcceptQuote();
    });

    expect(result.current.quote.data?.agreementRequestId).toBe('ar-1');
    expect(result.current.acceptance.data?.agreementId).toBe('agmt-1');

    // Switching to a different offer must nuke both — otherwise Finish on the new
    // offer would use the previous offer's acceptance result.
    await act(async () => {
      await result.current.handleSelectPurchaseOption({ ...OPTION, offerId: 'offer-2' });
    });

    expect(result.current.quote.data).toBeNull();
    expect(result.current.acceptance.data).toBeNull();
    expect(result.current.agreedToTerms).toBe(false);
  });
});

describe('useProcurementWizard.handleBackwardNavigation', () => {
  it('resets quote + acceptance when stepping back past step 3', async () => {
    const { result } = renderHook(() => useProcurementWizard(), { wrapper });

    await act(async () => {
      await result.current.handleSelectPurchaseOption(OPTION);
    });
    await act(async () => {
      await result.current.handleRequestQuote();
    });
    expect(result.current.quote.data?.agreementRequestId).toBe('ar-1');

    // Stepping back from step 3 (index 2) to step 2 (index 1) should reset the quote —
    // if the user changes terms and re-quotes, we want a fresh AR id, not the stale one.
    act(() => {
      result.current.handleBackwardNavigation(STEP_GET_QUOTE, STEP_REVIEW_TERMS);
    });
    expect(result.current.quote.data).toBeNull();
  });

  it('does not reset when stepping backward through step 1', async () => {
    const { result } = renderHook(() => useProcurementWizard(), { wrapper });
    await act(async () => {
      await result.current.handleSelectPurchaseOption(OPTION);
    });
    // No quote yet, but the offer is loaded. Step 1 → step 0 shouldn't clear anything.
    act(() => {
      result.current.handleBackwardNavigation(STEP_REVIEW_TERMS, STEP_BROWSE_OFFERS);
    });
    expect(result.current.offer.data).not.toBeNull();
  });
});

describe('useProcurementWizard with initialOfferId (listing-detail handoff)', () => {
  it('starts on step 2 (Review terms) when initialOfferId is provided', () => {
    const { result } = renderHook(
      () => useProcurementWizard({ initialOfferId: 'offer-from-listing' }),
      { wrapper },
    );

    expect(result.current.activeStepIndex).toBe(STEP_REVIEW_TERMS);
    expect(result.current.startedFromInitialOffer).toBe(true);
    // A synthetic selectedOption should have been pre-populated with the offerId.
    expect(result.current.selectedOption?.offerId).toBe('offer-from-listing');
    expect(result.current.selectedOption?.purchaseOptionType).toBe('OFFER');
  });

  it('starts on step 1 (Browse offers) when initialOfferId is absent', () => {
    const { result } = renderHook(() => useProcurementWizard(), { wrapper });

    expect(result.current.activeStepIndex).toBe(STEP_BROWSE_OFFERS);
    expect(result.current.startedFromInitialOffer).toBe(false);
    expect(result.current.selectedOption).toBeNull();
  });

  it('fetches the offer detail automatically when initialOfferId is provided', async () => {
    const { result } = renderHook(
      () => useProcurementWizard({ initialOfferId: 'offer-auto-fetch' }),
      { wrapper },
    );

    // useEffect fires after render — wait for the offer to resolve.
    await act(async () => {
      await tick();
    });

    expect(result.current.offer.data?.offerId).toBe('offer-1');
  });
});

describe('useProcurementWizard.handleRequestQuote filters terms per pricing model', () => {
  // AWS's CreateAgreementRequest rejects a request that carries a
  // ConfigurableUpfrontPricingTerm without a `configuration` payload, so a
  // USAGE request must not forward every offer term (e.g. a Palo Alto offer
  // with both usage and upfront terms). This verifies the wizard filters the
  // terms through `filterTermsForRequestedPayload`.
  it('USAGE offer with a ConfigurableUpfrontPricingTerm sends only usage + mandatory terms', async () => {
    const { marketplaceProcurementAPI } = await import(
      '../../../../../services/API/marketplace-procurement-api'
    );
    // Palo Alto-shaped mixed-terms offer: usage + configurable upfront.
    (marketplaceProcurementAPI.getOffer as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      offerId: 'offer-mixed-usage',
      pricingModelType: 'USAGE',
      terms: [
        { termId: 'term-legal', termType: 'LegalTerm', rawTerm: {} },
        { termId: 'term-support', termType: 'SupportTerm', rawTerm: {} },
        { termId: 'term-validity', termType: 'ValidityTerm', rawTerm: {} },
        { termId: 'term-usage', termType: 'UsageBasedPricingTerm', rawTerm: {} },
        // The offending term — AWS rejects this without configuration.
        { termId: 'term-configurable', termType: 'ConfigurableUpfrontPricingTerm', rawTerm: {} },
      ],
    });

    const { result } = renderHook(() => useProcurementWizard(), { wrapper });
    await act(async () => {
      await result.current.handleSelectPurchaseOption(OPTION);
    });
    await act(async () => {
      await result.current.handleRequestQuote();
    });

    expect(marketplaceProcurementAPI.createAgreementRequest).toHaveBeenCalledWith(
      'proj-1',
      OPTION.offerId,
      expect.objectContaining({
        requestedTerms: [
          { id: 'term-legal' },
          { id: 'term-support' },
          { id: 'term-validity' },
          { id: 'term-usage' },
          // NOTE: no term-configurable.
        ],
      }),
    );
  });

  it('CONTRACT offer forwards all terms to the backend', async () => {
    const { marketplaceProcurementAPI } = await import(
      '../../../../../services/API/marketplace-procurement-api'
    );
    (marketplaceProcurementAPI.getOffer as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      offerId: 'offer-contract',
      pricingModelType: 'CONTRACT',
      terms: [
        { termId: 'term-legal', termType: 'LegalTerm', rawTerm: {} },
        { termId: 'term-validity', termType: 'ValidityTerm', rawTerm: {} },
        { termId: 'term-fixed', termType: 'FixedUpfrontPricingTerm', rawTerm: {} },
        { termId: 'term-configurable', termType: 'ConfigurableUpfrontPricingTerm', rawTerm: {} },
      ],
    });

    const { result } = renderHook(() => useProcurementWizard(), { wrapper });
    await act(async () => {
      await result.current.handleSelectPurchaseOption(OPTION);
    });
    await act(async () => {
      await result.current.handleRequestQuote();
    });

    const call = (marketplaceProcurementAPI.createAgreementRequest as ReturnType<typeof vi.fn>)
      .mock.calls.at(LAST);
    expect(call?.[2].requestedTerms).toHaveLength(FOUR);
  });

  it('attaches enableAutoRenew=false to RenewalTerm when present', async () => {
    const { marketplaceProcurementAPI } = await import(
      '../../../../../services/API/marketplace-procurement-api'
    );
    (marketplaceProcurementAPI.getOffer as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      offerId: 'offer-with-renewal',
      pricingModelType: 'USAGE',
      terms: [
        { termId: 'term-legal', termType: 'LegalTerm', rawTerm: {} },
        { termId: 'term-usage', termType: 'UsageBasedPricingTerm', rawTerm: {} },
        { termId: 'term-renewal', termType: 'RenewalTerm', rawTerm: {} },
      ],
    });

    const { result } = renderHook(() => useProcurementWizard(), { wrapper });
    await act(async () => {
      await result.current.handleSelectPurchaseOption(OPTION);
    });
    await act(async () => {
      await result.current.handleRequestQuote();
    });

    const call = (marketplaceProcurementAPI.createAgreementRequest as ReturnType<typeof vi.fn>)
      .mock.calls.at(LAST);
    const renewalTerm = call?.[2].requestedTerms.find(
      (t: { id: string }) => t.id === 'term-renewal',
    );
    expect(renewalTerm).toEqual({
      id: 'term-renewal',
      configuration: {
        renewalTermConfiguration: { enableAutoRenew: false },
      },
    });
  });
});

// ---------------------------------------------------------------------------
// Quote staleness on pricing-configuration change (CONTRACT flow)
//
// A quote is a priced commitment. Before this, the auto-fire guard included
// `!quote.data`, so once any quote existed no new one was requested — the buyer
// could configure, get a quote, change the quantity or duration, and then accept
// the OLD quote. The Accept step would display one price and AWS would be sent
// an agreement request for another.
// ---------------------------------------------------------------------------
describe('useProcurementWizard quote staleness on config change', () => {
  const CONTRACT_OFFER = {
    offerId: 'offer-contract',
    pricingModelType: 'CONTRACT',
    terms: [
      { termId: 'term-legal', termType: 'LegalTerm', rawTerm: {} },
      { termId: 'term-cupt', termType: 'ConfigurableUpfrontPricingTerm', rawTerm: {} },
    ],
  };

  const CONFIG_12M = {
    termId: 'term-cupt',
    selectorValue: 'P12M',
    dimensions: [{ dimensionKey: 'Users', dimensionValue: TEN }],
  };
  const CONFIG_24M = {
    termId: 'term-cupt',
    selectorValue: 'P24M',
    dimensions: [{ dimensionKey: 'Users', dimensionValue: TEN }],
  };

  /** Drive the hook to "quoted for CONFIG_12M on the Configure step". */
  const arriveAtQuotedContractStep = async (
    result: { current: ReturnType<typeof useProcurementWizard> },
  ) => {
    await act(async () => {
      await result.current.handleSelectPurchaseOption(OPTION);
    });
    act(() => {
      result.current.setAgreedToTerms(true);
      result.current.setActiveStepIndex(STEP_GET_QUOTE);
    });
    await act(async () => {
      result.current.setContractConfig(CONFIG_12M);
      await tick();
    });
  };

  it('requests a NEW quote when the buyer changes the config after a quote exists', async () => {
    const { marketplaceProcurementAPI } = await import(
      '../../../../../services/API/marketplace-procurement-api'
    );
    const createMock = marketplaceProcurementAPI
      .createAgreementRequest as ReturnType<typeof vi.fn>;
    (marketplaceProcurementAPI.getOffer as ReturnType<typeof vi.fn>)
      .mockResolvedValue(CONTRACT_OFFER);
    createMock.mockReset();
    createMock
      .mockResolvedValueOnce({ agreementRequestId: 'ar-12m', estimatedAgreementValue: '1200' })
      .mockResolvedValueOnce({ agreementRequestId: 'ar-24m', estimatedAgreementValue: '2400' });

    const { result } = renderHook(() => useProcurementWizard(), { wrapper });
    await arriveAtQuotedContractStep(result);

    expect(result.current.quote.data?.agreementRequestId).toBe('ar-12m');
    expect(createMock).toHaveBeenCalledTimes(ONCE);

    // The buyer switches the duration to 24 months.
    await act(async () => {
      result.current.setContractConfig(CONFIG_24M);
      await tick();
    });

    // A second request must have been fired, with the NEW selectorValue, and
    // the quote in state must be the new one.
    expect(createMock).toHaveBeenCalledTimes(TWICE);
    const lastBody = createMock.mock.calls.at(LAST)?.[2];
    const cupt = lastBody.requestedTerms.find((t: { id: string }) => t.id === 'term-cupt');
    expect(cupt.configuration.configurableUpfrontPricingTermConfiguration.selectorValue)
      .toBe('P24M');
    expect(result.current.quote.data?.agreementRequestId).toBe('ar-24m');
  });

  it('blocks Finish while the held quote belongs to a superseded config', async () => {
    const { marketplaceProcurementAPI } = await import(
      '../../../../../services/API/marketplace-procurement-api'
    );
    const createMock = marketplaceProcurementAPI
      .createAgreementRequest as ReturnType<typeof vi.fn>;
    (marketplaceProcurementAPI.getOffer as ReturnType<typeof vi.fn>)
      .mockResolvedValue(CONTRACT_OFFER);
    createMock.mockReset();
    // The second request never settles, so the wizard is left holding ONLY the
    // stale quote — the window in which Finish must stay blocked.
    createMock
      .mockResolvedValueOnce({ agreementRequestId: 'ar-12m', estimatedAgreementValue: '1200' })
      .mockReturnValueOnce(new Promise(() => { /* never settles */ }));

    const { result } = renderHook(() => useProcurementWizard(), { wrapper });
    await arriveAtQuotedContractStep(result);
    expect(result.current.canProceedFromStep(STEP_ACCEPT_CONFIRM)).toBe(true);

    await act(async () => {
      result.current.setContractConfig(CONFIG_24M);
      await tick();
    });

    // THE MONEY ASSERTION: no accepting a quote priced for a config the buyer
    // has abandoned.
    expect(result.current.canProceedFromStep(STEP_ACCEPT_CONFIRM)).toBe(false);
    expect(result.current.hasCurrentQuote).toBe(false);
  });

  it('refuses to accept a quote whose config was superseded', async () => {
    const { marketplaceProcurementAPI } = await import(
      '../../../../../services/API/marketplace-procurement-api'
    );
    const createMock = marketplaceProcurementAPI
      .createAgreementRequest as ReturnType<typeof vi.fn>;
    const acceptMock = marketplaceProcurementAPI
      .acceptAgreementRequest as ReturnType<typeof vi.fn>;
    (marketplaceProcurementAPI.getOffer as ReturnType<typeof vi.fn>)
      .mockResolvedValue(CONTRACT_OFFER);
    createMock.mockReset();
    acceptMock.mockClear();
    createMock
      .mockResolvedValueOnce({ agreementRequestId: 'ar-12m', estimatedAgreementValue: '1200' })
      .mockReturnValueOnce(new Promise(() => { /* never settles */ }));

    const { result } = renderHook(() => useProcurementWizard(), { wrapper });
    await arriveAtQuotedContractStep(result);

    await act(async () => {
      result.current.setContractConfig(CONFIG_24M);
      await tick();
    });

    let accepted: unknown;
    await act(async () => {
      accepted = await result.current.handleAcceptQuote();
    });

    // Defence in depth: even called directly, bypassing the wizard's own gate,
    // acceptance must not reach AWS with the stale agreement request id.
    expect(accepted).toBeNull();
    expect(acceptMock).not.toHaveBeenCalledWith('ar-12m');
  });

  it('does not land an in-flight quote fired for the OLD config', async () => {
    const { marketplaceProcurementAPI } = await import(
      '../../../../../services/API/marketplace-procurement-api'
    );
    const createMock = marketplaceProcurementAPI
      .createAgreementRequest as ReturnType<typeof vi.fn>;
    (marketplaceProcurementAPI.getOffer as ReturnType<typeof vi.fn>)
      .mockResolvedValue(CONTRACT_OFFER);
    createMock.mockReset();

    // First request is held open; the buyer changes config while it is still
    // in flight; only then does the first response arrive.
    let releaseFirst!: (v: unknown) => void;
    const firstInFlight = new Promise((resolve) => { releaseFirst = resolve; });
    createMock
      .mockReturnValueOnce(firstInFlight)
      .mockResolvedValueOnce({ agreementRequestId: 'ar-24m', estimatedAgreementValue: '2400' });

    const { result } = renderHook(() => useProcurementWizard(), { wrapper });
    await act(async () => {
      await result.current.handleSelectPurchaseOption(OPTION);
    });
    act(() => {
      result.current.setAgreedToTerms(true);
      result.current.setActiveStepIndex(STEP_GET_QUOTE);
    });
    await act(async () => {
      result.current.setContractConfig(CONFIG_12M);
      await tick();
    });
    // In flight, nothing in state yet.
    expect(createMock).toHaveBeenCalledTimes(ONCE);
    expect(result.current.quote.data).toBeNull();

    // Config changes mid-request.
    await act(async () => {
      result.current.setContractConfig(CONFIG_24M);
      await tick();
    });

    // The abandoned request finally answers.
    await act(async () => {
      releaseFirst({ agreementRequestId: 'ar-12m-late', estimatedAgreementValue: '1200' });
      await tick();
    });

    // The late response for the abandoned 12-month config must not be the
    // quote the buyer sees or accepts.
    expect(result.current.quote.data?.agreementRequestId).not.toBe('ar-12m-late');
    expect(result.current.quote.data?.agreementRequestId).toBe('ar-24m');
  });

  // --- Calibration: the invalidation must not fire when nothing changed, or
  // --- the wizard would re-request a quote on every render.
  //
  // Asserts only on the request count and the quote in state, so it checks
  // the invalidation does not over-reach rather than failing merely because a
  // field is absent.
  it('does not re-request when the config is re-emitted with equal values', async () => {
    const { marketplaceProcurementAPI } = await import(
      '../../../../../services/API/marketplace-procurement-api'
    );
    const createMock = marketplaceProcurementAPI
      .createAgreementRequest as ReturnType<typeof vi.fn>;
    (marketplaceProcurementAPI.getOffer as ReturnType<typeof vi.fn>)
      .mockResolvedValue(CONTRACT_OFFER);
    createMock.mockReset();
    createMock.mockResolvedValue({ agreementRequestId: 'ar-12m', estimatedAgreementValue: '1200' });

    const { result } = renderHook(() => useProcurementWizard(), { wrapper });
    await arriveAtQuotedContractStep(result);
    expect(createMock).toHaveBeenCalledTimes(ONCE);

    // The Configure step rebuilds this object on every render/keystroke. A
    // fresh object with identical values is NOT a change.
    await act(async () => {
      result.current.setContractConfig({
        termId: 'term-cupt',
        selectorValue: 'P12M',
        dimensions: [{ dimensionKey: 'Users', dimensionValue: TEN }],
      });
      await tick();
    });

    expect(createMock).toHaveBeenCalledTimes(ONCE);
    expect(result.current.quote.data?.agreementRequestId).toBe('ar-12m');
    expect(result.current.canProceedFromStep(STEP_ACCEPT_CONFIRM)).toBe(true);
  });

  // --- Calibration: non-CONTRACT flows have no buyer config, so their quote
  // --- must never be invalidated by contractConfig churn.
  it('keeps a USAGE-flow quote even if contractConfig changes', async () => {
    const { marketplaceProcurementAPI } = await import(
      '../../../../../services/API/marketplace-procurement-api'
    );
    const createMock = marketplaceProcurementAPI
      .createAgreementRequest as ReturnType<typeof vi.fn>;
    (marketplaceProcurementAPI.getOffer as ReturnType<typeof vi.fn>)
      .mockResolvedValue({
        offerId: 'offer-usage',
        pricingModelType: 'USAGE',
        terms: [
          { termId: 'term-legal', termType: 'LegalTerm', rawTerm: {} },
          { termId: 'term-usage', termType: 'UsageBasedPricingTerm', rawTerm: {} },
        ],
      });
    createMock.mockReset();
    createMock.mockResolvedValue({ agreementRequestId: 'ar-usage' });

    const { result } = renderHook(() => useProcurementWizard(), { wrapper });
    await act(async () => {
      await result.current.handleSelectPurchaseOption(OPTION);
    });
    await act(async () => {
      result.current.setAgreedToTerms(true);
      await tick();
    });
    expect(result.current.quote.data?.agreementRequestId).toBe('ar-usage');
    const callsAfterQuote = createMock.mock.calls.length;

    await act(async () => {
      result.current.setContractConfig(CONFIG_24M);
      await tick();
    });

    expect(result.current.quote.data?.agreementRequestId).toBe('ar-usage');
    expect(result.current.canProceedFromStep(STEP_ACCEPT_CONFIRM)).toBe(true);
    expect(createMock.mock.calls.length).toBe(callsAfterQuote);
  });
});

// ---------------------------------------------------------------------------
// Idempotency token (clientToken) on CreateAgreementRequest
//
// Without one the backend derives a token from the request content, so a buyer
// who cancels and later re-subscribes with the same configuration gets the old
// request back. One token per purchase attempt and configuration.
// ---------------------------------------------------------------------------
describe('useProcurementWizard clientToken', () => {
  const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/u;
  const CONTRACT_OFFER = {
    offerId: 'offer-contract',
    pricingModelType: 'CONTRACT',
    terms: [{ termId: 'term-cupt', termType: 'ConfigurableUpfrontPricingTerm', rawTerm: {} }],
  };
  const configFor = (selectorValue: string) => ({
    termId: 'term-cupt',
    selectorValue,
    dimensions: [{ dimensionKey: 'Users', dimensionValue: TEN }],
  });

  const tokens = async () => {
    const { marketplaceProcurementAPI } = await import(
      '../../../../../services/API/marketplace-procurement-api'
    );
    return (marketplaceProcurementAPI.createAgreementRequest as ReturnType<typeof vi.fn>)
      .mock.calls.map((call) => call[2].clientToken as string);
  };

  const setUp = async () => {
    const { marketplaceProcurementAPI } = await import(
      '../../../../../services/API/marketplace-procurement-api'
    );
    (marketplaceProcurementAPI.getOffer as ReturnType<typeof vi.fn>)
      .mockResolvedValue(CONTRACT_OFFER);
    const createMock = marketplaceProcurementAPI
      .createAgreementRequest as ReturnType<typeof vi.fn>;
    createMock.mockReset();
    createMock.mockResolvedValue({ agreementRequestId: 'ar-1', estimatedAgreementValue: '400.00' });
  };

  const quoteFor = async (
    result: { current: ReturnType<typeof useProcurementWizard> },
    selectorValue: string,
  ) => {
    act(() => { result.current.setContractConfig(configFor(selectorValue)); });
    await act(async () => { await result.current.handleRequestQuote(); });
  };

  it('reuses the token when the same configuration is retried', async () => {
    await setUp();
    const { result } = renderHook(() => useProcurementWizard(), { wrapper });
    await act(async () => { await result.current.handleSelectPurchaseOption(OPTION); });

    await quoteFor(result, 'P12M');
    await act(async () => { await result.current.handleRequestQuote(); });

    const [first, retry] = await tokens();
    expect(first).toMatch(UUID);
    expect(retry).toBe(first);
  });

  it('mints a new token when the configuration changes', async () => {
    await setUp();
    const { result } = renderHook(() => useProcurementWizard(), { wrapper });
    await act(async () => { await result.current.handleSelectPurchaseOption(OPTION); });

    await quoteFor(result, 'P12M');
    await quoteFor(result, 'P24M');

    const [first, second] = await tokens();
    expect(second).toMatch(UUID);
    expect(second).not.toBe(first);
  });

  it('mints a new token for a new wizard session with the same configuration', async () => {
    await setUp();
    const first = renderHook(() => useProcurementWizard(), { wrapper });
    await act(async () => { await first.result.current.handleSelectPurchaseOption(OPTION); });
    await quoteFor(first.result, 'P12M');
    first.unmount();

    const second = renderHook(() => useProcurementWizard(), { wrapper });
    await act(async () => { await second.result.current.handleSelectPurchaseOption(OPTION); });
    await quoteFor(second.result, 'P12M');

    const [a, b] = await tokens();
    expect(b).toMatch(UUID);
    expect(b).not.toBe(a);
  });

  it('mints a new token when the buyer asks for a new quote after a rejected accept', async () => {
    await setUp();
    const { result } = renderHook(() => useProcurementWizard(), { wrapper });
    await act(async () => { await result.current.handleSelectPurchaseOption(OPTION); });
    await quoteFor(result, 'P12M');

    act(() => { result.current.handleRequestNewQuote(); });
    await act(async () => { await result.current.handleRequestQuote(); });

    const [first, fresh] = await tokens();
    expect(fresh).not.toBe(first);
  });

  it('mints a new token when the buyer steps back after a rejected accept', async () => {
    await setUp();
    const { marketplaceProcurementAPI } = await import(
      '../../../../../services/API/marketplace-procurement-api'
    );
    (marketplaceProcurementAPI.acceptAgreementRequest as ReturnType<typeof vi.fn>)
      .mockRejectedValueOnce(new Error('ValidationException: agreement request expired'));
    const { result } = renderHook(() => useProcurementWizard(), { wrapper });
    await act(async () => { await result.current.handleSelectPurchaseOption(OPTION); });
    await quoteFor(result, 'P12M');
    await act(async () => { await result.current.handleAcceptQuote(); });
    expect(result.current.acceptance.error).not.toBeNull();

    // Previous, from Accept & Confirm back to Configure, then re-quote the
    // same configuration.
    act(() => {
      result.current.handleBackwardNavigation(STEP_ACCEPT_CONFIRM, STEP_GET_QUOTE);
    });
    await act(async () => { await result.current.handleRequestQuote(); });

    const [rejected, fresh] = await tokens();
    expect(fresh).toMatch(UUID);
    expect(fresh).not.toBe(rejected);
  });
});

describe('useProcurementWizard CONTRACT quote without an estimate', () => {
  const CONTRACT_OFFER = {
    offerId: 'offer-contract',
    pricingModelType: 'CONTRACT',
    terms: [{ termId: 'term-cupt', termType: 'ConfigurableUpfrontPricingTerm', rawTerm: {} }],
  };
  const CONFIG = {
    termId: 'term-cupt',
    selectorValue: 'P12M',
    dimensions: [{ dimensionKey: 'Users', dimensionValue: TEN }],
  };

  const quoteContract = async (quoteResponse: Record<string, unknown>) => {
    const { marketplaceProcurementAPI } = await import(
      '../../../../../services/API/marketplace-procurement-api'
    );
    (marketplaceProcurementAPI.getOffer as ReturnType<typeof vi.fn>)
      .mockResolvedValue(CONTRACT_OFFER);
    const createMock = marketplaceProcurementAPI
      .createAgreementRequest as ReturnType<typeof vi.fn>;
    createMock.mockReset();
    createMock.mockResolvedValue(quoteResponse);
    const acceptMock = marketplaceProcurementAPI
      .acceptAgreementRequest as ReturnType<typeof vi.fn>;
    acceptMock.mockClear();

    const hook = renderHook(() => useProcurementWizard(), { wrapper });
    await act(async () => { await hook.result.current.handleSelectPurchaseOption(OPTION); });
    act(() => { hook.result.current.setContractConfig(CONFIG); });
    await act(async () => { await hook.result.current.handleRequestQuote(); });
    return { ...hook, acceptMock };
  };

  it('disables Finish and refuses to accept', async () => {
    const { result, acceptMock } = await quoteContract({
      agreementRequestId: 'ar-no-estimate',
      estimatedAgreementValue: null,
      estimatedCurrencyCode: 'USD',
    });
    expect(result.current.hasCurrentQuote).toBe(true);
    expect(result.current.canProceedFromStep(STEP_ACCEPT_CONFIRM)).toBe(false);

    await act(async () => { await result.current.handleAcceptQuote(); });
    expect(acceptMock).not.toHaveBeenCalled();
  });

  it('allows Finish once the quote carries an estimate', async () => {
    const { result } = await quoteContract({
      agreementRequestId: 'ar-estimate',
      estimatedAgreementValue: '400.00',
      estimatedCurrencyCode: 'USD',
    });
    expect(result.current.canProceedFromStep(STEP_ACCEPT_CONFIRM)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Quantity edits on the CONTRACT step are debounced
//
// Each valid quantity is a new configuration, and each configuration a real
// CreateAgreementRequest. Typing "50" must not request a quote for 5 first.
// ---------------------------------------------------------------------------
describe('useProcurementWizard debounces quotes for quantity edits', () => {
  const CONTRACT_OFFER = {
    offerId: 'offer-contract',
    pricingModelType: 'CONTRACT',
    terms: [{ termId: 'term-cupt', termType: 'ConfigurableUpfrontPricingTerm', rawTerm: {} }],
  };
  const withUsers = (dimensionValue: number, selectorValue = 'P12M') => ({
    termId: 'term-cupt',
    selectorValue,
    dimensions: [{ dimensionKey: 'Users', dimensionValue }],
  });
  const ONE_USER = 1;
  const FIVE_USERS = 5;
  const FIFTY_USERS = 50;
  const JUST_BEFORE = QUANTITY_QUOTE_DEBOUNCE_MS - ONE_USER;
  const HALF_WAY = QUANTITY_QUOTE_DEBOUNCE_MS / (ONE_USER + ONE_USER);

  const flush = async (ms = NO_DELAY_MS) => {
    await act(async () => { await vi.advanceTimersByTimeAsync(ms); });
  };

  const sentQuantities = (createMock: ReturnType<typeof vi.fn>) =>
    createMock.mock.calls.map((call) => {
      const cupt = call[2].requestedTerms.find((t: { id: string }) => t.id === 'term-cupt');
      return cupt.configuration.configurableUpfrontPricingTermConfiguration
        .dimensions[0].dimensionValue as number;
    });

  const arriveQuoted = async () => {
    const { marketplaceProcurementAPI } = await import(
      '../../../../../services/API/marketplace-procurement-api'
    );
    (marketplaceProcurementAPI.getOffer as ReturnType<typeof vi.fn>)
      .mockResolvedValue(CONTRACT_OFFER);
    const createMock = marketplaceProcurementAPI
      .createAgreementRequest as ReturnType<typeof vi.fn>;
    createMock.mockReset();
    createMock.mockResolvedValue({ agreementRequestId: 'ar-1' });

    const hook = renderHook(() => useProcurementWizard(), { wrapper });
    await act(async () => { await hook.result.current.handleSelectPurchaseOption(OPTION); });
    act(() => {
      hook.result.current.setAgreedToTerms(true);
      hook.result.current.setActiveStepIndex(STEP_GET_QUOTE);
    });
    // The step's first emitted config is quoted at once.
    act(() => { hook.result.current.setContractConfig(withUsers(ONE_USER)); });
    await flush();
    return { ...hook, createMock };
  };

  it('quotes only the final quantity after typing stops', async () => {
    vi.useFakeTimers();
    try {
      const { result, createMock } = await arriveQuoted();
      expect(sentQuantities(createMock)).toEqual([ONE_USER]);

      // Typing "50": the config passes through 5 on the way.
      act(() => { result.current.setContractConfig(withUsers(FIVE_USERS)); });
      await flush(HALF_WAY);
      act(() => { result.current.setContractConfig(withUsers(FIFTY_USERS)); });
      await flush(JUST_BEFORE);

      expect(sentQuantities(createMock)).toEqual([ONE_USER]);
      // No quote for the new quantity yet, so Next/Finish stay blocked.
      expect(result.current.hasCurrentQuote).toBe(false);

      await flush(ONE_USER);

      expect(sentQuantities(createMock)).toEqual([ONE_USER, FIFTY_USERS]);
      expect(result.current.hasCurrentQuote).toBe(true);
    } finally {
      vi.useRealTimers();
    }
  });

  it('still quotes a rate-card change immediately', async () => {
    vi.useFakeTimers();
    try {
      const { result, createMock } = await arriveQuoted();

      act(() => { result.current.setContractConfig(withUsers(ONE_USER, 'P24M')); });
      await flush();

      expect(createMock).toHaveBeenCalledTimes(ONE_USER + ONE_USER);
    } finally {
      vi.useRealTimers();
    }
  });
});

// ---------------------------------------------------------------------------
// FREE guard: an offer labelled FREE whose pricing terms charge something is
// never sent to AWS.
// ---------------------------------------------------------------------------
describe('useProcurementWizard FREE offer with a charge', () => {
  it('refuses to request a quote and reports why', async () => {
    const { marketplaceProcurementAPI } = await import(
      '../../../../../services/API/marketplace-procurement-api'
    );
    (marketplaceProcurementAPI.getOffer as ReturnType<typeof vi.fn>).mockResolvedValue({
      offerId: 'offer-not-free',
      pricingModelType: 'FREE',
      terms: [
        { termId: 'term-legal', termType: 'LegalTerm', rawTerm: {} },
        {
          termId: 'term-usage',
          termType: 'UsageBasedPricingTerm',
          rawTerm: { rateCards: [{ rateCard: [{ dimensionKey: 'm5.large', price: '0.10' }] }] },
        },
      ],
    });
    const createMock = marketplaceProcurementAPI
      .createAgreementRequest as ReturnType<typeof vi.fn>;
    createMock.mockReset();

    const { result } = renderHook(() => useProcurementWizard(), { wrapper });
    await act(async () => { await result.current.handleSelectPurchaseOption(OPTION); });
    await act(async () => {
      result.current.setAgreedToTerms(true);
      await tick();
    });

    expect(createMock).not.toHaveBeenCalled();
    expect(result.current.quoteBlockedMessage).toBe(i18n.freeOfferChargesError);
    expect(result.current.canProceedFromStep(STEP_REVIEW_TERMS)).toBe(false);
  });
});
