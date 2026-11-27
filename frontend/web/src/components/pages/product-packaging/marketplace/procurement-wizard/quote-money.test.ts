// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { describe, it, expect } from 'vitest';
import { formatQuoteCurrency, formatQuoteMoney, isMissingContractEstimate } from './quote-money';

describe('formatQuoteMoney', () => {
  it('shows value and currency', () => {
    expect(formatQuoteMoney('400.00', 'USD', 'CONTRACT')).toBe('400.00 USD');
    expect(formatQuoteMoney('0', 'USD', 'FREE')).toBe('0 USD');
  });

  it('keeps a value whose currency is missing', () => {
    expect(formatQuoteMoney('400.00', null, 'CONTRACT')).toBe('400.00 (currency unknown)');
    expect(formatQuoteMoney('12', undefined, 'USAGE')).toBe('12 (currency unknown)');
  });

  it('calls a missing CONTRACT estimate unavailable', () => {
    expect(formatQuoteMoney(null, 'USD', 'CONTRACT')).toBe('Estimate unavailable');
    expect(formatQuoteMoney('', null, 'CONTRACT')).toBe('Estimate unavailable');
  });

  it.each(['USAGE', 'FREE', 'BYOL'] as const)('calls a missing %s estimate usage-based', (flow) => {
    expect(formatQuoteMoney(null, null, flow)).toBe('Usage-based pricing (see terms)');
  });
});

describe('formatQuoteCurrency', () => {
  it('distinguishes an unknown CONTRACT currency from usage-based pricing', () => {
    expect(formatQuoteCurrency('EUR', 'CONTRACT')).toBe('EUR');
    expect(formatQuoteCurrency(null, 'CONTRACT')).toBe('(currency unknown)');
    expect(formatQuoteCurrency(null, 'USAGE')).toBe('Usage-based pricing (see terms)');
  });
});

describe('isMissingContractEstimate', () => {
  it('is true only for CONTRACT without a value', () => {
    expect(isMissingContractEstimate(null, 'CONTRACT')).toBe(true);
    expect(isMissingContractEstimate('1', 'CONTRACT')).toBe(false);
    expect(isMissingContractEstimate(null, 'USAGE')).toBe(false);
  });
});
