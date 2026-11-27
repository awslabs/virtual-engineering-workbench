// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { RecoilRoot, SetRecoilState } from 'recoil';
import { SWRConfig } from 'swr';
import { describe, it, expect, vi } from 'vitest';
import { BrowseMarketplace } from './browse-marketplace';
import { selectedProjectState } from '../../../../state';
import {
  SearchMarketplaceListingsResponse,
  GetMarketplaceFacetsResponse,
} from '../../../../services/API/marketplace-listings-api';

type ServiceApiProp = React.ComponentProps<typeof BrowseMarketplace>['serviceApi'];

const NO_DEDUPING = 0;
const NONE = 0;
const ONE = 1;

const renderWithProviders = (serviceApi: {
  searchListings: () => Promise<SearchMarketplaceListingsResponse>,
  getFacets: () => Promise<GetMarketplaceFacetsResponse>,
}) => {
  const initializeState = ({ set }: { set: SetRecoilState }) => {
    set(selectedProjectState, { projectId: 'proj-1', projectName: 'Test' });
  };
  return render(
    <MemoryRouter>
      <RecoilRoot initializeState={initializeState}>
        <SWRConfig value={{ provider: () => new Map(), dedupingInterval: NO_DEDUPING }}>
          <BrowseMarketplace serviceApi={serviceApi as unknown as ServiceApiProp} />
        </SWRConfig>
      </RecoilRoot>
    </MemoryRouter>,
  );
};

describe('BrowseMarketplace page', () => {
  it('renders returned listings as tiles with pricing badge', async () => {
    const searchListings = vi.fn().mockResolvedValue({
      listings: [
        {
          listingId: 'prodview-1',
          listingName: 'Ubuntu 24.04 LTS',
          catalog: 'AWSMarketplace',
          shortDescription: 'Official Ubuntu LTS.',
          publisher: { sellerProfileId: 's1', displayName: 'Canonical' },
          categories: [],
          fulfillmentOptionSummaries: [
            { fulfillmentOptionType: 'AMAZON_MACHINE_IMAGE', displayName: 'AMI' },
          ],
          pricingModels: [{ pricingModelType: 'FREE', displayName: 'Free' }],
          badges: [],
          reviewSummary: [],
          primaryOfferId: 'offer-1',
          primaryProductId: 'prod-1',
        },
      ],
      nextToken: null,
      totalResults: ONE,
    });
    const getFacets = vi.fn().mockResolvedValue({ facets: {}, totalResults: ONE });

    renderWithProviders({ searchListings, getFacets });

    await waitFor(() => {
      expect(screen.getByText('Ubuntu 24.04 LTS')).toBeTruthy();
    });
    expect(screen.getByText('Free')).toBeTruthy();
    expect(searchListings).toHaveBeenCalled();
    expect(getFacets).toHaveBeenCalled();
  });

  it('renders an empty state when no listings match', async () => {
    const searchListings = vi.fn().mockResolvedValue({
      listings: [], nextToken: null, totalResults: NONE,
    });
    const getFacets = vi.fn().mockResolvedValue({ facets: {}, totalResults: NONE });

    renderWithProviders({ searchListings, getFacets });

    await waitFor(() => {
      expect(screen.getByText('No listings match your filters')).toBeTruthy();
    });
    // The link-out button to the AWS Marketplace website should be present.
    expect(screen.getByText(/Open AWS Marketplace/u)).toBeTruthy();
  });

  it('does not leak stale listings across filter changes (pagination race)', async () => {
    // After the user changes filters mid-fetch, SWR's `keepPreviousData`
    // briefly returns the old-filter page while the new one is in flight.
    // The accumulator must NOT include the old data once the new page arrives.

    const makeListing = (id: string, name: string) => ({
      listingId: id,
      listingName: name,
      catalog: 'AWSMarketplace',
      publisher: { sellerProfileId: 's', displayName: 'Test' },
      categories: [],
      fulfillmentOptionSummaries: [],
      pricingModels: [],
      badges: [],
      reviewSummary: [],
      primaryOfferId: null,
      primaryProductId: null,
    });

    // First call: initial page. Second call: post-search-submit page.
    // We fire the search *after* the initial page has rendered, then
    // assert the old listing is gone from the DOM.
    const searchListings = vi.fn()
      .mockResolvedValueOnce({
        listings: [makeListing('l-old', 'Old Filter Result')],
        nextToken: null,
        totalResults: ONE,
      })
      .mockResolvedValue({
        listings: [makeListing('l-new', 'New Filter Result')],
        nextToken: null,
        totalResults: ONE,
      });
    const getFacets = vi.fn().mockResolvedValue({ facets: {}, totalResults: ONE });

    renderWithProviders({ searchListings, getFacets });

    await waitFor(() => {
      expect(screen.getByText('Old Filter Result')).toBeTruthy();
    });

    // User types + submits a new search. This changes `appliedSearchText`
    // which changes `filterKey`, which must reset the accumulator.
    fireEvent.change(
      screen.getByPlaceholderText(/Search AMI products/u),
      { target: { value: 'new query' } },
    );
    // The Search button — there's only one button labelled 'Search'.
    fireEvent.click(screen.getByText('Search'));

    await waitFor(() => {
      expect(screen.getByText('New Filter Result')).toBeTruthy();
    });
    // The old filter's listing must be gone. If the useEffect append
    // guard is missing, the accumulator would still contain 'l-old'.
    expect(screen.queryByText('Old Filter Result')).toBeNull();
  });
});
