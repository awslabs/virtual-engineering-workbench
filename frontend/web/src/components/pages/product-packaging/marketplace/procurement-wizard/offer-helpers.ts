// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Helpers for interpreting AWS Marketplace offer + term data structures.
//
// AWS's Marketplace Discovery API surfaces offers with these top-level
// pricing model types (see ``get_offer.pricingModel.pricingModelType``):
//
// - ``FREE``     — public free offers (Ubuntu, Amazon Linux, etc.)
// - ``USAGE``    — hourly / usage-metered pricing
// - ``CONTRACT`` — up-front paid contracts
// - ``BYOL``     — bring-your-own-license
// - ``OTHER``    — anything else AWS hasn't formalized yet
//
// For free-tier offers, the procurement flow is materially different:
// there's no cost quote to review, so the Get Quote wizard step is
// meaningless friction. This module encapsulates the detection so the
// UI can branch cleanly (Review Terms → skip Get Quote → Accept).

import {
  GetMarketplaceOfferResponse,
  MarketplaceOfferTerm,
} from '../../../../../services/API/marketplace-procurement-api';
import { i18n } from './procurement-wizard.translations';

/**
 * True when the offer's pricing model is FREE according to AWS. This is
 * the authoritative signal — no inference from rate cards required.
 *
 * NOTE: A FREE Marketplace offer still incurs EC2 compute costs — AWS
 * charges you for the instance the AMI runs on, only the software
 * license fee is $0. The wizard must make that disclaimer clear.
 */
export const isFreeTierOffer = (offer: GetMarketplaceOfferResponse | null): boolean => {
  if (!offer) { return false; }
  return offer.pricingModelType === 'FREE';
};

/**
 * True when the offer's pricing model is BYOL — "Bring Your Own License".
 * Used by the Review Terms step to render an up-front info alert so the
 * user understands that (a) no licence is collected here, and (b) the
 * licence must be obtained separately from the seller.
 *
 * BYOL is a valid, complete AWS Marketplace pricing model — accepting
 * the agreement only grants entitlement to launch the AMI. The software
 * inside performs its own licence check at boot; AWS is not involved in
 * licence delivery or billing.
 */
export const isByolOffer = (offer: GetMarketplaceOfferResponse | null): boolean => {
  if (!offer) { return false; }
  return offer.pricingModelType === 'BYOL';
};

/**
 * The Marketplace SellerProfileId AWS uses when it acts as Seller of
 * Record for AMIs it publishes itself — Microsoft Windows Server, some
 * RHEL SKUs, some SUSE SKUs, etc.
 */
const EMPTY = 0;
const FIRST_ITEM_INDEX = 0;
const SINGLE_PRICE = 1;

export const AWS_SELLER_PROFILE_ID = 'e6a5002c-6dd0-4d1e-8196-0a1d1857229b';

/**
 * True when AWS itself is the Seller of Record for the offer.
 *
 * Informational only — use it to label an offer as sold by AWS, not to pick
 * a flow. Whether an offer can be subscribed to depends on its terms, not on
 * who sells it: AWS-sold offers that carry a pricing term subscribe through
 * the buyer-side agreement API like any other. See `offerHasNoPricingTerm`.
 */
export const isAwsSoldOffer = (offer: GetMarketplaceOfferResponse | null): boolean => {
  if (!offer) { return false; }
  return offer.sellerOfRecordProfileId === AWS_SELLER_PROFILE_ID;
};

/**
 * Term types AWS Marketplace classifies as pricing. An offer carrying none
 * of them has no agreement to create: `CreateAgreementRequest` rejects it,
 * because the licence is granted implicitly by EC2 at `RunInstances` time.
 * These offers carry only metadata terms such as `LegalTerm` and
 * `SupportTerm`.
 */
const PRICING_TERM_TYPES = new Set([
  'UsageBasedPricingTerm',
  'FixedUpfrontPricingTerm',
  'ConfigurableUpfrontPricingTerm',
  'RecurringPaymentTerm',
  'FreeTrialTerm',
]);

/**
 * True when the offer carries no pricing term, which means there is nothing
 * to subscribe to and the AMI should be imported directly instead.
 *
 * This is the authoritative distinguisher between "the licence lives in the
 * EC2 billing code; import the AMI" and "a real agreement is required; run
 * the procurement wizard". It is deliberately not the seller id: a
 * transactable offer always carries a pricing term even when the software
 * fee is $0.
 *
 * Returns `false` while the offer is still loading (`null`), so callers must
 * wait for the offer before branching on this signal.
 */
export const offerHasNoPricingTerm = (offer: GetMarketplaceOfferResponse | null): boolean => {
  if (!offer) { return false; }
  return !(offer.terms || []).some((term) => PRICING_TERM_TYPES.has(term.termType));
};

/**
 * The wizard flow that best matches an offer's pricing model.
 *
 * - ``FREE``           — 2-step wizard, no Get Quote
 * - ``USAGE``          — 2-step wizard, no Get Quote
 * - ``BYOL``           — 2-step wizard, no Get Quote
 * - ``CONTRACT``       — 3-step wizard with "Configure & confirm pricing"
 * - ``PRIVATE_OFFER``  — same shape as underlying pricing model, badge added
 *
 * Every offer gets a flow regardless of seller. An offer with no pricing
 * term never reaches these steps: the wizard renders the direct-import panel
 * for it instead, keyed off `offerHasNoPricingTerm`.
 *
 * The catch-all bucket for anything unrecognized falls through to
 * ``USAGE``, which is the safest 2-step default (no Get Quote,
 * auto-fires the agreement request).
 */
export type WizardFlow = 'FREE' | 'USAGE' | 'CONTRACT' | 'BYOL' | 'PRIVATE_OFFER';

export const getWizardFlow = (offer: GetMarketplaceOfferResponse | null): WizardFlow => {
  if (!offer) { return 'USAGE'; }
  switch (offer.pricingModelType) {
    case 'FREE': return 'FREE';
    case 'BYOL': return 'BYOL';
    case 'CONTRACT': return 'CONTRACT';
    // 'USAGE' + anything unknown (defensive)
    default: return 'USAGE';
  }
};

/**
 * True when the given wizard flow uses a 2-step layout (Review →
 * Accept, no middle "Get Quote" or "Configure & confirm" step).
 * FREE, USAGE, and BYOL are 2-step; CONTRACT is 3-step.
 */
export const isTwoStepFlow = (flow: WizardFlow): boolean =>
  flow === 'FREE' || flow === 'USAGE' || flow === 'BYOL';

/**
 * Return the best CTA label for a listing based on its declared pricing
 * models.
 *
 * Every AMI listing routes to the procurement wizard, whoever sells it. The
 * wizard reads the offer's terms and, for an offer with no pricing term,
 * offers a direct import instead of the subscribe steps — so the label here
 * describes the pricing model only.
 *
 *   FREE  →  "Subscribe"
 *   BYOL  →  "Subscribe with own license"
 *   USAGE →  "Subscribe"
 *   CONTRACT → "Buy contract"
 *   otherwise → "Get this product" (fallback)
 *
 * FREE and USAGE deliberately share the label. They are the same action:
 * `isTwoStepFlow` treats both identically, both fire CreateAgreementRequest
 * then AcceptAgreementRequest, and both end in a real agreement plus a
 * licence grant. A free product still has to be subscribed to before it can
 * be used, exactly like pay-as-you-go. The $0 software fee is communicated by
 * the Free tier badge and alert on Review Terms, not by weakening the verb.
 *
 * When a listing has multiple pricing models, we pick the "friendliest"
 * one in the order FREE > BYOL > USAGE > CONTRACT.
 */
export const getListingCtaLabel = (
  pricingModelTypes: readonly string[],
): string => {
  const set = new Set(pricingModelTypes);
  if (set.has('FREE')) { return 'Subscribe'; }
  if (set.has('BYOL')) { return 'Subscribe with own license'; }
  if (set.has('USAGE')) { return 'Subscribe'; }
  if (set.has('CONTRACT')) { return 'Buy contract'; }
  return 'Get this product';
};

/**
 * Return the friendliest human-readable name for an offer.
 *
 * Preference order:
 * 1. Explicit ``offerName`` when AWS provides one.
 * 2. ``associatedProducts[0].productName`` — the product name is what
 *    the user actually recognised on the browse tile.
 * 3. Fall back to the raw ``offerId`` so we never render an empty
 *    field, but this path should be rare.
 *
 * The raw 25-char ``offerId`` (e.g. ``2wqkpek696qhdeo7lbbjncqli``) is
 * unreadable to end users, so it is only the last resort.
 */
export const getFriendlyOfferName = (offer: GetMarketplaceOfferResponse): string => {
  if (offer.offerName && offer.offerName.trim().length > EMPTY) {
    return offer.offerName;
  }
  const firstProduct = (offer.associatedProducts || [])[0];
  if (firstProduct?.productName) {
    return `${firstProduct.productName} (public offer)`;
  }
  return offer.offerId;
};

/**
 * Extract a friendly display label for a single offer term. Used by the
 * Review Terms step to render a term summary without exposing internal
 * IDs or JSON to the user.
 */
export const getTermTypeLabel = (termType: string): string => {
  switch (termType) {
    case 'LegalTerm':
      return 'Legal terms';
    case 'SupportTerm':
      return 'Support';
    case 'UsageBasedPricingTerm':
      return 'Usage-based pricing';
    case 'FixedUpfrontPricingTerm':
      return 'Upfront pricing';
    case 'ConfigurableUpfrontPricingTerm':
      return 'Configurable upfront pricing';
    case 'RecurringPaymentTerm':
      return 'Recurring payment';
    case 'FreeTrialTerm':
      return 'Free trial';
    case 'PaymentScheduleTerm':
      return 'Payment schedule';
    case 'RenewalTerm':
      return 'Renewal';
    case 'ValidityTerm':
      return 'Validity period';
    default:
      // Convert PascalCase to spaced words for anything unknown.
      // "SomeNewTerm" → "Some New Term"
      return termType
        .replace(/(?<upper>[A-Z])/gu, ' $<upper>')
        .replace(/Term$/u, '')
        .trim() || termType;
  }
};

/**
 * Legal document metadata extracted from a LegalTerm's ``rawTerm`` payload.
 */
export interface LegalDocument {
  type: string,
  displayName: string,
  url: string | null,
  version: string | null,
}

/**
 * Best-effort mapping from a raw AWS document type to a user-friendly
 * display name. AWS document types are relatively stable but not
 * exhaustive; unknown types fall through to a title-cased fallback.
 */
const documentDisplayName = (docType: string | undefined): string => {
  if (!docType) { return 'License document'; }
  switch (docType) {
    case 'CustomEula':
    case 'StandardEula':
      return 'End-User License Agreement';
    case 'CustomDsa':
    case 'StandardDsa':
      return 'Data Sharing Agreement';
    case 'TermsOfService':
      return 'Terms of Service';
    case 'PrivacyPolicy':
      return 'Privacy Policy';
    default:
      // "SomeDocumentType" → "Some Document Type"
      return docType.replace(/(?<upper>[A-Z])/gu, ' $<upper>').trim();
  }
};

/**
 * A term's raw AWS payload. The API types it as a bare object because its
 * shape depends on the term type, so each reader narrows the fields it uses.
 */
const rawTermOf = (term: MarketplaceOfferTerm): Record<string, unknown> =>
  (term.rawTerm ?? {}) as Record<string, unknown>;

/**
 * Extract the list of legal documents from a LegalTerm's ``rawTerm``
 * payload. Returns an empty array for non-LegalTerm inputs or for
 * malformed payloads.
 */
export const extractLegalDocuments = (term: MarketplaceOfferTerm): LegalDocument[] => {
  if (term.termType !== 'LegalTerm') { return []; }
  const documents = rawTermOf(term).documents;
  if (!Array.isArray(documents)) { return []; }
  return documents.map((d): LegalDocument => {
    const doc = d as Record<string, unknown>;
    const docType = typeof doc.type === 'string' ? doc.type : undefined;
    const url = typeof doc.url === 'string' ? doc.url : null;
    const version = typeof doc.version === 'string' ? doc.version : null;
    return {
      type: docType || 'Unknown',
      displayName: documentDisplayName(docType),
      url,
      version,
    };
  });
};

/**
 * Extract the refund policy text from a SupportTerm. Returns an empty
 * string for non-SupportTerm inputs or missing/malformed data.
 */
export const extractRefundPolicy = (term: MarketplaceOfferTerm): string => {
  if (term.termType !== 'SupportTerm') { return ''; }
  const policy = rawTermOf(term).refundPolicy;
  return typeof policy === 'string' ? policy.trim() : '';
};

// -----------------------------------------------------------------------------
// requestedTerms construction for CreateAgreementRequest
// -----------------------------------------------------------------------------
//
// AWS Marketplace Agreement API rules for which terms to include in a
// CreateAgreementRequest, per pricing model:
// https://docs.aws.amazon.com/marketplace/latest/developerguide/
//   work-with-agreement-api-buyer.html#construct-requested-terms
//
// - Mandatory (always include when present):
//     LegalTerm, SupportTerm, ValidityTerm, RenewalTerm
// - FREE:      same as USAGE (a free offer is a usage offer at $0 rates).
// - USAGE:     mandatory + UsageBasedPricingTerm + RecurringPaymentTerm.
//              DO NOT include ConfigurableUpfrontPricingTerm /
//              FixedUpfrontPricingTerm / PaymentScheduleTerm — those belong
//              in a separate second agreement if the buyer wants an annual
//              contract discount on top of pay-as-you-go.
// - CONTRACT:  all terms returned by GetOfferTerms. Configurable term must
//              carry a `configuration` payload (see below).
// - BYOL:      mandatory + ByolPricingTerm.
//
// Certain term types additionally require a `configuration` payload:
// - ConfigurableUpfrontPricingTerm — `configuration.configurableUpfrontPricingTermConfiguration`
//     with `selectorValue` + `dimensions[]`. Buyer supplies it on the
//     Configure & Confirm Pricing step.
// - RenewalTerm — `configuration.renewalTermConfiguration.enableAutoRenew`.
//     We default to `false` — buyers can amend after acceptance to enable.
// - VariablePaymentTerm — approval strategy. Not supported.

const MANDATORY_TERM_TYPES = new Set([
  'LegalTerm',
  'SupportTerm',
  'ValidityTerm',
  'RenewalTerm',
  // FreeTrialPricingTerm is mandatory when present (e.g. offer
  // e9yfvyj3uag5uo5j2hjikv74n, Palo Alto VM-Series Bundle 2): omitting it
  // yields "All mandatory
  // terms must be accepted to create an Agreement." AWS's docs describe
  // it as "can only be accepted once per product" — if the buyer has
  // already consumed the free trial, CreateAgreementRequest returns a
  // distinct error which we surface as-is.
  'FreeTrialPricingTerm',
]);

const USAGE_PRICING_TERM_TYPES = new Set([
  'UsageBasedPricingTerm',
  'RecurringPaymentTerm',
]);

const BYOL_PRICING_TERM_TYPES = new Set([
  'ByolPricingTerm',
]);

const CONTRACT_ONLY_TERM_TYPES = new Set([
  'ConfigurableUpfrontPricingTerm',
  'FixedUpfrontPricingTerm',
  'PaymentScheduleTerm',
]);

/**
 * A `requestedTerms[]` entry for AWS's `CreateAgreementRequest` API. The
 * `id` field is always required; `configuration` is only present for a
 * few specific term types (see AWS docs above).
 */
export interface RequestedTermPayload {
  id: string,
  configuration?: Record<string, unknown>,
}

/**
 * Buyer-supplied configuration for a `ConfigurableUpfrontPricingTerm`
 * (CONTRACT flow). Passed into `filterTermsForRequestedPayload` so the
 * wizard's Configure & Confirm Pricing step can produce a
 * complete `CreateAgreementRequest` payload.
 *
 * `termId` — the ConfigurableUpfrontPricingTerm's termId, so the filter
 *   attaches the configuration to the correct term (an offer could in
 *   principle have multiple such terms, though we've never seen it in
 *   the wild).
 * `selectorValue` — the chosen rate card's `selector.value`. Usually an
 *   ISO 8601 period like `P12M`, but the field is defined as a free
 *   string by AWS so we forward it verbatim.
 * `dimensions` — buyer's per-dimension quantity choices. At least one
 *   dimension is required (AWS's
 *   `ConfigurableUpfrontPricingTermConfiguration.dimensions` requires
 *   min 1 item). When the rate card's constraints set
 *   `quantityConfiguration=Disallowed`, callers should still supply
 *   one entry per dimension with quantity=1.
 */
export interface ContractPricingConfig {
  termId: string,
  selectorValue: string,
  dimensions: Array<{ dimensionKey: string, dimensionValue: number }>,
}

/**
 * Stable identity string for a pricing configuration — everything in it that
 * changes the *price* of the resulting quote.
 *
 * Used by the wizard to decide whether a quote it already holds was priced for
 * the configuration currently on screen. The Configure & Confirm Pricing step
 * re-emits a brand-new `ContractPricingConfig` object on every keystroke and
 * re-render, so object identity (`!==`) is useless for this: it reports a
 * change when the buyer changed nothing, which would re-fire a
 * CreateAgreementRequest on every render.
 *
 * `dimensions` are sorted by `dimensionKey` because the step builds that array
 * by mapping over the rate card's dimension list, and a card re-parse can
 * reorder it without the buyer touching anything. Same reasoning as the
 * backend's idempotency key, which canonicalises term order for exactly this
 * reason.
 *
 * `null` (no configuration chosen) gets its own sentinel rather than `''`, so
 * "nothing selected" is distinguishable from a config whose fields are all
 * empty strings.
 */
export const contractConfigIdentity = (
  config: ContractPricingConfig | null | undefined,
): string => {
  if (!config) { return 'none'; }
  const dims = [...config.dimensions]
    .sort((a, b) => a.dimensionKey.localeCompare(b.dimensionKey))
    .map((d) => `${d.dimensionKey}=${d.dimensionValue}`)
    .join(',');
  return `${config.termId}|${config.selectorValue}|${dims}`;
};

/**
 * Raised instead of building a FREE request whose pricing terms carry a
 * non-zero (or unreadable) rate.
 *
 * The FREE flow sends the same pricing terms as USAGE, because a free offer
 * is a usage offer whose rates are all zero. If the offer is labelled FREE
 * but a rate is not zero, accepting would subscribe the buyer to a paid
 * product through a flow that tells them it is free, so no request is made.
 */
export class FreeOfferChargesError extends Error {
  termId: string;

  constructor(termId: string) {
    super(i18n.freeOfferChargesError);
    this.name = 'FreeOfferChargesError';
    this.termId = termId;
  }
}

const ZERO_PRICE = 0;

/** True only for a price that parses to exactly zero ("0", "0.00", 0). */
const isZeroPrice = (price: unknown): boolean => {
  if (typeof price !== 'string' && typeof price !== 'number') { return false; }
  if (String(price).trim() === '') { return false; }
  return Number(price) === ZERO_PRICE;
};

/**
 * Every rate a pricing term would charge, or `null` when the term carries
 * rates that cannot be read. Non-pricing terms (legal, support, ...) have no
 * rates and return `[]`.
 */
const ratesOf = (term: MarketplaceOfferTerm): unknown[] | null => {
  const raw = rawTermOf(term);
  if (term.termType === 'UsageBasedPricingTerm') {
    const rateCards = raw.rateCards;
    if (!Array.isArray(rateCards)) { return null; }
    const rates: unknown[] = [];
    for (const card of rateCards) {
      const inner = (card as Record<string, unknown> | null)?.rateCard;
      if (!Array.isArray(inner)) { return null; }
      inner.forEach((entry) => rates.push((entry as Record<string, unknown> | null)?.price));
    }
    return rates;
  }
  if (term.termType === 'RecurringPaymentTerm') {
    return [raw.price];
  }
  return [];
};

/** True when the term charges nothing: every rate it carries is zero. */
const chargesNothing = (term: MarketplaceOfferTerm): boolean => {
  const rates = ratesOf(term);
  return rates !== null && rates.every(isZeroPrice);
};

/**
 * Build the `requestedTerms` array for a `CreateAgreementRequest`
 * given the flow the user is in and the offer's terms.
 *
 * Enforces the AWS-documented "which terms to include" rules per pricing
 * model, and attaches the required `configuration` payload for
 * `RenewalTerm` (we default `enableAutoRenew` to `false`).
 *
 * `ConfigurableUpfrontPricingTerm` carries the buyer's `contractConfig`
 * (selector value + dimensions) when its term id matches; without a
 * matching config only the term id is sent and AWS rejects the request.
 * The USAGE flow drops the term entirely so pay-as-you-go works.
 *
 * Throws `FreeOfferChargesError` for the FREE flow when a pricing term
 * being sent has a non-zero or unreadable rate.
 */
export const filterTermsForRequestedPayload = (
  terms: readonly MarketplaceOfferTerm[],
  flow: WizardFlow,
  contractConfig?: ContractPricingConfig,
): RequestedTermPayload[] => {
  const filtered = terms.filter((term) => {
    // Always include mandatory metadata terms.
    if (MANDATORY_TERM_TYPES.has(term.termType)) { return true; }

    switch (flow) {
      case 'FREE':
        // A FREE offer is, in the Agreements API, a USAGE offer whose rate
        // card happens to be $0. For example offer-4eliy2uadroxs (Debian 12
        // ARM) and offer-jwqxgu6msev6q (Ubuntu 24.04 Noble): GetOfferTerms
        // returns exactly UsageBasedPricingTerm (currency USD, every price
        // "0") + LegalTerm + SupportTerm. There is no separate "free" term
        // type, and dropping the pricing term makes AWS reject the request
        // with "All mandatory terms must be accepted to create an Agreement."
        //
        // Treated identically to USAGE: same terms, $0 rates. The guard
        // after this filter refuses the request if any rate is not zero.
        return USAGE_PRICING_TERM_TYPES.has(term.termType);

      case 'USAGE':
        // Include usage/recurring pricing terms; strip contract-only
        // pricing terms — those belong in a separate agreement.
        return USAGE_PRICING_TERM_TYPES.has(term.termType);

      case 'BYOL':
        return BYOL_PRICING_TERM_TYPES.has(term.termType);

      case 'CONTRACT':
        // Include everything — CONTRACT agreements require the full
        // term set per AWS docs. The ConfigurableUpfrontPricingTerm gets
        // the buyer's configuration attached below.
        return true;

      case 'PRIVATE_OFFER':
        // Private offers share the underlying pricing model — the
        // wizard shouldn't be dispatched here without first resolving
        // the base flow. Defensive: include usage/BYOL/contract-only
        // as a superset that still respects "no random terms".
        return (
          USAGE_PRICING_TERM_TYPES.has(term.termType)
          || BYOL_PRICING_TERM_TYPES.has(term.termType)
          || CONTRACT_ONLY_TERM_TYPES.has(term.termType)
        );

      default:
        return false;
    }
  });

  if (flow === 'FREE') {
    const charged = filtered.find((term) => !chargesNothing(term));
    if (charged) { throw new FreeOfferChargesError(charged.termId); }
  }

  return filtered.map((term): RequestedTermPayload => {
    // RenewalTerm requires `enableAutoRenew`. Default to `false` — buyers
    // can amend later. Sending the term id without configuration causes a
    // ValidationException.
    if (term.termType === 'RenewalTerm') {
      return {
        id: term.termId,
        configuration: {
          renewalTermConfiguration: { enableAutoRenew: false },
        },
      };
    }
    // ConfigurableUpfrontPricingTerm (CONTRACT flow) requires the buyer's
    // selectorValue + dimensions. Payload shape confirmed via official
    // AWS docs at
    // https://docs.aws.amazon.com/marketplace/latest/developerguide/work-with-agreement-api-buyer.html
    if (
      term.termType === 'ConfigurableUpfrontPricingTerm'
      && contractConfig
      && contractConfig.termId === term.termId
    ) {
      return {
        id: term.termId,
        configuration: {
          configurableUpfrontPricingTermConfiguration: {
            selectorValue: contractConfig.selectorValue,
            dimensions: contractConfig.dimensions,
          },
        },
      };
    }
    return { id: term.termId };
  });
};

/**
 * Usage-based summary: peek at the first rate card's prices to decide free vs
 * paid. Extracted from `summarizePricingTerm` to keep that function under the
 * repo's complexity limit.
 */
const summarizeUsageBasedTerm = (
  rawTerm: Record<string, unknown>,
  currency: string,
): string => {
  const rateCards = rawTerm.rateCards as Array<Record<string, unknown>> | undefined;
  if (!Array.isArray(rateCards) || rateCards.length === EMPTY) {
    return `Usage-based (${currency})`;
  }
  const inner = rateCards[FIRST_ITEM_INDEX]?.rateCard as
    Array<Record<string, unknown>> | undefined;
  if (!Array.isArray(inner) || inner.length === EMPTY) {
    return `Usage-based (${currency})`;
  }
  const prices = new Set(
    inner.map((r) => typeof r.price === 'string' ? r.price : String(r.price ?? '')),
  );
  if (prices.size === SINGLE_PRICE && prices.has('0')) {
    return `Usage-based · ${currency} 0.00 per unit (free)`;
  }
  // Show a range hint for varied instance-type pricing.
  return `Usage-based · pricing varies by dimension (${currency})`;
};

/**
 * Best-effort human-readable one-line summary for a pricing term. For
 * usage-based free-tier offers we surface "$0.00 / hour"; for anything
 * else we fall back to a currency-code hint if available. The full rate
 * card is available in the expandable "technical details" section.
 */
export const summarizePricingTerm = (term: MarketplaceOfferTerm): string => {
  const t = term.rawTerm as Record<string, unknown>;
  const currency = typeof t.currencyCode === 'string' ? t.currencyCode : 'USD';

  if (term.termType === 'FreeTrialTerm') {
    return 'Free trial included';
  }

  if (term.termType === 'UsageBasedPricingTerm') {
    return summarizeUsageBasedTerm(t, currency);
  }

  // Fixed upfront and recurring — surface currency; specific amount is
  // dimension-dependent, expand for details.
  if (term.termType === 'FixedUpfrontPricingTerm') {
    return `Fixed upfront (${currency})`;
  }
  if (term.termType === 'ConfigurableUpfrontPricingTerm') {
    return `Configurable upfront (${currency})`;
  }
  if (term.termType === 'RecurringPaymentTerm') {
    return `Recurring (${currency})`;
  }

  return '';
};
