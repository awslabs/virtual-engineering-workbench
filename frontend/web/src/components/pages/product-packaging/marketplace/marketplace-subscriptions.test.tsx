// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { RecoilRoot, SetRecoilState } from 'recoil';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { selectedProjectState } from '../../../../state';

// Mock the SWR-based hook that fetches subscriptions. Each test seeds
// its own mock return value before rendering, then the component reads
// it synchronously.
const mockUseDiscover = vi.fn();
vi.mock('../../../../hooks/packaging/discover-marketplace-subscriptions.logic', () => ({
  useDiscoverMarketplaceSubscriptions: (opts: unknown) => mockUseDiscover(opts),
}));

// Import after mock so the component picks up the mocked hook.
import { MarketplaceSubscriptions } from './marketplace-subscriptions';

type ServiceApiProp = React.ComponentProps<typeof MarketplaceSubscriptions>['serviceApi'];

const renderWithProviders = (serviceApi: object) => {
  const initializeState = ({ set }: { set: SetRecoilState }) => {
    set(selectedProjectState, { projectId: 'proj-1', projectName: 'Test' });
  };
  return render(
    <MemoryRouter>
      <RecoilRoot initializeState={initializeState}>
        <MarketplaceSubscriptions
          serviceApi={serviceApi as unknown as ServiceApiProp}
        />
      </RecoilRoot>
    </MemoryRouter>,
  );
};

const FRESH_SUBSCRIPTION = {
  productName: 'Fresh Product',
  productCode: 'pc-fresh',
  hubRegionAmiId: 'ami-fresh',
  // eslint-disable-next-line @typescript-eslint/naming-convention -- AWS region id
  regionalAmiIds: { 'us-east-1': 'ami-fresh' },
  subscriptionOwnership: 'VEW_MANAGED',
  alreadyImported: false,
  newerVersionAvailable: false,
};

const ALREADY_IMPORTED = {
  productName: 'Imported Product',
  productCode: 'pc-imported',
  hubRegionAmiId: 'ami-imported',
  // eslint-disable-next-line @typescript-eslint/naming-convention -- AWS region id
  regionalAmiIds: { 'us-east-1': 'ami-imported' },
  subscriptionOwnership: 'VEW_MANAGED',
  alreadyImported: true,
  newerVersionAvailable: false,
};

const UPDATE_AVAILABLE = {
  productName: 'Update Product',
  productCode: 'pc-update',
  hubRegionAmiId: 'ami-latest', // backend already overrode this to latest
  // eslint-disable-next-line @typescript-eslint/naming-convention -- AWS region id
  regionalAmiIds: { 'us-east-1': 'ami-latest' },
  subscriptionOwnership: 'VEW_MANAGED',
  alreadyImported: true,
  newerVersionAvailable: true,
  latestAmiId: 'ami-latest',
  latestAmiCreationDate: '2026-06-01T00:00:00Z',
};

describe('MarketplaceSubscriptions page — smoke tests', () => {
  beforeEach(() => {
    mockUseDiscover.mockReset();
  });

  it('renders the subscription row for a fresh product', () => {
    mockUseDiscover.mockReturnValue({
      subscriptions: [FRESH_SUBSCRIPTION],
      isLoading: false,
      discover: vi.fn(),
    });
    renderWithProviders({ discoverMarketplaceSubscriptions: vi.fn() });
    expect(screen.getByText('Fresh Product')).toBeInTheDocument();
    expect(screen.getByText('Available')).toBeInTheDocument();
  });

  it('renders the subscription row for an already-imported product', () => {
    mockUseDiscover.mockReturnValue({
      subscriptions: [ALREADY_IMPORTED],
      isLoading: false,
      discover: vi.fn(),
    });
    renderWithProviders({ discoverMarketplaceSubscriptions: vi.fn() });
    expect(screen.getByText('Imported Product')).toBeInTheDocument();
    expect(screen.getByText('Imported')).toBeInTheDocument();
  });

  it('shows "Update available" status when a newer AMI version exists', () => {
    // When `newerVersionAvailable === true`, the Status column must
    // surface the "Update available" warning rather than the plain
    // "Imported" success indicator.
    mockUseDiscover.mockReturnValue({
      subscriptions: [UPDATE_AVAILABLE],
      isLoading: false,
      discover: vi.fn(),
    });
    renderWithProviders({ discoverMarketplaceSubscriptions: vi.fn() });
    expect(screen.getByText('Update Product')).toBeInTheDocument();
    expect(screen.getByText('Update available')).toBeInTheDocument();
    // The "Imported" status is NOT shown when a newer version is available —
    // otherwise the user would see two contradictory status indicators.
    expect(screen.queryByText('Imported')).not.toBeInTheDocument();
  });
});
