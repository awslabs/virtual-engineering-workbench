// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Covers the Marketplace procurement and listings clients at the HTTP level:
// the generated client must send each operation to the path, method, headers
// and body the backend routes expect, and map a failed response to the
// wrapper's error type.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { marketplaceProcurementAPI, ProcurementApiError } from './marketplace-procurement-api';
import { marketplaceListingsAPI, ListingsApiError, facetValuesOf } from './marketplace-listings-api';

const BASE = 'https://api.example.test';
const OK = 200;
const BAD_REQUEST = 400;
const FIRST_CALL = 0;
const FIRST_ARG = 0;
const PAGE_SIZE = 20;
const TWO_FACET_VALUES = 2;
const ONE_FACET_VALUE = 1;
const SECOND_ARG = 1;

vi.mock('aws-amplify', () => ({
  Amplify: {
    getConfig: () => ({ API: { REST: { PackagingAPI: { endpoint: BASE } } } }),
  },
}));

vi.mock('..', () => ({
  getAccessToken: () => Promise.resolve('test-token'),
}));

const jsonResponse = (status: number, body: unknown): Response => new Response(
  JSON.stringify(body),
  { status },
);

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

const call = () => fetchMock.mock.calls[FIRST_CALL];
const url = (): string => String(call()[FIRST_ARG]);
const init = (): RequestInit => call()[SECOND_ARG] as RequestInit;
const header = (name: string): string | undefined =>
  (init().headers as Record<string, string>)[name];

describe('marketplaceProcurementAPI', () => {
  it('lists purchase options under the project with the bearer token', async () => {
    fetchMock.mockResolvedValue(jsonResponse(OK, { purchaseOptions: [] }));

    await marketplaceProcurementAPI.listPurchaseOptions('proj-1');

    expect(url()).toBe(`${BASE}/projects/proj-1/marketplace/purchase-options`);
    expect(init().method).toBe('GET');
    expect(header('Authorization')).toBe('Bearer test-token');
  });

  it('reads one offer under the project', async () => {
    fetchMock.mockResolvedValue(jsonResponse(OK, { offerId: 'offer-1', catalog: 'AWSMarketplace' }));

    await marketplaceProcurementAPI.getOffer('proj-1', 'offer-1');

    expect(url()).toBe(`${BASE}/projects/proj-1/marketplace/offers/offer-1`);
    expect(init().method).toBe('GET');
  });

  it('posts a quote with the product type, terms and client token', async () => {
    fetchMock.mockResolvedValue(jsonResponse(OK, { agreementRequestId: 'ar-1' }));

    await marketplaceProcurementAPI.createAgreementRequest('proj-1', 'offer-1', {
      requestedTerms: [{ id: 'term-1', configuration: { selectorValue: 'P12M' } }],
      clientToken: 'token-1',
    });

    expect(url()).toBe(`${BASE}/projects/proj-1/marketplace/offers/offer-1/quotes`);
    expect(init().method).toBe('POST');
    expect(JSON.parse(String(init().body))).toEqual({
      productType: 'AmiProduct',
      requestedTerms: [{ id: 'term-1', configuration: { selectorValue: 'P12M' } }],
      clientToken: 'token-1',
    });
  });

  it('accepts a quote on the account-scoped route, with no project in the path', async () => {
    fetchMock.mockResolvedValue(jsonResponse(OK, { agreementId: 'agmt-1' }));

    await marketplaceProcurementAPI.acceptAgreementRequest('ar-1');

    expect(url()).toBe(`${BASE}/marketplace/quotes/ar-1/accept`);
    expect(init().method).toBe('POST');
  });

  it('cancels an agreement on the account-scoped route', async () => {
    fetchMock.mockResolvedValue(jsonResponse(OK, { agreementId: 'agmt-1' }));

    await marketplaceProcurementAPI.cancelAgreement('agmt-1');

    expect(url()).toBe(`${BASE}/marketplace/agreements/agmt-1`);
    expect(init().method).toBe('DELETE');
  });

  it('maps a failed response to ProcurementApiError with status, code and message', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(BAD_REQUEST, { message: 'quote no longer valid', code: 'ExpiredResourceException' }),
    );

    const error = await marketplaceProcurementAPI.acceptAgreementRequest('ar-1').catch((e) => e);

    expect(error).toBeInstanceOf(ProcurementApiError);
    expect(error).toMatchObject({
      message: 'quote no longer valid',
      status: BAD_REQUEST,
      code: 'ExpiredResourceException',
    });
  });

  it('falls back to a status message when the error body is not JSON', async () => {
    fetchMock.mockResolvedValue(new Response('<html>', { status: BAD_REQUEST }));

    const error = await marketplaceProcurementAPI.cancelAgreement('agmt-1').catch((e) => e);

    expect(error).toBeInstanceOf(ProcurementApiError);
    expect(error.message).toBe(`Request failed with status ${BAD_REQUEST}`);
  });

  it('does not wrap a network failure', async () => {
    const failure = new TypeError('Failed to fetch');
    fetchMock.mockRejectedValue(failure);

    const error = await marketplaceProcurementAPI.listPurchaseOptions('proj-1').catch((e) => e);

    expect(error).not.toBeInstanceOf(ProcurementApiError);
  });
});

describe('marketplaceListingsAPI', () => {
  it('searches with repeated filter values and omits unset ones', async () => {
    fetchMock.mockResolvedValue(jsonResponse(OK, { listings: [] }));

    await marketplaceListingsAPI.searchListings('proj-1', {
      searchText: 'ubuntu',
      category: ['os', 'security'],
      maxResults: PAGE_SIZE,
    });

    const requested = new URL(url());
    expect(requested.pathname).toBe('/projects/proj-1/marketplace/listings');
    expect(requested.searchParams.get('searchText')).toBe('ubuntu');
    expect(requested.searchParams.getAll('category')).toEqual(['os', 'security']);
    expect(requested.searchParams.get('maxResults')).toBe(String(PAGE_SIZE));
    expect(requested.searchParams.has('nextToken')).toBe(false);
    expect(requested.searchParams.has('publisher')).toBe(false);
    expect(header('Authorization')).toBe('Bearer test-token');
  });

  it('sends no filter for an empty facet selection', async () => {
    // The browse page passes [] for every facet nothing is selected in.
    fetchMock.mockResolvedValue(jsonResponse(OK, { listings: [] }));

    await marketplaceListingsAPI.searchListings('proj-1', {
      category: [],
      pricingModel: [],
      publisher: [''],
      rating: [],
      maxResults: PAGE_SIZE,
    });

    const requested = new URL(url());
    expect([...requested.searchParams.keys()]).toEqual(['maxResults']);
  });

  it('sends no query string for an empty search', async () => {
    fetchMock.mockResolvedValue(jsonResponse(OK, { listings: [] }));

    await marketplaceListingsAPI.searchListings('proj-1');

    expect(url()).toBe(`${BASE}/projects/proj-1/marketplace/listings`);
  });

  it('reads one listing and the facets under the project', async () => {
    fetchMock.mockResolvedValue(jsonResponse(OK, { listingId: 'prodview-1' }));
    await marketplaceListingsAPI.getListing('proj-1', 'prodview-1');
    expect(url()).toBe(`${BASE}/projects/proj-1/marketplace/listings/prodview-1`);

    fetchMock.mockClear();
    fetchMock.mockResolvedValue(jsonResponse(OK, { facets: {} }));
    await marketplaceListingsAPI.getFacets('proj-1');
    expect(url()).toBe(`${BASE}/projects/proj-1/marketplace/facets`);
  });

  it('maps a failed response to ListingsApiError', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(BAD_REQUEST, { message: 'bad filter', code: 'ValidationError' }),
    );

    const error = await marketplaceListingsAPI.getFacets('proj-1').catch((e) => e);

    expect(error).toBeInstanceOf(ListingsApiError);
    expect(error).toMatchObject({ message: 'bad filter', status: BAD_REQUEST, code: 'ValidationError' });
  });
});

describe('facetValuesOf', () => {
  it('returns the values of a facet, or an empty list when it is missing', () => {
    const response = { facets: { category: [{ value: 'os', displayName: 'OS', count: TWO_FACET_VALUES }] } };

    expect(facetValuesOf(response, 'category')).toHaveLength(ONE_FACET_VALUE);
    expect(facetValuesOf(response, 'publisher')).toEqual([]);
    expect(facetValuesOf({}, 'category')).toEqual([]);
  });
});
