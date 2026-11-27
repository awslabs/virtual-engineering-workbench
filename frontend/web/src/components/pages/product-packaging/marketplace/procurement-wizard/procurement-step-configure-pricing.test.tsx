// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Tests for ProcurementStepConfigurePricing — the CONTRACT flow's
// Configure & Confirm Pricing step.
//
// NOTE ON SELECTORS: this component's `data-test` attributes do NOT reach the
// DOM. Cloudscape components do not forward unknown props, so every
// `data-test` on an <Input>, <RadioGroup>, <Box> etc. is swallowed — a probe
// of the rendered output found zero `[data-test]` elements. `getByTestId`
// here would never match, producing a test that cannot pass.
// These tests therefore assert on real DOM: input types/values, radio inputs,
// and visible text.

import React from 'react';
import { render, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ProcurementStepConfigurePricing, parseQuantity } from './procurement-step-configure-pricing';
import { GetMarketplaceOfferResponse } from '../../../../../services/API/marketplace-procurement-api';
import { i18n } from './procurement-wizard.translations';

const ONE = 1;
const FIFTY = 50;
const SEVEN = 7;
const THREE = 3;
const LAST = -1;
const NONE = 0;
const FOUR = 4;
const TWENTY_FIVE = 25;
const TWO = 2;

type RawDimension = Record<string, string>;

/** Build a CONTRACT offer with one rate card under the given constraints. */
const offerWith = (
  constraints: Record<string, string>,
  dimensions: RawDimension[],
  selectorValue = 'P12M',
): GetMarketplaceOfferResponse => ({
  offerId: 'offer-contract',
  pricingModelType: 'CONTRACT',
  terms: [{
    termId: 'term-cupt',
    termType: 'ConfigurableUpfrontPricingTerm',
    rawTerm: {
      currencyCode: 'USD',
      rateCards: [{
        selector: { type: 'Duration', value: selectorValue },
        constraints,
        rateCard: dimensions,
      }],
    },
  }],
} as unknown as GetMarketplaceOfferResponse);

const ALLOW_ALL = { multipleDimensionSelection: 'Allowed', quantityConfiguration: 'Allowed' };
const SINGLE_DIM = { multipleDimensionSelection: 'Disallowed', quantityConfiguration: 'Allowed' };

const USERS = { dimensionKey: 'Users', displayName: 'Users', price: '100', unit: 'user' };
const NODES = { dimensionKey: 'Nodes', displayName: 'Nodes', price: '500', unit: 'node' };

const renderStep = (offer: GetMarketplaceOfferResponse) => {
  const onConfigChange = vi.fn();
  const utils = render(
    <ProcurementStepConfigurePricing
      offer={offer}
      isLoading={false}
      onConfigChange={onConfigChange}
      config={null}
    />,
  );
  const quantityInput = () =>
    utils.container.querySelector('input[type="number"]') as HTMLInputElement;
  return { ...utils, onConfigChange, quantityInput };
};

// ---------------------------------------------------------------------------
// parseQuantity — strict parsing of a typed quantity (no `Number.parseInt`
// prefix reads, no `Math.max(1, ...)` clamping). The component tests below
// cover what the buyer sees and what is emitted.
// ---------------------------------------------------------------------------
describe('parseQuantity', () => {
  it('accepts positive integers', () => {
    expect(parseQuantity('1')).toBe(ONE);
    expect(parseQuantity('50')).toBe(FIFTY);
    expect(parseQuantity(' 7 ')).toBe(SEVEN);
  });

  it('rejects zero and negatives rather than coercing them to 1', () => {
    expect(parseQuantity('0')).toBeNull();
    expect(parseQuantity('-5')).toBeNull();
  });

  it('rejects partially-numeric and fractional input', () => {
    // `Number.parseInt` reads these as 3 and 1 — a typo silently becoming a
    // different quantity than the one on screen is the defect.
    expect(parseQuantity('3abc')).toBeNull();
    expect(parseQuantity('1.9')).toBeNull();
    expect(parseQuantity('1e3')).toBeNull();
  });

  it('rejects empty input', () => {
    // Mid-edit, not a request for zero units.
    expect(parseQuantity('')).toBeNull();
    expect(parseQuantity('   ')).toBeNull();
  });

  it('rejects values beyond safe integer precision', () => {
    expect(parseQuantity('99999999999999999999')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Invalid quantities are validated, never coerced
//
// Coercing with `Math.max(1, Math.floor(...))` before a "positive integer"
// check would make the check unreachable: typing 0 or -5 would show one
// quantity and send another, with Next still enabled.
// ---------------------------------------------------------------------------
describe('ProcurementStepConfigurePricing invalid quantities', () => {
  it('keeps an invalid quantity visible AND refuses to submit it', () => {
    const { quantityInput, onConfigChange } = renderStep(offerWith(ALLOW_ALL, [USERS]));
    expect(quantityInput().value).toBe('1');

    fireEvent.change(quantityInput(), { target: { value: '0' } });

    // The input must show 0 AND emit no config: showing 0 while sending 1
    // is the failure mode. Both halves are asserted so the pairing is what
    // the test protects.
    expect(quantityInput().value).toBe('0');
    expect(onConfigChange).toHaveBeenLastCalledWith(null);
  });

  it.each([
    ['0', 'zero'],
    ['-5', 'negative'],
    ['1.9', 'fractional'],
    ['3abc', 'partially numeric'],
    ['', 'empty'],
  ])('emits null config for %s input (%s)', (value) => {
    const { quantityInput, onConfigChange } = renderStep(offerWith(ALLOW_ALL, [USERS]));
    onConfigChange.mockClear();

    fireEvent.change(quantityInput(), { target: { value } });

    // null is what disables the wizard's Next button. Anything else means the
    // buyer can carry this quantity into a quote.
    expect(onConfigChange).toHaveBeenLastCalledWith(null);
  });

  it.each([
    ['0', ONE],
    ['-5', ONE],
    ['1.9', ONE],
    ['3abc', THREE],
  ])('never submits a quantity the buyer did not type (%s was sent as %i)', (typed) => {
    const { quantityInput, onConfigChange } = renderStep(offerWith(ALLOW_ALL, [USERS]));

    fireEvent.change(quantityInput(), { target: { value: typed } });

    // Coercion would emit the value shown in the test name —
    // `Math.max(1, Math.floor(...))` turns 0 and -5 into 1, and
    // `Number.parseInt` reads '3abc' as 3 and '1.9' as 1. Asserting on the
    // emitted dimensions (rather than just `null`) states the real contract:
    // the config must never carry a number the buyer never entered.
    const last = onConfigChange.mock.calls.at(LAST)?.[0];
    expect(last).toBeNull();
  });

  it('shows an actionable error and hides the total while a quantity is invalid', () => {
    const { quantityInput, container } = renderStep(offerWith(ALLOW_ALL, [USERS]));

    fireEvent.change(quantityInput(), { target: { value: '0' } });

    expect(container.textContent).toContain('Enter a whole number of 1 or more.');
    // A total computed from an invalid quantity is a made-up number; showing
    // USD 0.00 would read as a free contract.
    expect(container.textContent).toContain('—');
    expect(container.textContent).not.toContain('USD 0.00');
  });

  it('marks the input invalid so the error is not colour-only', () => {
    const { quantityInput } = renderStep(offerWith(ALLOW_ALL, [USERS]));
    fireEvent.change(quantityInput(), { target: { value: '0' } });
    expect(quantityInput().getAttribute('aria-invalid')).toBe('true');
  });

  it('recovers when the buyer corrects the quantity', () => {
    const { quantityInput, onConfigChange, container } = renderStep(
      offerWith(ALLOW_ALL, [USERS]),
    );

    fireEvent.change(quantityInput(), { target: { value: '0' } });
    expect(onConfigChange).toHaveBeenLastCalledWith(null);

    fireEvent.change(quantityInput(), { target: { value: '4' } });

    expect(onConfigChange).toHaveBeenLastCalledWith({
      termId: 'term-cupt',
      selectorValue: 'P12M',
      dimensions: [{ dimensionKey: 'Users', dimensionValue: FOUR }],
    });
    expect(container.textContent).not.toContain('Enter a whole number');
    expect(container.textContent).toContain('USD 400');
  });

  // Calibration: valid input must still work, or "it rejects everything" would
  // pass all the tests above.
  it('emits the typed quantity for valid input', () => {
    const { quantityInput, onConfigChange } = renderStep(offerWith(ALLOW_ALL, [USERS]));

    fireEvent.change(quantityInput(), { target: { value: '25' } });

    expect(onConfigChange).toHaveBeenLastCalledWith({
      termId: 'term-cupt',
      selectorValue: 'P12M',
      dimensions: [{ dimensionKey: 'Users', dimensionValue: TWENTY_FIVE }],
    });
  });
});

// ---------------------------------------------------------------------------
// #10b — multipleDimensionSelectionAllowed was parsed and never enforced
//
// The constraint was read into `ParsedRateCard.multipleDimensionSelectionAllowed`
// and then unused: the step always submitted EVERY dimension on the card. For a
// Disallowed card with >1 dimension that is a guaranteed AWS 400, raised only at
// the end of the wizard after the buyer has agreed to terms.
// ---------------------------------------------------------------------------
describe('ProcurementStepConfigurePricing multipleDimensionSelection', () => {
  /** Radio inputs excluding the rate-card selector (whose values are indices). */
  const dimensionRadios = (container: HTMLElement) =>
    [...container.querySelectorAll('input[type="radio"]')]
      .filter((r) => !/^\d+$/u.test((r as HTMLInputElement).value)) as HTMLInputElement[];

  it('submits exactly ONE dimension when multiple selection is disallowed', () => {
    const { onConfigChange } = renderStep(offerWith(SINGLE_DIM, [USERS, NODES]));

    const last = onConfigChange.mock.calls.at(LAST)?.[0];
    expect(last.dimensions).toHaveLength(ONE);
    expect(last.dimensions[0].dimensionKey).toBe('Users');
  });

  it('offers the dimensions as a single-select and honours the choice', () => {
    const { container, onConfigChange } = renderStep(offerWith(SINGLE_DIM, [USERS, NODES]));

    const radios = dimensionRadios(container);
    expect(radios.map((r) => r.value)).toEqual(['Users', 'Nodes']);
    expect(container.textContent).toContain('only one dimension per agreement');

    fireEvent.click(radios[1]);

    expect(onConfigChange).toHaveBeenLastCalledWith({
      termId: 'term-cupt',
      selectorValue: 'P12M',
      dimensions: [{ dimensionKey: 'Nodes', dimensionValue: ONE }],
    });
  });

  it('renders one quantity input — for the selected dimension only', () => {
    const { container } = renderStep(offerWith(SINGLE_DIM, [USERS, NODES]));
    expect(container.querySelectorAll('input[type="number"]')).toHaveLength(ONE);
  });

  it('prices only the selected dimension, not the sum of all of them', () => {
    const { container } = renderStep(offerWith(SINGLE_DIM, [USERS, NODES]));

    // Users alone = 100. The sum of both (600) would be a price the buyer
    // cannot be charged, because AWS will not accept both dimensions.
    expect(container.textContent).toContain('USD 100');
    expect(container.textContent).not.toContain('USD 600');
  });

  // Calibration: Allowed cards must keep the existing multi-dimension
  // behaviour. Without this, "always send one dimension" would pass everything
  // above while breaking every normal offer.
  it('submits ALL dimensions when multiple selection is allowed', () => {
    const { container, onConfigChange } = renderStep(offerWith(ALLOW_ALL, [USERS, NODES]));

    const last = onConfigChange.mock.calls.at(LAST)?.[0];
    expect(last.dimensions).toHaveLength(TWO);
    expect(last.dimensions.map((d: { dimensionKey: string }) => d.dimensionKey))
      .toEqual(['Users', 'Nodes']);
    // One input per dimension, and no single-select prompt.
    expect(container.querySelectorAll('input[type="number"]')).toHaveLength(TWO);
    expect(dimensionRadios(container)).toHaveLength(NONE);
  });

  // Calibration: a single-dimension Disallowed card is the common real shape
  // and must not acquire a pointless radio group.
  it('does not render a dimension selector for a single-dimension card', () => {
    const { container, onConfigChange } = renderStep(offerWith(SINGLE_DIM, [USERS]));

    expect(dimensionRadios(container)).toHaveLength(NONE);
    expect(onConfigChange.mock.calls.at(LAST)?.[0].dimensions).toHaveLength(ONE);
  });
});

// ---------------------------------------------------------------------------
// quantityConfiguration=Disallowed — every dimension is fixed at 1.
// ---------------------------------------------------------------------------
describe('ProcurementStepConfigurePricing quantityConfiguration=Disallowed', () => {
  it('fixes every dimension at 1 and renders no quantity input', () => {
    const { container, onConfigChange } = renderStep(offerWith(
      { multipleDimensionSelection: 'Allowed', quantityConfiguration: 'Disallowed' },
      [USERS, NODES],
    ));

    expect(container.querySelectorAll('input[type="number"]')).toHaveLength(NONE);
    expect(container.textContent).toContain('× 1 (fixed)');
    expect(onConfigChange.mock.calls.at(LAST)?.[0].dimensions).toEqual([
      { dimensionKey: 'Users', dimensionValue: ONE },
      { dimensionKey: 'Nodes', dimensionValue: ONE },
    ]);
  });
});

// ---------------------------------------------------------------------------
// Rules of hooks: the step returns early for loading, no offer, and an offer
// without rate cards. With hooks after those returns, switching from the form
// to an offer without rate cards ran fewer hooks than the previous render and
// React threw "Rendered fewer hooks than expected".
// ---------------------------------------------------------------------------
describe('ProcurementStepConfigurePricing loading transitions', () => {
  it('switches between the form and every early-return state', () => {
    const onConfigChange = vi.fn();
    const offer = offerWith(ALLOW_ALL, [USERS]);
    const step = (props: { offer: GetMarketplaceOfferResponse | null, isLoading: boolean }) =>
      <ProcurementStepConfigurePricing
        offer={props.offer}
        isLoading={props.isLoading}
        onConfigChange={onConfigChange}
        config={null}
      />;
    const { container, rerender } = render(step({ offer, isLoading: false }));
    expect(container.querySelector('input[type="number"]')).toBeTruthy();

    rerender(step({ offer, isLoading: true }));
    expect(container.querySelector('input[type="number"]')).toBeNull();

    rerender(step({ offer: null, isLoading: false }));
    expect(container.textContent).toContain(i18n.configurePricingNoOfferHint);

    rerender(step({ offer, isLoading: false }));
    const withoutRateCards = { ...offer, terms: [] };
    rerender(step({ offer: withoutRateCards, isLoading: false }));
    expect(container.textContent).toContain(i18n.configurePricingNoRateCardsError);

    rerender(step({ offer, isLoading: false }));
    expect(container.querySelector('input[type="number"]')).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// Restoring a config: it must belong to this term, not only share a selector.
// ---------------------------------------------------------------------------
describe('ProcurementStepConfigurePricing restored config', () => {
  const RESTORED_QUANTITY = 50;
  const restored = (termId: string) => ({
    termId,
    selectorValue: 'P12M',
    dimensions: [{ dimensionKey: 'Users', dimensionValue: RESTORED_QUANTITY }],
  });

  const renderWithConfig = (config: ReturnType<typeof restored>) => {
    const { container } = render(
      <ProcurementStepConfigurePricing
        offer={offerWith(ALLOW_ALL, [USERS])}
        isLoading={false}
        onConfigChange={vi.fn()}
        config={config}
      />,
    );
    return container.querySelector('input[type="number"]') as HTMLInputElement;
  };

  it('seeds quantities from a config for the same term', () => {
    expect(renderWithConfig(restored('term-cupt')).value).toBe(String(RESTORED_QUANTITY));
  });

  it('ignores a config for another term with the same selector', () => {
    expect(renderWithConfig(restored('term-other')).value).toBe('1');
  });
});
