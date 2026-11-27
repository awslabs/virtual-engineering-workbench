// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
/* eslint-disable no-script-url -- these tests assert that `javascript:`
   URLs are REJECTED. The literal hostile scheme is the input under test;
   removing it would delete the security assertion. Scoped to this file. */
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import { RecoilRoot, SetRecoilState } from 'recoil';
import { SWRConfig } from 'swr';
import { describe, it, expect, vi } from 'vitest';
import { ListingDetail } from './listing-detail';
import { ProjectRoles, selectedProjectState } from '../../../../state';
import { GetMarketplaceListingResponse } from '../../../../services/API/marketplace-listings-api';

const NO_DEDUPING = 0;
const NONE = 0;

/** Exposes the current query string so navigation can be asserted on. */
const LocationProbe = () => {
  const location = useLocation();
  return <div data-test="location-search">{location.search}</div>;
};

/** The query string the router is currently on. */
const probeSearch = (): string =>
  document.querySelector('[data-test="location-search"]')?.textContent || '';

const renderWithProviders = (
  getListing: (projectId: string, listingId: string) => Promise<GetMarketplaceListingResponse>,
  listingId = 'prodview-1',
  roles: ProjectRoles[] = [ProjectRoles.Admin],
) => {
  const initializeState = ({ set }: { set: SetRecoilState }) => {
    set(selectedProjectState, { projectId: 'proj-1', projectName: 'Test', roles });
  };
  return render(
    <MemoryRouter initialEntries={[`/projects/proj-1/marketplace/listings/${listingId}`]}>
      <RecoilRoot initializeState={initializeState}>
        <SWRConfig value={{ provider: () => new Map(), dedupingInterval: NO_DEDUPING }}>
          <LocationProbe />
          <Routes>
            <Route
              path="/projects/:projectId/marketplace/listings/:listingId"
              element={<ListingDetail serviceApi={{ getListing }} />}
            />
            <Route path="*" element={<div>navigated</div>} />
          </Routes>
        </SWRConfig>
      </RecoilRoot>
    </MemoryRouter>,
  );
};

const makeListing = (
  overrides: Partial<GetMarketplaceListingResponse> = {},
): GetMarketplaceListingResponse => ({
  listingId: 'prodview-1',
  listingName: 'Ubuntu 24.04 LTS',
  catalog: 'AWSMarketplace',
  shortDescription: 'Short description here.',
  longDescription: 'Long description with details.',
  publisher: { sellerProfileId: 's1', displayName: 'Canonical' },
  categories: [{ categoryId: 'c1', displayName: 'Operating Systems' }],
  fulfillmentOptionSummaries: [
    { fulfillmentOptionType: 'AMAZON_MACHINE_IMAGE', displayName: 'AMI' },
  ],
  pricingModels: [{ pricingModelType: 'FREE', displayName: 'Free' }],
  badges: [],
  highlights: ['Highlight A', 'Highlight B'],
  useCases: ['Use case X'],
  resources: [
    {
      resourceType: 'MANUFACTURER_INSTRUCTIONS', contentType: 'LINK',
      value: 'https://ubuntu.com/aws', displayName: 'Ubuntu on AWS'
    },
  ],
  associatedEntities: [{
    productId: 'prod-1', productName: 'Ubuntu',
    productManufacturer: { sellerProfileId: 's1', displayName: 'Canonical' },
    offerId: 'offer-1',
    offerSellerOfRecord: { sellerProfileId: 's1', displayName: 'Canonical' },
  }],
  primaryOfferId: 'offer-1',
  primaryProductId: 'prod-1',
  ...overrides,
});

describe('ListingDetail page', () => {
  it('renders product id, offer id, and the pricing-model-aware CTA enabled', async () => {
    const getListing = vi.fn().mockResolvedValue(makeListing());
    renderWithProviders(getListing);

    // "Ubuntu 24.04 LTS" appears in breadcrumb + H1, so getAllByText.
    await waitFor(() => {
      expect(screen.getAllByText('Ubuntu 24.04 LTS').length).toBeGreaterThan(NONE);
    });
    expect(screen.getByText('prod-1')).toBeTruthy();
    expect(screen.getByText('offer-1')).toBeTruthy();
    expect(screen.getByText('Highlight A')).toBeTruthy();
    expect(screen.getByText('Highlight B')).toBeTruthy();
    // Default fixture has pricingModels=[FREE]. FREE is a subscription like
    // any other, so the CTA reads "Subscribe" — same as pay-as-you-go.
    const getButtons = screen.getAllByText('Subscribe');
    expect(getButtons.length).toBeGreaterThan(NONE);
    const cta = getButtons[0].closest('button');
    expect(cta?.disabled).toBe(false);
  });

  it('disables the CTA for a role the offer and quote APIs refuse', async () => {
    const getListing = vi.fn().mockResolvedValue(makeListing());
    renderWithProviders(getListing, 'prodview-1', [ProjectRoles.ProductContributor]);

    await waitFor(() => {
      expect(screen.getAllByText('Subscribe').length).toBeGreaterThan(NONE);
    });
    const cta = screen.getAllByText('Subscribe')[0].closest('button');
    expect(cta?.disabled).toBe(true);
  });

  it('renders "Subscribe" CTA for USAGE-only listings', async () => {
    const getListing = vi.fn().mockResolvedValue(makeListing({
      pricingModels: [{ pricingModelType: 'USAGE', displayName: 'Usage' }],
    }));
    renderWithProviders(getListing);
    await waitFor(() => {
      expect(screen.getAllByText('Subscribe').length).toBeGreaterThan(NONE);
    });
  });

  it('renders "Buy contract" CTA for CONTRACT listings', async () => {
    const getListing = vi.fn().mockResolvedValue(makeListing({
      pricingModels: [{ pricingModelType: 'CONTRACT', displayName: 'Contract' }],
    }));
    renderWithProviders(getListing);
    await waitFor(() => {
      expect(screen.getAllByText('Buy contract').length).toBeGreaterThan(NONE);
    });
  });

  it('renders "Subscribe with own license" CTA for BYOL listings', async () => {
    const getListing = vi.fn().mockResolvedValue(makeListing({
      pricingModels: [{ pricingModelType: 'BYOL', displayName: 'BYOL' }],
    }));
    renderWithProviders(getListing);
    await waitFor(() => {
      expect(screen.getAllByText('Subscribe with own license').length).toBeGreaterThan(NONE);
    });
  });

  it('gives AWS-published listings a normal pricing CTA, not a "not supported" one', async () => {
    // Microsoft Windows Server 2022 Base: AWS is both publisher and Seller of
    // Record and the pricing model is FREE. Whether a subscription is
    // possible depends on the offer's terms, which this page does not load,
    // so the CTA reads off the pricing model like any other listing. The
    // procurement wizard it routes to resolves the offer and switches to a
    // direct import when there is no pricing term.
    const getListing = vi.fn().mockResolvedValue(makeListing({
      publisher: {
        sellerProfileId: 'e6a5002c-6dd0-4d1e-8196-0a1d1857229b',
        displayName: 'Amazon Web Services',
      },
      pricingModels: [{ pricingModelType: 'FREE', displayName: 'Free' }],
    }));
    renderWithProviders(getListing);
    await waitFor(() => {
      expect(screen.getAllByText('Subscribe').length).toBeGreaterThan(NONE);
    });
    // The superseded label promised the product could not be handled at all.
    expect(screen.queryByText('Not supported yet')).toBeNull();
    const cta = screen.getAllByText('Subscribe')[0].closest('button');
    expect(cta?.disabled).toBe(false);
  });

  it('carries the listing id to the procurement wizard so a direct import can resolve it', async () => {
    // The direct-import path starts from the listing, not the offer, so the
    // listing id has to survive the hand-off.
    const getListing = vi.fn().mockResolvedValue(makeListing({
      listingId: 'prodview-win2025',
      primaryOfferId: 'offer-1',
    }));
    renderWithProviders(getListing, 'prodview-win2025');
    await waitFor(() => {
      expect(screen.getAllByText('Subscribe').length).toBeGreaterThan(NONE);
    });
    const cta = screen.getAllByText('Subscribe')[0].closest('button');
    fireEvent.click(cta as HTMLButtonElement);
    await waitFor(() => {
      expect(probeSearch()).toContain('listingId=prodview-win2025');
    });
    expect(probeSearch()).toContain('offerId=offer-1');
  });

  it('disables the CTA when primaryOfferId is missing', async () => {
    const getListing = vi.fn().mockResolvedValue(makeListing({
      primaryOfferId: null,
      associatedEntities: [{
        productId: 'prod-1',
        productName: 'Ubuntu',
        offerId: null,
      }],
    }));
    renderWithProviders(getListing);

    await waitFor(() => {
      expect(screen.getAllByText('Ubuntu 24.04 LTS').length).toBeGreaterThan(NONE);
    });
    const cta = screen.getAllByText('Subscribe')[0].closest('button');
    expect(cta?.disabled).toBe(true);
    // Warning alert should surface.
    expect(screen.getAllByText('This listing has no purchasable offer.').length)
      .toBeGreaterThan(NONE);
  });

  it('renders an error state when the API call fails', async () => {
    const getListing = vi.fn().mockRejectedValue(new Error('Listing not found'));
    renderWithProviders(getListing);

    await waitFor(() => {
      expect(screen.getByText('Failed to load listing')).toBeTruthy();
    });
    // Retry button surfaces from EmptyGridNotification.
    expect(screen.getByText('Retry')).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// `resources[].value` is seller-controlled. Only allowlisted schemes may
// render as a live `<Link href=...>`; anything else renders as text.
// ---------------------------------------------------------------------------
describe('ListingDetail — seller-supplied resource URLs', () => {
  const resourceWith = (value: string) => makeListing({
    resources: [{
      resourceType: 'MANUFACTURER_INSTRUCTIONS',
      contentType: 'LINK',
      value,
      displayName: 'Vendor docs',
    }],
  });

  it('renders an https resource as a link', async () => {
    const getListing = vi.fn().mockResolvedValue(resourceWith('https://ubuntu.com/aws'));
    renderWithProviders(getListing);

    const link = await waitFor(() => screen.getByText('Vendor docs').closest('a'));
    expect(link).not.toBeNull();
    expect(link?.getAttribute('href')).toBe('https://ubuntu.com/aws');
  });

  it('does not render a javascript: resource as a link', async () => {
    const getListing = vi.fn().mockResolvedValue(resourceWith('javascript:alert(document.cookie)'));
    renderWithProviders(getListing);

    // The text still appears -- the user should see what the seller supplied --
    // but it must not be clickable.
    const label = await waitFor(() => screen.getByText('Vendor docs'));
    expect(label.closest('a')).toBeNull();
  });

  it('does not render a data: resource as a link', async () => {
    const getListing = vi.fn().mockResolvedValue(
      resourceWith('data:text/html,<script>alert(1)</script>'),
    );
    renderWithProviders(getListing);

    const label = await waitFor(() => screen.getByText('Vendor docs'));
    expect(label.closest('a')).toBeNull();
  });

  it('leaves no anchor anywhere carrying a javascript: href', async () => {
    // Broader assertion than the one above: catches the value leaking into a
    // different element than the one asserted on.
    const getListing = vi.fn().mockResolvedValue(resourceWith('javascript:alert(1)'));
    const { container } = renderWithProviders(getListing);

    await waitFor(() => screen.getByText('Vendor docs'));
    const hrefs = Array.from(container.querySelectorAll('a'))
      .map((a) => a.getAttribute('href') || '');
    expect(hrefs.some((h) => h.toLowerCase().includes('javascript:'))).toBe(false);
  });
});
