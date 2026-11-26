import { useState, useEffect, useRef } from 'react';
import { useRecoilValue } from 'recoil';
import {
  useListPurchaseOptions,
  useGetMarketplaceOffer,
  useCreateAgreementRequest,
  useAcceptAgreementRequest,
} from '../../../../../hooks/packaging';
import {
  MarketplaceOfferTerm,
  MarketplacePurchaseOption,
} from '../../../../../services/API/marketplace-procurement-api';
import { selectedProjectState } from '../../../../../state';
import {
  isFreeTierOffer,
  getWizardFlow,
  offerHasNoPricingTerm,
  isTwoStepFlow,
  filterTermsForRequestedPayload,
  contractConfigIdentity,
  FreeOfferChargesError,
  WizardFlow,
  ContractPricingConfig,
} from './offer-helpers';
import { isMissingContractEstimate } from './quote-money';

export type ProductTypeTab = 'AmiProduct' | 'ContainerProduct' | 'SaaSProduct';

// Wizard step indices. Exported so tests and the wizard component share the same names.
export const STEP_BROWSE_OFFERS = 0;
export const STEP_REVIEW_TERMS = 1;
export const STEP_GET_QUOTE = 2;
export const STEP_ACCEPT_CONFIRM = 3;

/**
 * Config identity used for every non-CONTRACT flow (FREE / USAGE / BYOL).
 *
 * Those flows have no buyer-supplied pricing configuration — the quote is
 * derived from the offer's own terms — so their quote can never be invalidated
 * by a config change. A constant keeps the staleness check uniform across all
 * flows instead of special-casing `null` to mean two different things.
 */
const NON_CONTRACT_CONFIG_IDENTITY = 'no-contract-config';

/**
 * Wait this long after the last quantity edit before requesting a CONTRACT
 * quote. Every quote is a real CreateAgreementRequest, so typing "50" must
 * not request one for 5 on the way.
 */
export const QUANTITY_QUOTE_DEBOUNCE_MS = 600;
const NO_DELAY_MS = 0;

/**
 * True when `next` differs from `previous` only in its dimension quantities —
 * same term, same rate card. That is the edit a buyer makes keystroke by
 * keystroke; choosing a different rate card is a single deliberate click and
 * is quoted immediately.
 */
const isQuantityOnlyChange = (
  previous: ContractPricingConfig | null,
  next: ContractPricingConfig | null,
): boolean => !!previous && !!next
  && previous.termId === next.termId
  && previous.selectorValue === next.selectorValue;

// Synthetic purchase option constructed when the wizard is entered from
// the listing-detail page. We only have an offerId at that point —
// the downstream flow only consumes `selectedOption.offerId`, so the rest
// is best-effort labelling.
const syntheticPurchaseOption = (offerId: string): MarketplacePurchaseOption => ({
  purchaseOptionId: offerId,
  purchaseOptionType: 'OFFER',
  purchaseOptionName: undefined,
  catalog: 'AWSMarketplace',
  offerId,
  productId: '',
  productName: undefined,
  sellerOfRecordDisplayName: undefined,
  availableFromTime: undefined,
  expirationTime: undefined,
  partOfOfferSet: false,
});

interface UseProcurementWizardOptions {
  /**
   * When set, the wizard skips step 1 (Browse offers) and starts on step 2
   * (Review terms) with this offerId already resolved. Used by the
   * listing-detail page — the user has already picked a product from the
   * public catalog, we don't need them to pick again from a private-offer
   * inbox that would show `[]` for a public product.
   */
  initialOfferId?: string | null,
}

/**
 * Should the wizard fire a quote request right now?
 *
 * Pure predicate extracted from the reconciliation effect to keep it under the
 * repo's complexity limit. `quotedConfigIdentity === null` is the "no live
 * quote" condition. Do not key this off `quote.data`: a quote already in state
 * must not stop a re-request after the buyer changes the configuration, or the
 * buyer could accept a quote priced for a configuration no longer on screen.
 */
const shouldFireQuote = ({
  twoStep,
  wizardFlow,
  activeStepIndex,
  contractConfig,
  agreedToTerms,
  hasOffer,
  hasSelectedOption,
  quotedConfigIdentity,
  quoteIsLoading,
  quoteHasError,
}: {
  twoStep: boolean,
  wizardFlow: WizardFlow,
  activeStepIndex: number,
  contractConfig: ContractPricingConfig | null,
  agreedToTerms: boolean,
  hasOffer: boolean,
  hasSelectedOption: boolean,
  quotedConfigIdentity: string | null,
  quoteIsLoading: boolean,
  quoteHasError: boolean,
}): boolean => {
  const isContractStep = wizardFlow === 'CONTRACT' && activeStepIndex === STEP_GET_QUOTE;
  const contractReady = isContractStep && contractConfig !== null;
  if (!twoStep && !contractReady) { return false; }
  return agreedToTerms
    && hasOffer
    && hasSelectedOption
    && quotedConfigIdentity === null
    && !quoteIsLoading
    && !quoteHasError;
};

export const useProcurementWizard = (options: UseProcurementWizardOptions = {}) => {
  const selectedProject = useRecoilValue(selectedProjectState);
  const projectId = selectedProject.projectId || '';
  const { initialOfferId } = options;

  const [activeStepIndex, setActiveStepIndex] = useState(
    initialOfferId ? STEP_REVIEW_TERMS : STEP_BROWSE_OFFERS,
  );
  const [productType, setProductType] = useState<ProductTypeTab>('AmiProduct');
  const [selectedOption, setSelectedOption] = useState<MarketplacePurchaseOption | null>(
    initialOfferId ? syntheticPurchaseOption(initialOfferId) : null,
  );
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [cancelConfirmVisible, setCancelConfirmVisible] = useState(false);
  // CONTRACT flow — buyer-supplied ConfigurableUpfrontPricingTerm
  // configuration (selectorValue + dimensions[]). Populated by the
  // Configure & Confirm Pricing step; forwarded to
  // filterTermsForRequestedPayload when we fire CreateAgreementRequest.
  //
  // `null` until the user picks a valid rate card + quantities;
  // canProceedFromStep(STEP_GET_QUOTE) gates Next on non-null.
  const [contractConfig, setContractConfig] = useState<ContractPricingConfig | null>(null);
  /**
   * Identity of the pricing configuration the quote currently in state (or
   * currently in flight) was priced for — `null` when no quote has been
   * requested yet.
   *
   * A quote is a priced commitment, so it is only valid for the configuration
   * it was requested with. Holding a quote without recording *which* config
   * produced it would allow this sequence:
   * configure → quote → change quantity or duration → accept the old quote.
   *
   * State rather than a ref because `canProceedFromStep` reads it during
   * render to gate Next/Finish. The reconciliation effect below also reads it,
   * and it is in that effect's dependency list.
   */
  const [quotedConfigIdentity, setQuotedConfigIdentity] = useState<string | null>(null);
  /** The CONTRACT configuration of the most recent quote request. */
  const lastRequestedConfigRef = useRef<ContractPricingConfig | null>(null);
  /**
   * Idempotency token sent as `clientToken` on CreateAgreementRequest, and the
   * offer + pricing configuration it belongs to.
   *
   * Without a token the backend derives one from (project, offer, proposal,
   * terms), so a buyer who cancels an agreement and later subscribes again
   * with the same configuration gets the old, cancelled request back. A token
   * is therefore minted per purchase attempt: a retry of the same
   * configuration reuses it, a different configuration or a new wizard
   * session (this ref starts empty on mount) gets a new one.
   */
  const clientTokenRef = useRef<{ key: string, token: string } | null>(null);
  /**
   * Set when the wizard refused to build a request at all (a FREE offer whose
   * pricing terms charge something). Blocks auto-fire until the quote state
   * is reset, e.g. by picking another offer.
   */
  const [quoteBlockedError, setQuoteBlockedError] = useState<FreeOfferChargesError | null>(null);
  // Guard so we only auto-fetch the initial offer once. Without this a
  // caller-side re-render (e.g. project switch) would refire `offer.run`.
  const [initialOfferFetched, setInitialOfferFetched] = useState(false);

  const purchaseOptions = useListPurchaseOptions();
  const offer = useGetMarketplaceOffer({ projectId });
  const quote = useCreateAgreementRequest({ projectId });
  // Account-scoped, unlike the offer/quote hooks above: accepting commits the
  // buyer account, not a project.
  const acceptance = useAcceptAgreementRequest();

  // Auto-fetch the offer detail on first render when we were handed an
  // initialOfferId. Fired via useEffect so we don't mutate during render.
  useEffect(() => {
    if (initialOfferId && !initialOfferFetched) {
      setInitialOfferFetched(true);
      // Fire and forget — the wizard renders a loading/error state while it resolves.
      offer.run(initialOfferId).catch(() => { /* handled by offer.error */ });
    }
  }, [initialOfferId, initialOfferFetched, offer]);

  /**
   * True when the resolved offer's ``pricingModelType`` is ``FREE``. For
   * free-tier offers the wizard hides the Get Quote step entirely — a
   * $0 offer has no meaningful quote to review, so we auto-fire the
   * quote request behind the scenes and let the user skip straight to
   * Accept & Confirm.
   */
  const isFreeTier = isFreeTierOffer(offer.data);

  /**
   * The wizard flow inferred from the resolved offer's pricing model
   * (FREE / USAGE / BYOL / CONTRACT). Drives step visibility and CTA
   * labelling.
   */
  const wizardFlow: WizardFlow = getWizardFlow(offer.data);

  /**
   * True when the resolved offer carries no pricing term, so there is no
   * agreement to create and the AMI is imported directly instead. Only
   * meaningful once the offer has resolved; `false` while it loads, so the
   * wizard shows its normal steps rather than flashing the wrong screen.
   */
  const directImportAvailable = offerHasNoPricingTerm(offer.data);

  /**
   * True when the current flow uses a 2-step wizard (Review → Accept).
   * FREE / USAGE / BYOL are 2-step; CONTRACT is 3-step.
   */
  const twoStep = isTwoStepFlow(wizardFlow);

  /**
   * Identity of the pricing configuration a quote requested *right now* would
   * be priced for.
   *
   * Only the CONTRACT flow has a buyer-supplied configuration. FREE / USAGE /
   * BYOL quotes are derived purely from the offer's own terms, so they share a
   * single constant identity — `contractConfig` is irrelevant to their price
   * and must not be allowed to invalidate their quote.
   */
  const currentConfigIdentity = wizardFlow === 'CONTRACT'
    ? contractConfigIdentity(contractConfig)
    : NON_CONTRACT_CONFIG_IDENTITY;

  /**
   * Discard the quote, any acceptance result, and the record of what the quote
   * was priced for.
   *
   * All three must move together. `quote.reset()` on its own leaves
   * `quotedConfigIdentity` pointing at a quote that no longer exists, which
   * suppresses the auto-fire effect and strands the wizard with no quote and no
   * way to request one. Exposed so the component can never reset only part of
   * it.
   */
  const resetQuoteState = () => {
    quote.reset();
    acceptance.reset();
    setQuotedConfigIdentity(null);
    setQuoteBlockedError(null);
  };

  /** The client token for a quote on this offer + configuration. */
  const clientTokenFor = (offerId: string, configIdentity: string): string => {
    const key = `${offerId}|${configIdentity}`;
    if (clientTokenRef.current?.key !== key) {
      clientTokenRef.current = { key, token: crypto.randomUUID() };
    }
    return clientTokenRef.current.token;
  };

  /**
   * Fire CreateAgreementRequest for the configuration on screen.
   *
   * Stamps `quotedConfigIdentity` before awaiting: stamping afterwards would
   * let two renders both see `null` and fire two CreateAgreementRequest calls
   * for one configuration, and a config change during the request would not be
   * detected as a supersede (`quote.run` discards a superseded response). A
   * quote costs nothing (only accepting one does), but each call creates a
   * real agreement request in the buyer account, so duplicates are avoided.
   */
  const requestQuoteNow = async (offerId: string, terms: MarketplaceOfferTerm[]) => {
    let requestedTerms;
    try {
      requestedTerms = filterTermsForRequestedPayload(
        terms,
        wizardFlow,
        contractConfig || undefined,
      );
    } catch (e) {
      if (e instanceof FreeOfferChargesError) {
        setQuoteBlockedError(e);
        return null;
      }
      throw e;
    }
    lastRequestedConfigRef.current = contractConfig;
    setQuotedConfigIdentity(currentConfigIdentity);
    return quote.run(offerId, {
      requestedTerms,
      clientToken: clientTokenFor(offerId, currentConfigIdentity),
    });
  };

  // Keep the quote in sync with the pricing configuration, then auto-fire when
  // one is needed.
  //
  // (1) Invalidation. A quote is only valid for the configuration it was
  //     priced with. If the buyer changes the rate card or a quantity after a
  //     quote exists — or while one is still in flight — that quote is stale
  //     and is thrown away. Without this the buyer could configure, quote,
  //     change the quantity or duration, and then accept the *old* quote: a
  //     real agreement at a price that does not match what the final step
  //     displays. `quote.reset()` additionally invalidates the in-flight
  //     request inside the hook, so a late response for the abandoned config
  //     cannot land afterwards.
  //
  // (2) Auto-fire:
  //   (a) for 2-step flows (FREE / USAGE / BYOL) as soon as terms are
  //       agreed — the user is about to hop from Review Terms straight
  //       to Accept & Confirm, and Accept needs a valid quote in state.
  //   (b) for CONTRACT (3-step) when the user reaches the Configure &
  //       Confirm Pricing step AND has picked a valid rate card
  //       configuration. The quote is fired with the buyer's chosen
  //       selectorValue + dimensions attached, so the returned
  //       estimatedAgreementValue matches what the user just picked.
  //
  // `quotedConfigIdentity === null` is the "no live quote" condition. A
  // `!quote.data` guard would be wrong here: it stops a refetch precisely when
  // a quote already exists, which is the case a configuration change needs to
  // re-request.
  useEffect(() => {
    if (
      quotedConfigIdentity !== null
      && quotedConfigIdentity !== currentConfigIdentity
    ) {
      // Stale. Drop it and let the next render decide whether to re-fire for
      // the new configuration.
      resetQuoteState();
      return undefined;
    }

    const fireNow = shouldFireQuote({
      twoStep,
      wizardFlow,
      activeStepIndex,
      contractConfig,
      agreedToTerms,
      hasOffer: !!offer.data,
      hasSelectedOption: !!selectedOption,
      quotedConfigIdentity,
      quoteIsLoading: quote.isLoading,
      quoteHasError: !!quote.error || !!quoteBlockedError,
    });
    if (!fireNow || !offer.data || !selectedOption) { return undefined; }

    const { offerId } = selectedOption;
    const terms = offer.data.terms || [];
    const fire = () => {
      requestQuoteNow(offerId, terms).catch(() => {
        /* surfaced via quote.error on the current step */
      });
    };
    // Quantity edits are debounced: each keystroke yields a new valid config,
    // and each config would otherwise be a separate CreateAgreementRequest.
    // Quotes are free, but each one is a real agreement request in the buyer
    // account. The cleanup cancels the pending request when the buyer types
    // again; the invalidation above has already dropped any quote for the old
    // quantity.
    const delay = isQuantityOnlyChange(lastRequestedConfigRef.current, contractConfig)
      ? QUANTITY_QUOTE_DEBOUNCE_MS
      : NO_DELAY_MS;
    if (delay === NO_DELAY_MS) {
      fire();
      return undefined;
    }
    const timer = setTimeout(fire, delay);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    twoStep,
    agreedToTerms,
    offer.data,
    selectedOption,
    activeStepIndex,
    wizardFlow,
    contractConfig,
    currentConfigIdentity,
    quotedConfigIdentity,
  ]);

  /**
   * True when we hold a quote AND it was priced for the configuration
   * currently on screen.
   *
   * Every quote gate reads this. `quote.data !== null` alone is not a safe gate: between the buyer editing a
   * quantity and the invalidation effect running, `quote.data` still holds the
   * previous configuration's quote. Gating on that would let Finish through for
   * a price the final step no longer displays.
   */
  const hasCurrentQuote = quote.data !== null
    && quotedConfigIdentity === currentConfigIdentity;

  /** True for a held CONTRACT quote that AWS returned without an estimated total. */
  const hasMissingContractEstimate = quote.data !== null
    && isMissingContractEstimate(quote.data.estimatedAgreementValue, wizardFlow);

  /**
   * Finish needs a quote for the configuration on screen, and a CONTRACT
   * quote must carry an estimated total: a contract has a fixed price, so a
   * buyer must not commit to one whose total was never shown.
   */
  const canFinish = hasCurrentQuote && !hasMissingContractEstimate;

  const canProceedFromStep = (stepIdx: number): boolean => {
    switch (stepIdx) {
      case STEP_BROWSE_OFFERS:
        return productType === 'AmiProduct' && selectedOption !== null;
      case STEP_REVIEW_TERMS:
        // For 2-step flows (FREE / USAGE / BYOL) we require quote.data too,
        // because we're going to hop straight to Accept & Confirm and that
        // step needs a quote in state to render the "Finish" action. The
        // useEffect above auto-fires the quote request as soon as the terms
        // are agreed, so this is a natural gate rather than user friction.
        if (twoStep) {
          return offer.data !== null && agreedToTerms && hasCurrentQuote;
        }
        return offer.data !== null && agreedToTerms;
      case STEP_GET_QUOTE:
        // CONTRACT flow: this step is the Configure & Confirm Pricing step.
        // Require a completed contractConfig AND a quote priced for THAT
        // config before advancing. 2-step flows never reach here
        // (STEP_GET_QUOTE is hidden).
        if (wizardFlow === 'CONTRACT') {
          return contractConfig !== null && hasCurrentQuote;
        }
        return hasCurrentQuote;
      case STEP_ACCEPT_CONFIRM:
      // Finish will drive the accept call itself (see `onSubmit` in procurement-wizard.tsx).
        return canFinish;
      default:
        return true;
    }
  };

  const handleSelectPurchaseOption = async (option: MarketplacePurchaseOption) => {
    setSelectedOption(option);
    // Switching offers invalidates any downstream state — the quote and acceptance were
    // scoped to the *previous* offer, so keeping them around would let the user "Finish"
    // the wizard using stale data.
    resetQuoteState();
    // The previous offer's rate cards don't exist on the new offer, so a
    // carried-over config would point at a termId the new offer never declares.
    setContractConfig(null);
    setAgreedToTerms(false);
    // Prefetch offer for step 2.
    await offer.run(option.offerId);
  };

  const handleRequestQuote = async () => {
    if (!selectedOption || !offer.data) { return; }
    await requestQuoteNow(selectedOption.offerId, offer.data.terms || []);
  };

  /**
   * Start over with a fresh quote after Marketplace rejected the accept (for
   * example an expired quote). Discards the client token too: reusing it
   * would return the rejected request again.
   */
  const handleRequestNewQuote = () => {
    clientTokenRef.current = null;
    resetQuoteState();
    setActiveStepIndex(STEP_GET_QUOTE);
  };

  const handleAcceptQuote = async () => {
    if (!quote.data) { return null; }
    // Defence in depth: never accept a quote priced for a configuration the
    // buyer has since changed. The wizard's Finish handler already checks
    // `canProceedFromStep`, but acceptance is the irreversible, billable step
    // and should not depend on a caller remembering to gate it.
    if (quotedConfigIdentity !== currentConfigIdentity) { return null; }
    // Same reasoning: never accept a contract whose total the buyer has not seen.
    if (hasMissingContractEstimate) { return null; }
    return acceptance.run(quote.data.agreementRequestId);
  };

  /**
   * Reset state that becomes stale when the user navigates backward past step 3.
   * The wizard's `onNavigate` calls this so a user can re-do step 3 (get a new quote)
   * after e.g. a rejected accept.
   *
   * Clears the client token as well. Stepping back means the buyer wants a
   * fresh quote; reusing the token would make AWS return the previous agreement
   * request again, including one Marketplace already rejected.
   */
  const handleBackwardNavigation = (fromStep: number, toStep: number) => {
    if (toStep < fromStep && fromStep >= STEP_GET_QUOTE) {
      // Discard the previous quote + any acceptance result. `agreedToTerms` stays because
      // stepping back to step 2 shouldn't force the user to re-tick the checkbox.
      // For CONTRACT, keep contractConfig — the user may want to tweak on the same step
      // rather than start over — but reset the quote so the Configure step re-fires with
      // the current config on the next forward navigation.
      clientTokenRef.current = null;
      resetQuoteState();
    }
  };

  return {
    projectId,
    activeStepIndex,
    setActiveStepIndex,
    productType,
    setProductType,
    selectedOption,
    setSelectedOption,
    agreedToTerms,
    setAgreedToTerms,
    cancelConfirmVisible,
    setCancelConfirmVisible,
    /**
     * True when the wizard was launched with an initialOfferId. The wizard
     * component uses this to hide step 1 from the visible steps array —
     * users entering from the public-catalog browse flow have already picked a
     * product and don't need to re-browse.
     */
    startedFromInitialOffer: !!initialOfferId,

    /**
     * True when the resolved offer is FREE. The Review Terms step
     * uses this to render the "Free tier" badge + EC2-compute
     * disclaimer.
     */
    isFreeTier,

    /**
     * The pricing-model-aware wizard flow. Drives CTA labelling on the listing
     * detail page and (via ``twoStep``) step visibility.
     */
    wizardFlow,

    /**
     * True when the offer has no pricing term, so there is no agreement to
     * create and the wizard offers a direct import of the AMI instead of the
     * subscribe steps.
     */
    directImportAvailable,

    /**
     * True when the current flow uses a 2-step wizard (Review →
     * Accept). The wizard component uses this to filter STEP_GET_QUOTE
     * out of the visible steps array.
     */
    twoStep,

    purchaseOptions,
    offer,
    quote,
    acceptance,

    /**
     * Why no quote request was sent, when the wizard refused to build one.
     * `null` otherwise. Shown on the step that would have fired the quote.
     */
    quoteBlockedError,
    quoteBlockedMessage: quoteBlockedError?.message ?? null,
    /** The error the Get Quote step shows: a failed or a refused request. */
    quoteStepError: quote.error ?? quoteBlockedError,

    /**
     * CONTRACT flow only: the buyer-supplied ConfigurableUpfrontPricingTerm
     * configuration produced by the Configure & Confirm Pricing step.
     * `null` until the user makes a valid selection.
     */
    contractConfig,
    setContractConfig,

    /**
     * True when a quote is held AND it was priced for the configuration
     * currently on screen. The only safe signal that there is a quote worth
     * accepting — prefer it over `quote.data !== null` in any new call site.
     */
    hasCurrentQuote,

    /**
     * Discard the quote, the acceptance result, and the record of which
     * configuration the quote was priced for, as one atomic step. Use this
     * instead of calling `quote.reset()` directly: resetting the quote without
     * clearing the stamped identity leaves the wizard unable to re-request one.
     */
    resetQuoteState,

    canProceedFromStep,
    handleSelectPurchaseOption,
    handleRequestQuote,
    handleRequestNewQuote,
    handleAcceptQuote,
    handleBackwardNavigation,
  };
};


export type ProcurementWizardLogic = ReturnType<typeof useProcurementWizard>;
