// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { RecoilRoot, SetRecoilState } from 'recoil';
import { SWRConfig } from 'swr';
import { describe, it, expect, vi } from 'vitest';
import { MarketplaceAgreements } from './marketplace-agreements';
import { selectedProjectState } from '../../../../state';

type ServiceApiProp = React.ComponentProps<typeof MarketplaceAgreements>['serviceApi'];

const NO_DEDUPING = 0;
const NONE = 0;

const renderWithProviders = (serviceApi: {
  listMarketplaceAgreements: (projectId: string) => Promise<unknown>,
}) => {
  const initializeState = ({ set }: { set: SetRecoilState }) => {
    set(selectedProjectState, { projectId: 'proj-1', projectName: 'Test' });
  };
  return render(
    <MemoryRouter>
      <RecoilRoot initializeState={initializeState}>
        <SWRConfig value={{ provider: () => new Map(), dedupingInterval: NO_DEDUPING }}>
          <MarketplaceAgreements
            serviceApi={serviceApi as unknown as ServiceApiProp}
          />
        </SWRConfig>
      </RecoilRoot>
    </MemoryRouter>,
  );
};

describe('MarketplaceAgreements page', () => {
  it('renders agreements returned by the service', async () => {
    const listMarketplaceAgreements = vi.fn().mockResolvedValue({
      agreements: [
        {
          agreementId: 'agmt-1',
          productId: 'prod-1',
          offerId: 'offer-1',
          status: 'ACTIVE',
          acceptanceDate: '2026-01-01',
        },
      ],
    });

    renderWithProviders({ listMarketplaceAgreements });

    await waitFor(() => expect(screen.getByText('agmt-1')).toBeInTheDocument());
    expect(screen.getByText('ACTIVE')).toBeInTheDocument();
  });

  it('renders productName / offerName / pricingModelType when the server enriched the row', async () => {
    const listMarketplaceAgreements = vi.fn().mockResolvedValue({
      agreements: [
        {
          agreementId: 'agmt-2',
          productId: 'prod-2',
          offerId: 'offer-2',
          status: 'ACTIVE',
          acceptanceDate: '2026-01-01',
          productName: 'Ubuntu 24.04 LTS - Noble',
          offerName: 'Ubuntu Noble standard offer',
          pricingModelType: 'FREE',
        },
      ],
    });

    renderWithProviders({ listMarketplaceAgreements });

    // Human-readable names surface in the primary cell text.
    await waitFor(() => expect(screen.getByText('Ubuntu 24.04 LTS - Noble')).toBeInTheDocument());
    expect(screen.getByText('Ubuntu Noble standard offer')).toBeInTheDocument();
    expect(screen.getByText('FREE')).toBeInTheDocument();
    // Raw IDs still available as subtitle for support / debugging.
    expect(screen.getByText('prod-2')).toBeInTheDocument();
    expect(screen.getByText('offer-2')).toBeInTheDocument();
  });

  it('falls back to raw IDs when server-side enrichment yielded no names', async () => {
    const listMarketplaceAgreements = vi.fn().mockResolvedValue({
      agreements: [
        {
          agreementId: 'agmt-3',
          productId: 'prod-3',
          offerId: 'offer-3',
          status: 'ACTIVE',
          acceptanceDate: '2026-01-01',
          // productName / offerName / pricingModelType all undefined
        },
      ],
    });

    renderWithProviders({ listMarketplaceAgreements });

    // Fallback path: raw IDs render in the primary cell text.
    await waitFor(() => expect(screen.getByText('prod-3')).toBeInTheDocument());
    expect(screen.getByText('offer-3')).toBeInTheDocument();
  });

  it('renders an empty state when no agreements are returned', async () => {
    const listMarketplaceAgreements = vi.fn().mockResolvedValue({ agreements: [] });

    renderWithProviders({ listMarketplaceAgreements });

    await waitFor(() => expect(screen.getAllByText(/No agreements/iu).length).toBeGreaterThan(NONE));
  });
});
