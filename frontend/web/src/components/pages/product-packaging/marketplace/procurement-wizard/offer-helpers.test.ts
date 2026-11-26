// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Tests for offer-helpers utilities used by the procurement wizard.
// Covers:
// - isFreeTierOffer: detects FREE pricing model via top-level flag
// - getTermTypeLabel: maps AWS termType codes to human labels
// - extractLegalDocuments: parses LegalTerm rawTerm.documents safely
// - extractRefundPolicy: parses SupportTerm rawTerm.refundPolicy safely
// - summarizePricingTerm: renders a one-line pricing summary

import { describe, it, expect } from 'vitest';
import {
  isFreeTierOffer,
  isByolOffer,
  isAwsSoldOffer,
  offerHasNoPricingTerm,
  AWS_SELLER_PROFILE_ID,
  getTermTypeLabel,
  extractLegalDocuments,
  extractRefundPolicy,
  summarizePricingTerm,
  getFriendlyOfferName,
  getWizardFlow,
  isTwoStepFlow,
  getListingCtaLabel,
  filterTermsForRequestedPayload,
  FreeOfferChargesError,
} from './offer-helpers';
import {
  GetMarketplaceOfferResponse,
  MarketplaceOfferTerm,
} from '../../../../../services/API/marketplace-procurement-api';

const TWO = 2;
const FIVE = 5;
const FIFTY = 50;
const FOUR = 4;
const ONE = 1;
const EIGHT = 8;
const TWENTY_FIVE = 25;
const NONE = 0;

const makeOffer = (overrides: Partial<GetMarketplaceOfferResponse> = {}): GetMarketplaceOfferResponse => ({
  offerId: 'offer-test',
  catalog: 'AWSMarketplace',
  agreementProposalId: 'ap-1',
  associatedProducts: [],
  terms: [],
  ...overrides,
});

const makeTerm = (termType: string, termId?: string): MarketplaceOfferTerm => ({
  termId: termId || `term-${termType.toLowerCase()}`,
  termType,
  rawTerm: {},
});

/** A UsageBasedPricingTerm whose single rate card charges the given prices. */
const usageTermPriced = (...prices: unknown[]): MarketplaceOfferTerm => ({
  termId: 'term-usagebasedpricingterm',
  termType: 'UsageBasedPricingTerm',
  rawTerm: {
    currencyCode: 'USD',
    rateCards: [{
      rateCard: prices.map((price, i) => ({ dimensionKey: `d${i}`, price, unit: 'Hrs' })),
    }],
  },
});

describe('isFreeTierOffer', () => {
  it('returns false for null', () => {
    expect(isFreeTierOffer(null)).toBe(false);
  });

  it('returns true when pricingModelType is FREE', () => {
    expect(isFreeTierOffer(makeOffer({ pricingModelType: 'FREE' }))).toBe(true);
  });

  it('returns false for USAGE / CONTRACT / BYOL', () => {
    expect(isFreeTierOffer(makeOffer({ pricingModelType: 'USAGE' }))).toBe(false);
    expect(isFreeTierOffer(makeOffer({ pricingModelType: 'CONTRACT' }))).toBe(false);
    expect(isFreeTierOffer(makeOffer({ pricingModelType: 'BYOL' }))).toBe(false);
  });

  it('returns false when pricingModelType is missing', () => {
    expect(isFreeTierOffer(makeOffer({}))).toBe(false);
  });
});

describe('isByolOffer', () => {
  it('returns false for null', () => {
    expect(isByolOffer(null)).toBe(false);
  });

  it('returns true when pricingModelType is BYOL', () => {
    expect(isByolOffer(makeOffer({ pricingModelType: 'BYOL' }))).toBe(true);
  });

  it('returns false for FREE / USAGE / CONTRACT', () => {
    expect(isByolOffer(makeOffer({ pricingModelType: 'FREE' }))).toBe(false);
    expect(isByolOffer(makeOffer({ pricingModelType: 'USAGE' }))).toBe(false);
    expect(isByolOffer(makeOffer({ pricingModelType: 'CONTRACT' }))).toBe(false);
  });

  it('returns false when pricingModelType is missing', () => {
    expect(isByolOffer(makeOffer({}))).toBe(false);
  });
});

describe('getTermTypeLabel', () => {
  it('maps known types to friendly labels', () => {
    expect(getTermTypeLabel('LegalTerm')).toBe('Legal terms');
    expect(getTermTypeLabel('SupportTerm')).toBe('Support');
    expect(getTermTypeLabel('UsageBasedPricingTerm')).toBe('Usage-based pricing');
    expect(getTermTypeLabel('FixedUpfrontPricingTerm')).toBe('Upfront pricing');
    expect(getTermTypeLabel('RecurringPaymentTerm')).toBe('Recurring payment');
    expect(getTermTypeLabel('FreeTrialTerm')).toBe('Free trial');
    expect(getTermTypeLabel('ValidityTerm')).toBe('Validity period');
  });

  it('spaces unknown PascalCase into readable words and strips trailing Term', () => {
    expect(getTermTypeLabel('SomeNewTerm')).toBe('Some New');
    expect(getTermTypeLabel('AnotherUnknownThing')).toBe('Another Unknown Thing');
  });
});

describe('extractLegalDocuments', () => {
  const legalTerm: MarketplaceOfferTerm = {
    termId: 'term-legal-1',
    termType: 'LegalTerm',
    rawTerm: {
      id: 'term-legal-1',
      type: 'LegalTerm',
      documents: [
        {
          type: 'CustomEula',
          url: 'https://awsmp-legal.s3.us-east-1.amazonaws.com/eula.pdf?X-Amz-Signature=...',
          version: '2024-01-01',
        },
        {
          type: 'StandardDsa',
          url: 'https://awsmp-legal.s3.us-east-1.amazonaws.com/dsa.pdf',
        },
      ],
    },
  };

  it('extracts documents with friendly display names for known types', () => {
    const docs = extractLegalDocuments(legalTerm);
    expect(docs).toHaveLength(TWO);
    expect(docs[0].displayName).toBe('End-User License Agreement');
    expect(docs[0].url).toContain('eula.pdf');
    expect(docs[0].version).toBe('2024-01-01');
    expect(docs[1].displayName).toBe('Data Sharing Agreement');
    expect(docs[1].version).toBeNull();
  });

  it('returns empty for non-LegalTerm input', () => {
    const nonLegal: MarketplaceOfferTerm = {
      termId: 'x', termType: 'SupportTerm', rawTerm: {},
    };
    expect(extractLegalDocuments(nonLegal)).toEqual([]);
  });

  it('returns empty for malformed rawTerm', () => {
    const bad: MarketplaceOfferTerm = {
      termId: 'x', termType: 'LegalTerm', rawTerm: {},
    };
    expect(extractLegalDocuments(bad)).toEqual([]);
  });

  it('handles missing URL as null rather than throwing', () => {
    const noUrl: MarketplaceOfferTerm = {
      termId: 'x',
      termType: 'LegalTerm',
      rawTerm: {
        documents: [{ type: 'CustomEula' }],
      },
    };
    const docs = extractLegalDocuments(noUrl);
    expect(docs[0].url).toBeNull();
  });

  it('falls through to titlecase for unknown document types', () => {
    const t: MarketplaceOfferTerm = {
      termId: 'x',
      termType: 'LegalTerm',
      rawTerm: {
        documents: [{ type: 'SomeExoticDocKind', url: 'https://x' }],
      },
    };
    expect(extractLegalDocuments(t)[0].displayName).toBe('Some Exotic Doc Kind');
  });
});

describe('extractRefundPolicy', () => {
  it('extracts trimmed refund policy from SupportTerm', () => {
    const t: MarketplaceOfferTerm = {
      termId: 'x',
      termType: 'SupportTerm',
      rawTerm: { refundPolicy: '  No refunds will be issued.  \n' },
    };
    expect(extractRefundPolicy(t)).toBe('No refunds will be issued.');
  });

  it('returns empty for non-SupportTerm', () => {
    const t: MarketplaceOfferTerm = {
      termId: 'x', termType: 'LegalTerm', rawTerm: { refundPolicy: 'ignored' },
    };
    expect(extractRefundPolicy(t)).toBe('');
  });

  it('returns empty when refundPolicy is missing', () => {
    const t: MarketplaceOfferTerm = {
      termId: 'x', termType: 'SupportTerm', rawTerm: {},
    };
    expect(extractRefundPolicy(t)).toBe('');
  });
});

describe('summarizePricingTerm', () => {
  it('identifies UsageBased with all-zero rate cards as free', () => {
    const t: MarketplaceOfferTerm = {
      termId: 'x',
      termType: 'UsageBasedPricingTerm',
      rawTerm: {
        currencyCode: 'USD',
        rateCards: [{
          rateCard: [
            { price: '0', unit: 'Hrs', dimensionKey: 'i4i.xlarge' },
            { price: '0', unit: 'Hrs', dimensionKey: 'm5.large' },
          ],
        }],
      },
    };
    expect(summarizePricingTerm(t)).toBe('Usage-based · USD 0.00 per unit (free)');
  });

  it('identifies UsageBased with varied rate cards', () => {
    const t: MarketplaceOfferTerm = {
      termId: 'x',
      termType: 'UsageBasedPricingTerm',
      rawTerm: {
        currencyCode: 'USD',
        rateCards: [{
          rateCard: [
            { price: '0.05', unit: 'Hrs' },
            { price: '0.10', unit: 'Hrs' },
          ],
        }],
      },
    };
    expect(summarizePricingTerm(t)).toBe('Usage-based · pricing varies by dimension (USD)');
  });

  it('summarizes FreeTrialTerm', () => {
    const t: MarketplaceOfferTerm = {
      termId: 'x', termType: 'FreeTrialTerm', rawTerm: {},
    };
    expect(summarizePricingTerm(t)).toBe('Free trial included');
  });

  it('summarizes fixed upfront + recurring + configurable with currency', () => {
    const fixed: MarketplaceOfferTerm = {
      termId: 'a', termType: 'FixedUpfrontPricingTerm', rawTerm: { currencyCode: 'EUR' },
    };
    const recurring: MarketplaceOfferTerm = {
      termId: 'b', termType: 'RecurringPaymentTerm', rawTerm: { currencyCode: 'GBP' },
    };
    const configurable: MarketplaceOfferTerm = {
      termId: 'c', termType: 'ConfigurableUpfrontPricingTerm', rawTerm: {},
    };
    expect(summarizePricingTerm(fixed)).toBe('Fixed upfront (EUR)');
    expect(summarizePricingTerm(recurring)).toBe('Recurring (GBP)');
    expect(summarizePricingTerm(configurable)).toBe('Configurable upfront (USD)');
  });

  it('returns empty string for unknown / non-pricing term types', () => {
    const t: MarketplaceOfferTerm = {
      termId: 'x', termType: 'LegalTerm', rawTerm: {},
    };
    expect(summarizePricingTerm(t)).toBe('');
  });
});

describe('getFriendlyOfferName', () => {
  it('returns explicit offerName when AWS provides one', () => {
    expect(getFriendlyOfferName(makeOffer({
      offerId: 'abc123',
      offerName: 'Canonical Ubuntu 24.04 Free Tier',
    }))).toBe('Canonical Ubuntu 24.04 Free Tier');
  });

  it('falls back to product name when offerName is missing', () => {
    expect(getFriendlyOfferName(makeOffer({
      offerId: '2wqkpek696qhdeo7lbbjncqli',
      associatedProducts: [{
        productId: 'p1',
        productName: 'Fortinet FortiGate VM Next-Generation Firewall',
      } as any],
    }))).toBe('Fortinet FortiGate VM Next-Generation Firewall (public offer)');
  });

  it('falls back to raw offerId as last resort', () => {
    expect(getFriendlyOfferName(makeOffer({
      offerId: '2wqkpek696qhdeo7lbbjncqli',
      associatedProducts: [],
    }))).toBe('2wqkpek696qhdeo7lbbjncqli');
  });

  it('treats empty/whitespace offerName as absent', () => {
    expect(getFriendlyOfferName(makeOffer({
      offerId: 'abc',
      offerName: '   ',
      associatedProducts: [{ productId: 'p1', productName: 'Foo' } as any],
    }))).toBe('Foo (public offer)');
  });
});

describe('getWizardFlow', () => {
  it('routes an AWS-sold offer by its pricing model, like any other seller', () => {
    // Who sells the offer does not decide the flow. An AWS-sold offer that
    // carries a pricing term subscribes through the buyer-side agreement API
    // like any other; whether a subscription is possible at all is decided by
    // the offer's terms, see offerHasNoPricingTerm.
    expect(getWizardFlow(makeOffer({
      pricingModelType: 'FREE',
      sellerOfRecordProfileId: AWS_SELLER_PROFILE_ID,
    }))).toBe('FREE');
    expect(getWizardFlow(makeOffer({
      pricingModelType: 'BYOL',
      sellerOfRecordProfileId: AWS_SELLER_PROFILE_ID,
    }))).toBe('BYOL');
  });
  it('routes FREE offers to the FREE flow when seller is NOT AWS', () => {
    expect(getWizardFlow(makeOffer({
      pricingModelType: 'FREE',
      sellerOfRecordProfileId: '565feec9-canonical',
    }))).toBe('FREE');
  });
  it('routes BYOL offers to the BYOL flow', () => {
    expect(getWizardFlow(makeOffer({ pricingModelType: 'BYOL' }))).toBe('BYOL');
  });
  it('routes CONTRACT offers to the CONTRACT flow', () => {
    expect(getWizardFlow(makeOffer({ pricingModelType: 'CONTRACT' }))).toBe('CONTRACT');
  });
  it('routes USAGE offers to the USAGE flow', () => {
    expect(getWizardFlow(makeOffer({ pricingModelType: 'USAGE' }))).toBe('USAGE');
  });
  it('falls back to USAGE for unknown / missing pricing models', () => {
    expect(getWizardFlow(makeOffer({ pricingModelType: 'OTHER' }))).toBe('USAGE');
    expect(getWizardFlow(makeOffer({}))).toBe('USAGE');
    expect(getWizardFlow(null)).toBe('USAGE');
  });
});

describe('isAwsSoldOffer', () => {
  it('detects AWS SellerOfRecord by profile ID', () => {
    expect(isAwsSoldOffer(makeOffer({
      sellerOfRecordProfileId: AWS_SELLER_PROFILE_ID,
    }))).toBe(true);
  });
  it('returns false for third-party sellers', () => {
    expect(isAwsSoldOffer(makeOffer({
      sellerOfRecordProfileId: '565feec9-canonical',
    }))).toBe(false);
  });
  it('returns false for null / missing seller info', () => {
    expect(isAwsSoldOffer(null)).toBe(false);
    expect(isAwsSoldOffer(makeOffer({}))).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// offerHasNoPricingTerm: the signal that decides direct import vs subscribe.
// Keyed off the offer's terms, deliberately NOT off the seller id — a
// transactable offer carries a pricing term even when the fee is $0.
// ---------------------------------------------------------------------------
describe('offerHasNoPricingTerm', () => {
  it('is true when the offer carries only metadata terms', () => {
    // Products AWS sells itself carry legal + support terms and no pricing
    // term: there is no agreement to create, so the AMI is imported directly.
    expect(offerHasNoPricingTerm(makeOffer({
      terms: [makeTerm('LegalTerm'), makeTerm('SupportTerm')],
    }))).toBe(true);
  });

  it('is false when a pricing term is present, even at a zero rate', () => {
    // A $0 third-party offer is still subscribable, so it must not be routed
    // to direct import.
    expect(offerHasNoPricingTerm(makeOffer({
      terms: [makeTerm('LegalTerm'), usageTermPriced('0')],
    }))).toBe(false);
  });

  it('is false for every term type AWS treats as pricing', () => {
    for (const termType of [
      'UsageBasedPricingTerm',
      'FixedUpfrontPricingTerm',
      'ConfigurableUpfrontPricingTerm',
      'RecurringPaymentTerm',
      'FreeTrialTerm',
    ]) {
      expect(offerHasNoPricingTerm(makeOffer({
        terms: [makeTerm('LegalTerm'), makeTerm(termType)],
      }))).toBe(false);
    }
  });

  it('does not depend on who sells the offer', () => {
    // An AWS-sold offer WITH a pricing term subscribes normally; a
    // partner-sold offer WITHOUT one does not. The seller id is not the
    // signal.
    expect(offerHasNoPricingTerm(makeOffer({
      sellerOfRecordProfileId: AWS_SELLER_PROFILE_ID,
      terms: [usageTermPriced('0')],
    }))).toBe(false);
    expect(offerHasNoPricingTerm(makeOffer({
      sellerOfRecordProfileId: '565feec9-canonical',
      terms: [makeTerm('LegalTerm')],
    }))).toBe(true);
  });

  it('is false while the offer is still loading, so callers wait', () => {
    // The wizard must not flash the direct-import panel before the offer
    // resolves.
    expect(offerHasNoPricingTerm(null)).toBe(false);
  });

  it('treats an offer with no terms at all as having no pricing term', () => {
    expect(offerHasNoPricingTerm(makeOffer({ terms: [] }))).toBe(true);
  });
});

describe('isTwoStepFlow', () => {
  it('classifies FREE / USAGE / BYOL as 2-step', () => {
    expect(isTwoStepFlow('FREE')).toBe(true);
    expect(isTwoStepFlow('USAGE')).toBe(true);
    expect(isTwoStepFlow('BYOL')).toBe(true);
  });
  it('classifies CONTRACT / PRIVATE_OFFER as NOT 2-step', () => {
    expect(isTwoStepFlow('CONTRACT')).toBe(false);
    expect(isTwoStepFlow('PRIVATE_OFFER')).toBe(false);
  });
});

describe('getListingCtaLabel', () => {
  it('does not special-case the seller: AWS-sold listings get a pricing label', () => {
    // Every AMI listing routes to the procurement wizard, whoever sells it.
    // The wizard reads the offer's terms and offers a direct import when
    // there is no pricing term, so the CTA no longer has to say the product
    // is unsupported.
    expect(getListingCtaLabel(['FREE'])).toBe('Subscribe');
    expect(getListingCtaLabel(['CONTRACT'])).toBe('Buy contract');
    expect(getListingCtaLabel(['FREE'])).not.toBe('Not supported yet');
  });
  it('labels FREE the same as USAGE — both are a subscription (non-AWS seller)', () => {
    // A free product still requires an agreement + licence grant before it
    // can be used, exactly like pay-as-you-go, so the verb is the same.
    expect(getListingCtaLabel(['FREE'])).toBe('Subscribe');
    // A listing declaring both must not change the verb — same action either way.
    expect(getListingCtaLabel(['USAGE', 'FREE'])).toBe('Subscribe');
    // The invariant that matters: FREE and USAGE are indistinguishable here.
    expect(getListingCtaLabel(['FREE'])).toBe(getListingCtaLabel(['USAGE']));
  });
  it('uses BYOL label when the listing is BYOL-only', () => {
    expect(getListingCtaLabel(['BYOL'])).toBe('Subscribe with own license');
  });
  it('uses Subscribe for USAGE-only listings', () => {
    expect(getListingCtaLabel(['USAGE'])).toBe('Subscribe');
  });
  it('uses Buy contract for CONTRACT-only listings', () => {
    expect(getListingCtaLabel(['CONTRACT'])).toBe('Buy contract');
  });
  it('falls back to "Get this product" for unknown pricing models', () => {
    expect(getListingCtaLabel([])).toBe('Get this product');
    expect(getListingCtaLabel(['SOMETHING_NEW'])).toBe('Get this product');
  });
  it('priority order: FREE > BYOL > USAGE > CONTRACT', () => {
    expect(getListingCtaLabel(['BYOL', 'USAGE', 'CONTRACT'])).toBe('Subscribe with own license');
    expect(getListingCtaLabel(['USAGE', 'CONTRACT'])).toBe('Subscribe');
    expect(getListingCtaLabel(['CONTRACT', 'FREE'])).toBe('Subscribe');
  });
});

describe('filterTermsForRequestedPayload', () => {
  // Rules encoded here match the AWS Marketplace Agreement API docs:
  // https://docs.aws.amazon.com/marketplace/latest/developerguide/
  //   work-with-agreement-api-buyer.html#construct-requested-terms

  it('FREE flow: includes the $0 usage term — identical to USAGE', () => {
    // A FREE offer's GetOfferTerms returns
    // UsageBasedPricingTerm (all prices "0") + LegalTerm + SupportTerm.
    // There is no distinct "free" term type, so dropping the usage term
    // leaves AWS with a missing mandatory term:
    //   "All mandatory terms must be accepted to create an Agreement."
    // Reproduced against offer-4eliy2uadroxs (Debian 12 ARM).
    const terms = [
      makeTerm('LegalTerm'),
      makeTerm('SupportTerm'),
      makeTerm('ValidityTerm'),
      usageTermPriced('0', '0.00'), // $0 rate card — MUST be sent
    ];
    const result = filterTermsForRequestedPayload(terms, 'FREE');
    expect(result.map((t) => t.id)).toEqual([
      'term-legalterm',
      'term-supportterm',
      'term-validityterm',
      'term-usagebasedpricingterm',
    ]);
    // The invariant: FREE and USAGE build the same payload. A free product is
    // a usage product priced at zero, so the two must not drift apart.
    expect(result).toEqual(filterTermsForRequestedPayload(terms, 'USAGE'));
  });

  it('USAGE flow: includes mandatory + usage pricing, excludes ConfigurableUpfrontPricingTerm', () => {
    // E.g. a Palo Alto VM-Series offer: it has both a usage-based term (pay-as-you-go) and a configurable-
    // upfront term (annual contract). USAGE flow must strip the upfront
    // term so pay-as-you-go completes without an AWS ValidationException.
    const terms = [
      makeTerm('LegalTerm'),
      makeTerm('SupportTerm'),
      makeTerm('ValidityTerm'),
      makeTerm('UsageBasedPricingTerm'),
      makeTerm('ConfigurableUpfrontPricingTerm'),
    ];
    const result = filterTermsForRequestedPayload(terms, 'USAGE');
    expect(result.map((t) => t.id)).toEqual([
      'term-legalterm',
      'term-supportterm',
      'term-validityterm',
      'term-usagebasedpricingterm',
    ]);
  });

  it('USAGE flow: also strips FixedUpfrontPricingTerm and PaymentScheduleTerm', () => {
    const terms = [
      makeTerm('LegalTerm'),
      makeTerm('UsageBasedPricingTerm'),
      makeTerm('FixedUpfrontPricingTerm'),
      makeTerm('PaymentScheduleTerm'),
    ];
    const result = filterTermsForRequestedPayload(terms, 'USAGE');
    expect(result.map((t) => t.id)).toEqual([
      'term-legalterm',
      'term-usagebasedpricingterm',
    ]);
  });

  it('USAGE flow: includes RecurringPaymentTerm alongside UsageBasedPricingTerm', () => {
    // Per AWS docs: first-agreement USAGE terms are UsageBasedPricingTerm
    // AND/OR RecurringPaymentTerm — either or both may be present.
    const terms = [
      makeTerm('LegalTerm'),
      makeTerm('RecurringPaymentTerm'),
    ];
    const result = filterTermsForRequestedPayload(terms, 'USAGE');
    expect(result.map((t) => t.id)).toEqual([
      'term-legalterm',
      'term-recurringpaymentterm',
    ]);
  });

  it('CONTRACT flow: includes every term (subject to AWS-side configuration requirements)', () => {
    // CONTRACT agreements need the full term set per AWS docs. Configurable
    // upfront terms also need a `configuration` payload, covered by the
    // contractConfig tests below.
    const terms = [
      makeTerm('LegalTerm'),
      makeTerm('SupportTerm'),
      makeTerm('ValidityTerm'),
      makeTerm('ConfigurableUpfrontPricingTerm'),
      makeTerm('FixedUpfrontPricingTerm'),
    ];
    const result = filterTermsForRequestedPayload(terms, 'CONTRACT');
    expect(result).toHaveLength(FIVE);
  });

  it('BYOL flow: includes mandatory + ByolPricingTerm, excludes pricing terms', () => {
    const terms = [
      makeTerm('LegalTerm'),
      makeTerm('ValidityTerm'),
      makeTerm('ByolPricingTerm'),
      makeTerm('UsageBasedPricingTerm'),
      makeTerm('ConfigurableUpfrontPricingTerm'),
    ];
    const result = filterTermsForRequestedPayload(terms, 'BYOL');
    expect(result.map((t) => t.id)).toEqual([
      'term-legalterm',
      'term-validityterm',
      'term-byolpricingterm',
    ]);
  });

  it('attaches enableAutoRenew=false configuration to RenewalTerm', () => {
    // AWS requires `renewalTermConfiguration.enableAutoRenew` (bool) on
    // any RenewalTerm in `requestedTerms`. Default to false — the buyer
    // can enable auto-renew via an AMEND request after the agreement is
    // active.
    const terms = [makeTerm('RenewalTerm', 'term-renewal-abc')];
    const result = filterTermsForRequestedPayload(terms, 'USAGE');
    expect(result).toEqual([
      {
        id: 'term-renewal-abc',
        configuration: {
          renewalTermConfiguration: { enableAutoRenew: false },
        },
      },
    ]);
  });

  it('FREE flow with a zero-rate pricing term: keeps the pricing term', () => {
    // A FREE offer whose pricing term charges nothing still sends that term,
    // because AWS rejects the request without its mandatory terms.
    const terms = [makeTerm('LegalTerm'), usageTermPriced('0')];
    const payload = filterTermsForRequestedPayload(terms, 'FREE');
    expect(payload.map((t) => t.id)).toContain('term-usagebasedpricingterm');
  });

  it('always preserves the mandatory ValidityTerm across all flows', () => {
    const terms = [makeTerm('ValidityTerm')];
    for (const flow of ['FREE', 'USAGE', 'BYOL', 'CONTRACT'] as const) {
      const result = filterTermsForRequestedPayload(terms, flow);
      expect(result.map((t) => t.id)).toContain('term-validityterm');
    }
  });

  it('always preserves the FreeTrialPricingTerm when present (AWS treats as mandatory)', () => {
    // E.g. offer e9yfvyj3uag5uo5j2hjikv74n (Palo Alto VM-Series
    // Bundle 2) — the offer includes a FreeTrialPricingTerm and AWS rejects
    // any CreateAgreementRequest that omits it with "All mandatory terms
    // must be accepted to create an Agreement."
    const terms = [
      makeTerm('LegalTerm'),
      makeTerm('SupportTerm'),
      makeTerm('UsageBasedPricingTerm'),
      makeTerm('FreeTrialPricingTerm', 'term-freetrial'),
      makeTerm('ConfigurableUpfrontPricingTerm'),
    ];
    const result = filterTermsForRequestedPayload(terms, 'USAGE');
    expect(result.map((t) => t.id)).toContain('term-freetrial');
    // But we still strip the configurable-upfront term.
    expect(result.map((t) => t.id)).not.toContain('term-configurableupfrontpricingterm');
  });

  it('preserves original term order (idempotent filter, no reordering)', () => {
    const terms = [
      makeTerm('UsageBasedPricingTerm', 'term-usage'),
      makeTerm('LegalTerm', 'term-legal'),
      makeTerm('ValidityTerm', 'term-validity'),
      makeTerm('SupportTerm', 'term-support'),
    ];
    const result = filterTermsForRequestedPayload(terms, 'USAGE');
    expect(result.map((t) => t.id)).toEqual([
      'term-usage', 'term-legal', 'term-validity', 'term-support',
    ]);
  });
});


// ---------------------------------------------------------------------------
// CONTRACT flow — contractConfig payload attachment
//
// AWS's CreateAgreementRequest for a CONFIGURABLE upfront pricing term
// requires the buyer to supply a `configurableUpfrontPricingTermConfiguration`
// with `selectorValue` (duration, typically an ISO 8601 period like `P12M`)
// and `dimensions[{dimensionKey, dimensionValue}]`. Verified against AWS docs
// at https://docs.aws.amazon.com/marketplace/latest/developerguide/work-with-agreement-api-buyer.html
// ---------------------------------------------------------------------------

describe('filterTermsForRequestedPayload — CONTRACT contractConfig', () => {
  it('attaches configurableUpfrontPricingTermConfiguration to the matching term', () => {
    const terms = [
      makeTerm('LegalTerm', 'term-legal'),
      makeTerm('SupportTerm', 'term-support'),
      makeTerm('ConfigurableUpfrontPricingTerm', 'term-cupt-1'),
      makeTerm('RenewalTerm', 'term-renewal'),
    ];
    const result = filterTermsForRequestedPayload(terms, 'CONTRACT', {
      termId: 'term-cupt-1',
      selectorValue: 'P12M',
      dimensions: [
        { dimensionKey: 'Users', dimensionValue: FIFTY },
      ],
    });
    const configurableEntry = result.find((t) => t.id === 'term-cupt-1');
    expect(configurableEntry).toBeDefined();
    expect(configurableEntry?.configuration).toEqual({
      configurableUpfrontPricingTermConfiguration: {
        selectorValue: 'P12M',
        dimensions: [{ dimensionKey: 'Users', dimensionValue: FIFTY }],
      },
    });
  });

  it('leaves other terms unchanged when contractConfig is supplied', () => {
    const terms = [
      makeTerm('LegalTerm', 'term-legal'),
      makeTerm('ConfigurableUpfrontPricingTerm', 'term-cupt'),
      makeTerm('RenewalTerm', 'term-renewal'),
    ];
    const result = filterTermsForRequestedPayload(terms, 'CONTRACT', {
      termId: 'term-cupt',
      selectorValue: 'P24M',
      dimensions: [{ dimensionKey: 'Cores', dimensionValue: FOUR }],
    });
    const legal = result.find((t) => t.id === 'term-legal');
    expect(legal).toEqual({ id: 'term-legal' });
    const renewal = result.find((t) => t.id === 'term-renewal');
    expect(renewal?.configuration).toEqual({
      renewalTermConfiguration: { enableAutoRenew: false },
    });
  });

  it('does not attach configuration when contractConfig termId does not match', () => {
    // Defensive: if the wizard sends a stale contractConfig pointing at a
    // different term (e.g. user switched offers mid-flow), the ConfigurableUpfrontPricingTerm
    // on the new offer should NOT receive the stale payload — AWS would reject anyway,
    // but the frontend contract is "match by termId or ignore."
    const terms = [
      makeTerm('LegalTerm', 'term-legal'),
      makeTerm('ConfigurableUpfrontPricingTerm', 'term-cupt-current'),
    ];
    const result = filterTermsForRequestedPayload(terms, 'CONTRACT', {
      termId: 'term-cupt-stale',
      selectorValue: 'P12M',
      dimensions: [{ dimensionKey: 'X', dimensionValue: ONE }],
    });
    const cupt = result.find((t) => t.id === 'term-cupt-current');
    expect(cupt).toBeDefined();
    expect(cupt?.configuration).toBeUndefined();
  });

  it('leaves ConfigurableUpfrontPricingTerm without configuration when contractConfig omitted', () => {
    // The wizard passes no contractConfig if the Configure step is skipped or
    // the flow is CONTRACT but incomplete. AWS will reject; better a clear
    // AWS error than a silent shadow default.
    const terms = [
      makeTerm('LegalTerm', 'term-legal'),
      makeTerm('ConfigurableUpfrontPricingTerm', 'term-cupt'),
    ];
    const result = filterTermsForRequestedPayload(terms, 'CONTRACT');
    const cupt = result.find((t) => t.id === 'term-cupt');
    expect(cupt).toEqual({ id: 'term-cupt' });
  });

  it('supports multiple dimensions on the same term', () => {
    // Real offers sometimes have multipleDimensionSelection=Allowed —
    // the frontend must send all selected dimensions in one payload.
    const terms = [
      makeTerm('ConfigurableUpfrontPricingTerm', 'term-multi'),
    ];
    const result = filterTermsForRequestedPayload(terms, 'CONTRACT', {
      termId: 'term-multi',
      selectorValue: 'P36M',
      dimensions: [
        { dimensionKey: 'Cores', dimensionValue: EIGHT },
        { dimensionKey: 'Users', dimensionValue: TWENTY_FIVE },
      ],
    });
    const cupt = result[0];
    const config = cupt.configuration as Record<string, Record<string, unknown>>;
    expect(config.configurableUpfrontPricingTermConfiguration.dimensions).toEqual([
      { dimensionKey: 'Cores', dimensionValue: EIGHT },
      { dimensionKey: 'Users', dimensionValue: TWENTY_FIVE },
    ]);
  });

  it('does not apply contractConfig on non-CONTRACT flows', () => {
    // If the flow is somehow USAGE but the caller passed a contractConfig
    // (defensive test — shouldn't happen in normal wizard flow),
    // the ConfigurableUpfrontPricingTerm is filtered out entirely by the
    // USAGE rules and never gets a configuration attached.
    const terms = [
      makeTerm('UsageBasedPricingTerm', 'term-usage'),
      makeTerm('ConfigurableUpfrontPricingTerm', 'term-cupt'),
    ];
    const result = filterTermsForRequestedPayload(terms, 'USAGE', {
      termId: 'term-cupt',
      selectorValue: 'P12M',
      dimensions: [{ dimensionKey: 'X', dimensionValue: ONE }],
    });
    // ConfigurableUpfrontPricingTerm filtered out by USAGE flow rules
    expect(result.find((t) => t.id === 'term-cupt')).toBeUndefined();
  });
});

describe('filterTermsForRequestedPayload — FREE guard', () => {
  it('builds the request when every rate is zero', () => {
    const terms = [makeTerm('LegalTerm'), usageTermPriced('0', '0.0000', NONE)];
    expect(filterTermsForRequestedPayload(terms, 'FREE').map((t) => t.id))
      .toEqual(['term-legalterm', 'term-usagebasedpricingterm']);
  });

  it('builds the request when no pricing term is sent', () => {
    expect(filterTermsForRequestedPayload([makeTerm('LegalTerm')], 'FREE'))
      .toEqual([{ id: 'term-legalterm' }]);
  });

  it.each([
    ['a non-zero usage rate', usageTermPriced('0', '0.05')],
    ['a usage rate that is not a number', usageTermPriced('free')],
    ['a usage rate with no price', usageTermPriced(undefined)],
    ['a usage term without rate cards', makeTerm('UsageBasedPricingTerm')],
    ['a non-zero recurring payment', {
      termId: 'term-recurring', termType: 'RecurringPaymentTerm', rawTerm: { price: '10.00' },
    }],
  ])('refuses a FREE request with %s', (_label, pricingTerm) => {
    const build = () => filterTermsForRequestedPayload(
      [makeTerm('LegalTerm'), pricingTerm as MarketplaceOfferTerm],
      'FREE',
    );
    expect(build).toThrow(FreeOfferChargesError);
  });

  it('ignores charges on terms the FREE request does not send', () => {
    const contractTerm: MarketplaceOfferTerm = {
      termId: 'term-fixed', termType: 'FixedUpfrontPricingTerm', rawTerm: { price: '999' },
    };
    expect(() => filterTermsForRequestedPayload(
      [usageTermPriced('0'), contractTerm],
      'FREE',
    )).not.toThrow();
  });

  it('does not apply to USAGE, where charges are expected', () => {
    expect(() => filterTermsForRequestedPayload([usageTermPriced('0.05')], 'USAGE'))
      .not.toThrow();
  });
});
