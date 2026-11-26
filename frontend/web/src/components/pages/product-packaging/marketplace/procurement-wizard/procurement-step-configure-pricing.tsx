// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Configure & Confirm Pricing — CONTRACT flow step 2 of 3.
//
// AWS CONTRACT offers (pricingModelType=CONTRACT) carry a
// ConfigurableUpfrontPricingTerm with a list of "rate cards". Each rate
// card exposes:
//   - a selector (typically Duration, value like P12M / P24M / P36M),
//   - constraints (multipleDimensionSelection Allowed/Disallowed,
//     quantityConfiguration Allowed/Disallowed),
//   - the dimension list with per-unit prices.
//
// The buyer picks one rate card + (if quantityConfiguration=Allowed)
// per-dimension quantities. The chosen configuration is emitted via
// `onConfigChange` for the wizard to include on CreateAgreementRequest.
//
// Payload shape (per the AWS Agreements API docs):
//   configuration.configurableUpfrontPricingTermConfiguration = {
//     selectorValue: 'P12M',
//     dimensions: [{ dimensionKey: 'Users', dimensionValue: 50 }]
//   }

import { FC, useMemo, useState, useEffect } from 'react';
import {
  Alert,
  Box,
  Container,
  FormField,
  Header,
  Input,
  RadioGroup,
  SpaceBetween,
  Spinner,
} from '@cloudscape-design/components';
import {
  GetMarketplaceOfferResponse,
  MarketplaceOfferTerm,
} from '../../../../../services/API/marketplace-procurement-api';
import { i18n } from './procurement-wizard.translations';
import { ContractPricingConfig } from './offer-helpers';

interface Props {
  offer: GetMarketplaceOfferResponse | null,
  isLoading: boolean,
  onConfigChange: (config: ContractPricingConfig | null) => void,
  config: ContractPricingConfig | null,
}

// Named numeric constants. The repo enables @typescript-eslint/no-magic-numbers
// repo-wide (eslint.config.js:133) and the rest of the codebase complies —
// see FIRST_ITEM_INDEX / STEP_* in product-packaging/images for the convention.
const FIRST_ITEM_INDEX = 0;
const EMPTY = 0;
const SINGLE_ITEM = 1;
/** AWS's ConfigurableUpfrontPricingTermConfiguration requires >= 1 unit. */
const MIN_QUANTITY = 1;
/** Quantity used when the rate card forbids quantity configuration. */
const FIXED_QUANTITY = 1;
const ZERO_TOTAL = 0;
const MONTHS_PER_YEAR = 12;
const ONE_YEAR = 1;
const ONE_MONTH = 1;
const ONE_DAY = 1;
/** Contract prices are money: two decimals when not a whole number. */
const MONEY_DECIMALS = 2;

// ----------------------------------------------------------------------------
// Shape parsing
// ----------------------------------------------------------------------------

interface ParsedRateCardDimension {
  dimensionKey: string,
  displayName: string,
  price: string,
  unit: string,
}

interface ParsedRateCard {
  cardIdx: number,
  selectorType: string,
  selectorValue: string,
  currency: string,
  multipleDimensionSelectionAllowed: boolean,
  quantityConfigurationAllowed: boolean,
  dimensions: ParsedRateCardDimension[],
}

/**
 * Extract the ConfigurableUpfrontPricingTerm from an offer's terms.
 * Returns `null` if there isn't one (or if there's more than one — we
 * only support the single-term case; multi-term offers would need a
 * design update).
 */
const findConfigurableUpfrontTerm = (
  offer: GetMarketplaceOfferResponse | null,
): MarketplaceOfferTerm | null => {
  if (!offer) { return null; }
  const cupts = (offer.terms || []).filter(
    (t) => t.termType === 'ConfigurableUpfrontPricingTerm',
  );
  return cupts.length === SINGLE_ITEM ? cupts[FIRST_ITEM_INDEX] : null;
};

const parseRateCards = (term: MarketplaceOfferTerm | null): ParsedRateCard[] => {
  if (!term) { return []; }
  const raw = term.rawTerm as Record<string, unknown>;
  const currency = typeof raw.currencyCode === 'string' ? raw.currencyCode : 'USD';
  const rateCards = raw.rateCards as Array<Record<string, unknown>> | undefined;
  if (!Array.isArray(rateCards)) { return []; }

  const parsed: ParsedRateCard[] = [];
  rateCards.forEach((rc, cardIdx) => {
    const selector = rc.selector as Record<string, unknown> | undefined;
    const constraints = rc.constraints as Record<string, unknown> | undefined;
    const inner = rc.rateCard as Array<Record<string, unknown>> | undefined;

    const selectorType = typeof selector?.type === 'string' ? selector.type : '';
    const selectorValue = typeof selector?.value === 'string' ? selector.value : '';

    // Constraints are REQUIRED per AWS's ConfigurableUpfrontRateCardItem
    // schema. Missing constraints → treat as most restrictive (single
    // dimension, no quantity configuration) to avoid over-permissive UI.
    const multipleDim = constraints?.multipleDimensionSelection === 'Allowed';
    const quantityConf = constraints?.quantityConfiguration === 'Allowed';

    const dimensions: ParsedRateCardDimension[] = Array.isArray(inner)
      ? inner.map((r) => {
        const key = typeof r.dimensionKey === 'string' ? r.dimensionKey : '';
        // `r.price` comes off an untyped AWS rawTerm, so it may be a number,
        // null or absent. Both null and undefined mean "no price".
        const hasPrice = r.price !== null && r.price !== undefined;
        return {
          dimensionKey: key,
          displayName: typeof r.displayName === 'string' ? r.displayName : key,
          price: typeof r.price === 'string' ? r.price : hasPrice ? String(r.price) : '0',
          unit: typeof r.unit === 'string' ? r.unit : '',
        };
      })
      : [];

    parsed.push({
      cardIdx,
      selectorType,
      selectorValue,
      currency,
      multipleDimensionSelectionAllowed: multipleDim,
      quantityConfigurationAllowed: quantityConf,
      dimensions,
    });
  });
  return parsed;
};

// ----------------------------------------------------------------------------
// Display helpers
// ----------------------------------------------------------------------------

/** `12` → "12 months", `24` → "2 years". Whole years are preferred. */
const formatMonths = (n: number): string => {
  if (n % MONTHS_PER_YEAR === EMPTY) {
    const y = n / MONTHS_PER_YEAR;
    return y === ONE_YEAR ? '1 year' : `${y} years`;
  }
  return n === ONE_MONTH ? '1 month' : `${n} months`;
};

/**
 * Best-effort friendly rendering of an ISO 8601 period selector value.
 * `P12M` → "12 months", `P36M` → "3 years", `P1Y` → "1 year",
 * `P90D` → "90 days". Falls back to the raw value if the pattern
 * doesn't match — AWS's schema calls it a free string, not strictly
 * ISO 8601, so we defensively keep the raw value visible.
 *
 * Only single-unit periods are formatted. A mixed period like `P1Y6M` has no
 * unambiguous short rendering, so the raw value is shown rather than a
 * misleading approximation.
 */
export const formatSelectorValue = (selectorValue: string): string => {
  if (!selectorValue) { return ''; }
  const match = /^P(?:(?<years>\d+)Y)?(?:(?<months>\d+)M)?(?:(?<days>\d+)D)?$/u
    .exec(selectorValue);
  if (!match) { return selectorValue; }
  const { years, months, days } = match.groups ?? {};

  // Count how many units the period actually carries; only a lone unit is
  // formatted. Replaces three near-identical `x && !y && !z` guards, which is
  // what pushed this function over the complexity limit.
  const present = [years, months, days].filter(Boolean);
  if (present.length !== SINGLE_ITEM) { return selectorValue; }

  if (years) {
    const n = Number(years);
    return n === ONE_YEAR ? '1 year' : `${n} years`;
  }
  if (months) { return formatMonths(Number(months)); }
  const n = Number(days);
  return n === ONE_DAY ? '1 day' : `${n} days`;
};

const formatPrice = (price: string, currency: string): string => {
  const num = Number(price);
  if (!Number.isFinite(num)) { return `${price} ${currency}`; }
  if (num === ZERO_TOTAL) { return `${currency} 0.00`; }
  // Contract prices are usually whole numbers (e.g. 10000 for $10k).
  // Preserve up to 2 decimals but drop trailing zeros.
  if (Number.isInteger(num)) {
    return `${currency} ${num.toLocaleString()}`;
  }
  return `${currency} ${num.toFixed(MONEY_DECIMALS)}`;
};

/**
 * Compute the total price for a card given the current buyer quantities.
 * Sum(price[d] * quantity[d]) across all dimensions.
 *
 * `selectedDimensionKeys` restricts the sum to the dimensions actually being
 * purchased. For a `multipleDimensionSelection=Disallowed` card that is a
 * single dimension, so the total must not include the ones the buyer did not
 * pick — otherwise the displayed total is for an agreement AWS would reject.
 */
const computeCardTotal = (
  card: ParsedRateCard,
  quantities: Record<string, number>,
  selectedDimensionKeys?: ReadonlySet<string>,
): number => {
  return card.dimensions.reduce((sum, d) => {
    if (selectedDimensionKeys && !selectedDimensionKeys.has(d.dimensionKey)) {
      return sum;
    }
    const q = quantities[d.dimensionKey] ?? MIN_QUANTITY;
    const p = Number(d.price);
    return sum + (Number.isFinite(p) ? p * q : ZERO_TOTAL);
  }, ZERO_TOTAL);
};

/**
 * Cheapest single dimension on a card, at quantity 1.
 *
 * Used to preview a `multipleDimensionSelection=Disallowed` card, which can
 * only ever be bought one dimension at a time — summing all of its dimensions
 * would advertise a price the buyer cannot be charged.
 *
 * Returns 0 for a card with no dimensions: `Math.min(...[])` is `Infinity`,
 * which would render as a garbage price.
 */
const cheapestDimensionPrice = (card: ParsedRateCard): number => {
  if (card.dimensions.length === EMPTY) { return ZERO_TOTAL; }
  return Math.min(
    ...card.dimensions.map((d) => {
      const p = Number(d.price);
      return Number.isFinite(p) ? p : ZERO_TOTAL;
    }),
  );
};

/**
 * Parse a buyer-typed quantity string.
 *
 * Returns the number only when the WHOLE string is a positive integer.
 * `Number.parseInt` is not usable on its own here: it happily reads `'3abc'`
 * as `3` and `'1.9'` as `1`, so a typo silently becomes a different quantity
 * than the one on screen. An empty string is `null` (invalid) rather than 0 —
 * the buyer is mid-edit, not asking for zero units.
 */
export const parseQuantity = (valueStr: string): number | null => {
  const trimmed = valueStr.trim();
  if (!/^\d+$/u.test(trimmed)) { return null; }
  const parsed = Number(trimmed);
  if (!Number.isSafeInteger(parsed) || parsed < MIN_QUANTITY) { return null; }
  return parsed;
};

// ----------------------------------------------------------------------------
// Component
// ----------------------------------------------------------------------------

/**
 * Build the configuration to emit upward, or `null` when it is not valid.
 *
 * VALIDATES FIRST, then builds. Coercing before checking would make the
 * check unreachable. `null` is what disables the wizard's Next button, so
 * a buyer cannot carry an invalid quantity into a quote.
 */
const buildContractConfig = (
  termId: string,
  card: ParsedRateCard | undefined,
  activeDimensions: ParsedRateCardDimension[],
  quantityInputs: Record<string, string>,
  hasQuantityError: boolean,
): ContractPricingConfig | null => {
  if (!card) { return null; }
  if (hasQuantityError || activeDimensions.length === EMPTY) { return null; }
  return {
    termId,
    selectorValue: card.selectorValue,
    dimensions: activeDimensions.map((d) => ({
      dimensionKey: d.dimensionKey,
      dimensionValue: card.quantityConfigurationAllowed
        ? parseQuantity(quantityInputs[d.dimensionKey] ?? '') ?? MIN_QUANTITY
        : FIXED_QUANTITY,
    })),
  };
};

/** Radio label for a rate card: "12 months", or "Users: 50" for non-Duration. */
const rateCardLabel = (card: ParsedRateCard): string => {
  const formatted = formatSelectorValue(card.selectorValue) || card.selectorValue;
  return card.selectorType && card.selectorType !== 'Duration'
    ? `${card.selectorType}: ${formatted}`
    : formatted;
};

/**
 * Radio description for a rate card: a base-quantity price preview.
 *
 * A `multipleDimensionSelection=Disallowed` card can only be bought one
 * dimension at a time, so previewing the sum of ALL its dimensions would
 * advertise a price the buyer can never be charged. Show the cheapest single
 * dimension instead.
 */
const rateCardDescription = (card: ParsedRateCard): string => {
  const baseQuantities = Object.fromEntries(
    card.dimensions.map((d) => [d.dimensionKey, MIN_QUANTITY]),
  );
  const amount = card.multipleDimensionSelectionAllowed
    ? computeCardTotal(card, baseQuantities)
    : cheapestDimensionPrice(card);
  const suffix = card.multipleDimensionSelectionAllowed
    ? 'total (base quantity)'
    : 'from (per dimension)';
  return `${formatPrice(String(amount), card.currency)} ${suffix}`;
};

/**
 * The dimensions actually being purchased on a card.
 *
 * `multipleDimensionSelection=Allowed` → every dimension on the card.
 * `Disallowed` → exactly the one the buyer selected (falling back to the
 * first, so the list is never empty for a card that has dimensions).
 */
const resolveActiveDimensions = (
  card: ParsedRateCard | undefined,
  selectedDimensionKey: string,
): ParsedRateCardDimension[] => {
  if (!card) { return []; }
  if (card.multipleDimensionSelectionAllowed) { return card.dimensions; }
  const picked = card.dimensions.find((d) => d.dimensionKey === selectedDimensionKey);
  return picked ? [picked] : card.dimensions.slice(FIRST_ITEM_INDEX, SINGLE_ITEM);
};

/**
 * Per-dimension validity of the buyer's typed quantities.
 *
 * Only meaningful when the card allows quantity configuration; a
 * `quantityConfiguration=Disallowed` card is fixed at 1 per dimension and has
 * no input to get wrong.
 */
const resolveQuantityErrors = (
  card: ParsedRateCard | undefined,
  activeDimensions: ParsedRateCardDimension[],
  quantityInputs: Record<string, string>,
): Record<string, boolean> => {
  if (!card?.quantityConfigurationAllowed) { return {}; }
  const errors: Record<string, boolean> = {};
  activeDimensions.forEach((d) => {
    errors[d.dimensionKey] = parseQuantity(quantityInputs[d.dimensionKey] ?? '') === null;
  });
  return errors;
};

/**
 * True when an existing buyer configuration belongs to this rate card.
 *
 * A selector value such as `P12M` is only unique within one term, so the
 * term id must match as well. Comparing the selector alone let a config
 * restored for another term seed this card's quantities.
 */
const configMatchesCard = (
  config: ContractPricingConfig | null,
  termId: string,
  card: ParsedRateCard | undefined,
): boolean => !!config && !!card
  && config.termId === termId
  && config.selectorValue === card.selectorValue;

/** Index of the card matching an existing config, else the first card. */
const initialCardIndexFor = (
  config: ContractPricingConfig | null,
  termId: string,
  rateCards: ParsedRateCard[],
): number => {
  const idx = rateCards.findIndex((c) => configMatchesCard(config, termId, c));
  return idx >= FIRST_ITEM_INDEX ? idx : FIRST_ITEM_INDEX;
};

/** Quantity inputs seeded from an existing config, else 1 per dimension. */
const initialQuantitiesFor = (
  config: ContractPricingConfig | null,
  termId: string,
  card: ParsedRateCard,
): Record<string, string> => {
  const q: Record<string, string> = {};
  card.dimensions.forEach((d) => { q[d.dimensionKey] = String(MIN_QUANTITY); });
  if (configMatchesCard(config, termId, card)) {
    config?.dimensions.forEach((d) => {
      if (d.dimensionKey in q) { q[d.dimensionKey] = String(d.dimensionValue); }
    });
  }
  return q;
};

/** The dimension an existing single-dimension config selected, else the first. */
const initialDimensionKeyFor = (
  config: ContractPricingConfig | null,
  termId: string,
  card: ParsedRateCard,
): string => {
  if (configMatchesCard(config, termId, card) && config?.dimensions.length === SINGLE_ITEM) {
    return config.dimensions[FIRST_ITEM_INDEX].dimensionKey;
  }
  return card.dimensions[FIRST_ITEM_INDEX]?.dimensionKey ?? '';
};

interface DimensionRowProps {
  dimension: ParsedRateCardDimension,
  currency: string,
  quantityAllowed: boolean,
  value: string,
  invalid: boolean,
  onQuantityChange: (dimensionKey: string, value: string) => void,
}

/**
 * One purchasable dimension: name, unit price, and either a quantity input or
 * a fixed "× 1" label.
 *
 * Extracted from the step body to bring that function under the repo's
 * complexity limit. The quantity input is only rendered when the rate card's
 * `quantityConfiguration` constraint allows it.
 */
const DimensionRow: FC<DimensionRowProps> = ({
  dimension,
  currency,
  quantityAllowed,
  value,
  invalid,
  onQuantityChange,
}) =>
  <SpaceBetween size="xs" direction="horizontal">
    <Box variant="strong" data-test={`dim-name-${dimension.dimensionKey}`}>
      {dimension.displayName || dimension.dimensionKey}
    </Box>
    <Box color="text-body-secondary">
      @ {formatPrice(dimension.price, currency)}
      {dimension.unit ? ` / ${dimension.unit}` : ''}
    </Box>
    {quantityAllowed ?
      <div style={{ width: '180px' }}>
        <FormField
          errorText={invalid ? i18n.configurePricingQuantityInvalidError : undefined}
          data-test={`dim-qty-field-${dimension.dimensionKey}`}
        >
          <Input
            value={value}
            onChange={({ detail }) => onQuantityChange(dimension.dimensionKey, detail.value)}
            type="number"
            inputMode="numeric"
            invalid={invalid}
            data-test={`dim-qty-${dimension.dimensionKey}`}
          />
        </FormField>
      </div>
      :
      <Box data-test={`dim-qty-readonly-${dimension.dimensionKey}`}>
        × 1 (fixed)
      </Box>
    }
  </SpaceBetween>
;

interface DimensionsSectionProps {
  card: ParsedRateCard,
  activeDimensions: ParsedRateCardDimension[],
  selectedDimensionKey: string,
  onDimensionKeyChange: (key: string) => void,
  quantityInputs: Record<string, string>,
  quantityErrors: Record<string, boolean>,
  onQuantityChange: (dimensionKey: string, value: string) => void,
}

/**
 * The dimensions block: an optional single-select (for
 * `multipleDimensionSelection=Disallowed` cards with more than one dimension)
 * followed by one row per purchasable dimension.
 *
 * Extracted wholesale from the step body, which carried enough JSX branching
 * to exceed the repo's complexity limit. Rendered only when the card has
 * dimensions, so `card` is non-optional here.
 */
const DimensionsSection: FC<DimensionsSectionProps> = ({
  card,
  activeDimensions,
  selectedDimensionKey,
  onDimensionKeyChange,
  quantityInputs,
  quantityErrors,
  onQuantityChange,
}) => {
  const needsSingleSelect = !card.multipleDimensionSelectionAllowed
    && card.dimensions.length > SINGLE_ITEM;
  return (
    <div>
      <Box variant="awsui-key-label">
        {card.multipleDimensionSelectionAllowed
          ? i18n.configurePricingDimensionsLabel
          : i18n.configurePricingSingleDimensionLabel}
      </Box>
      {needsSingleSelect &&
        <>
          <Box variant="small" color="text-body-secondary">
            {i18n.configurePricingSingleDimensionHint}
          </Box>
          <RadioGroup
            value={selectedDimensionKey}
            onChange={({ detail }) => onDimensionKeyChange(detail.value)}
            items={card.dimensions.map((d) => ({
              value: d.dimensionKey,
              label: d.displayName || d.dimensionKey,
              description: `${formatPrice(d.price, card.currency)}`
                + `${d.unit ? ` / ${d.unit}` : ''}`,
            }))}
            data-test="configure-pricing-dimension-selector"
          />
        </>
      }
      <SpaceBetween size="xs">
        {activeDimensions.map((d) =>
          <DimensionRow
            key={d.dimensionKey}
            dimension={d}
            currency={card.currency}
            quantityAllowed={card.quantityConfigurationAllowed}
            value={quantityInputs[d.dimensionKey] ?? ''}
            invalid={quantityErrors[d.dimensionKey] ?? false}
            onQuantityChange={onQuantityChange}
          />
        )}
      </SpaceBetween>
    </div>
  );
};


interface ConfigurePricingFormProps {
  termId: string,
  rateCards: ParsedRateCard[],
  onConfigChange: (config: ContractPricingConfig | null) => void,
  config: ContractPricingConfig | null,
}

/** The rate-card and quantity form, rendered once a term with cards exists. */
const ConfigurePricingForm: FC<ConfigurePricingFormProps> = ({
  termId,
  rateCards,
  onConfigChange,
  config,
}) => {
  // Local state: currently-selected card index (as string for RadioGroup)
  // and per-dimensionKey quantity.
  //
  // Default selection: use existing `config` if it matches one of the
  // parsed cards, otherwise pick the first card.
  const initialCardIdx = useMemo(
    () => initialCardIndexFor(config, termId, rateCards),
    [rateCards, config, termId],
  );
  const [selectedCardIdx, setSelectedCardIdx] = useState<number>(initialCardIdx);

  // Quantities are held as the RAW STRING the buyer typed, not as a coerced
  // number. Coercing on every keystroke (clamping invalid input, or
  // `Math.max(1, ...)` when building the payload) would silently change what
  // the buyer typed: `0` or `-5` would be sent as `1`, `1.9` as `1`, `3abc`
  // as `3`, and validation would run on the coerced value, so it could never
  // fail and Next would never be disabled. Keeping the raw string means the
  // input shows exactly what was typed, and validation decides whether it is
  // usable.
  const initialQuantityInputs = useMemo(
    () => initialQuantitiesFor(config, termId, rateCards[initialCardIdx]),
    [rateCards, initialCardIdx, config, termId],
  );
  const [quantityInputs, setQuantityInputs] = useState<Record<string, string>>(
    initialQuantityInputs,
  );

  const selectedCard = rateCards[selectedCardIdx];

  // multipleDimensionSelection=Disallowed → AWS rejects a configuration
  // carrying more than one dimension, so the buyer must pick exactly one. The
  // constraint was parsed into `multipleDimensionSelectionAllowed` and then
  // never read — the step always submitted EVERY dimension on the card. For a
  // Disallowed card with more than one dimension that is a guaranteed AWS 400
  // at the end of the wizard, after the buyer has agreed to terms.
  //
  // Default to the first dimension; switching cards resets it below.
  const [selectedDimensionKey, setSelectedDimensionKey] = useState<string>(
    () => initialDimensionKeyFor(config, termId, rateCards[initialCardIdx]),
  );

  /**
   * The dimensions actually being purchased on the selected card.
   *
   * `multipleDimensionSelection=Allowed` → every dimension on the card.
   * `Disallowed` → exactly the one the buyer selected.
   *
   * A single-dimension card is unaffected either way, which is the common
   * case; the distinction only bites on multi-dimension Disallowed cards.
   */
  const activeDimensions = useMemo(
    () => resolveActiveDimensions(selectedCard, selectedDimensionKey),
    [selectedCard, selectedDimensionKey],
  );

  const activeDimensionKeys = useMemo(
    () => new Set(activeDimensions.map((d) => d.dimensionKey)),
    [activeDimensions],
  );

  /**
   * Per-dimension validity of the buyer's typed quantity, for the dimensions
   * that are actually being purchased.
   *
   * Only meaningful when the card allows quantity configuration; a
   * `quantityConfiguration=Disallowed` card is fixed at 1 per dimension and
   * has no input to get wrong.
   */
  const quantityErrors = useMemo(
    () => resolveQuantityErrors(selectedCard, activeDimensions, quantityInputs),
    [selectedCard, activeDimensions, quantityInputs],
  );

  const hasQuantityError = Object.values(quantityErrors).some(Boolean);

  // Whenever selection or quantities change, emit the new config upward.
  useEffect(() => {
    onConfigChange(buildContractConfig(
      termId,
      selectedCard,
      activeDimensions,
      quantityInputs,
      hasQuantityError,
    ));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    selectedCardIdx,
    quantityInputs,
    selectedCard,
    termId,
    activeDimensions,
    hasQuantityError,
  ]);

  // When the user switches card, reset quantities to the new card's dimensions.
  const handleCardChange = (newIdxStr: string) => {
    const newIdx = Number(newIdxStr);
    setSelectedCardIdx(newIdx);
    const newCard = rateCards[newIdx];
    const q: Record<string, string> = {};
    newCard.dimensions.forEach((d) => { q[d.dimensionKey] = '1'; });
    setQuantityInputs(q);
    // The previous card's dimension keys need not exist on the new card, so a
    // carried-over selection could leave `activeDimensions` empty.
    setSelectedDimensionKey(newCard.dimensions[0]?.dimensionKey ?? '');
  };

  const handleQuantityChange = (dimensionKey: string, valueStr: string) => {
    // Store verbatim. Validation happens in `quantityErrors`; coercing here
    // would send a quantity the buyer did not type.
    setQuantityInputs((prev) => ({ ...prev, [dimensionKey]: valueStr }));
  };

  const totalPrice = useMemo(
    () => computeCardTotal(
      selectedCard,
      // Invalid entries contribute their last valid meaning of nothing: the
      // total is only displayed alongside an error, and Next is disabled.
      Object.fromEntries(
        activeDimensions.map((d) => [
          d.dimensionKey,
          parseQuantity(quantityInputs[d.dimensionKey] ?? '') ?? ZERO_TOTAL,
        ]),
      ),
      activeDimensionKeys,
    ),
    [selectedCard, quantityInputs, activeDimensions, activeDimensionKeys],
  );

  return (
    <SpaceBetween size="l">
      <Container header={<Header variant="h2">{i18n.configurePricingHeader}</Header>}>
        <SpaceBetween size="m">
          <Box variant="p" color="text-body-secondary">
            {i18n.configurePricingDescription}
          </Box>

          <div>
            <Box variant="awsui-key-label">{i18n.configurePricingSelectorLabel}</Box>
            <RadioGroup
              value={String(selectedCardIdx)}
              onChange={({ detail }) => handleCardChange(detail.value)}
              items={rateCards.map((card, idx) => ({
                value: String(idx),
                label: rateCardLabel(card),
                description: rateCardDescription(card),
              }))}
              data-test="configure-pricing-selector"
            />
          </div>

          {selectedCard.dimensions.length > EMPTY &&
            <DimensionsSection
              card={selectedCard}
              activeDimensions={activeDimensions}
              selectedDimensionKey={selectedDimensionKey}
              onDimensionKeyChange={setSelectedDimensionKey}
              quantityInputs={quantityInputs}
              quantityErrors={quantityErrors}
              onQuantityChange={handleQuantityChange}
            />
          }

          <div>
            <Box variant="awsui-key-label">{i18n.configurePricingTotalLabel}</Box>
            <Box variant="h3" data-test="configure-pricing-total">
              {hasQuantityError
                ? '—'
                : formatPrice(String(totalPrice), selectedCard.currency)}
              {selectedCard.selectorValue && !hasQuantityError ?
                <Box variant="span" color="text-body-secondary">
                  {' '}for {formatSelectorValue(selectedCard.selectorValue) || selectedCard.selectorValue}
                </Box>
                : null}
            </Box>
          </div>

          <Alert type="info">
            {i18n.configurePricingRenewalHint}
          </Alert>
        </SpaceBetween>
      </Container>
    </SpaceBetween>
  );
};

export const ProcurementStepConfigurePricing: FC<Props> = ({
  offer,
  isLoading,
  onConfigChange,
  config,
}) => {
  // Hooks run before any early return (rules-of-hooks); both helpers accept
  // a missing offer or term.
  const term = useMemo(() => findConfigurableUpfrontTerm(offer), [offer]);
  const rateCards = useMemo(() => parseRateCards(term), [term]);

  if (isLoading) {
    return <Box textAlign="center"><Spinner /></Box>;
  }
  if (!offer) {
    return <Alert type="warning">{i18n.configurePricingNoOfferHint}</Alert>;
  }
  if (!term || rateCards.length === EMPTY) {
    return (
      <Alert type="error" data-test="configure-pricing-no-cupt">
        {i18n.configurePricingNoRateCardsError}
      </Alert>
    );
  }

  // Keyed on the term so a different offer starts from fresh local state
  // instead of carrying over card and quantity choices for another term.
  return (
    <ConfigurePricingForm
      key={term.termId}
      termId={term.termId}
      rateCards={rateCards}
      onConfigChange={onConfigChange}
      config={config}
    />
  );
};
