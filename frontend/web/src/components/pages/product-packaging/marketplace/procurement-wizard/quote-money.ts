// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Display helpers for the money fields of a CreateAgreementRequest quote.
// Shared by the Get Quote and Accept & Confirm steps.

import { WizardFlow } from './offer-helpers';
import { i18n } from './procurement-wizard.translations';

/**
 * Text for an estimated value and its currency.
 *
 * - value and currency: `"400.00 USD"`.
 * - value without currency: the value plus "(currency unknown)". Hiding a
 *   value AWS did return would hide part of the price.
 * - no value, CONTRACT: "Estimate unavailable". A contract has a fixed
 *   up-front price, so a missing estimate is a gap, not a pricing model.
 * - no value, other flows: "Usage-based pricing". Hourly and usage offers
 *   legitimately carry no estimate; the total depends on consumption.
 */
export const formatQuoteMoney = (
  value: string | null | undefined,
  currency: string | null | undefined,
  flow: WizardFlow,
): string => {
  if (value) {
    return currency ? `${value} ${currency}` : `${value} ${i18n.quoteCurrencyUnknown}`;
  }
  return flow === 'CONTRACT' ? i18n.quoteEstimateUnavailable : i18n.quoteUsageBased;
};

/** Text for the currency cell, following the same rules as `formatQuoteMoney`. */
export const formatQuoteCurrency = (
  currency: string | null | undefined,
  flow: WizardFlow,
): string => {
  if (currency) { return currency; }
  return flow === 'CONTRACT' ? i18n.quoteCurrencyUnknown : i18n.quoteUsageBased;
};

/** True for a CONTRACT quote that came back without an estimated value. */
export const isMissingContractEstimate = (
  value: string | null | undefined,
  flow: WizardFlow,
): boolean => flow === 'CONTRACT' && !value;
