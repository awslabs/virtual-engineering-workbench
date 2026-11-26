// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Import Image wizard tests — marketplace deep-link handoff.
//
// The wizard normally starts on step 0 (source picker) with imageSource
// = EXISTING_AMI. When the URL carries ?source=marketplace (deep-link
// from the Marketplace procurement wizard's success step), we skip the
// picker and land on step 1 (AMI picker) with MARKETPLACE_PRODUCT
// already selected. When it also carries the purchased product's id, the
// matching subscription is preselected.

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { RecoilRoot, SetRecoilState } from 'recoil';
import { SWRConfig } from 'swr';
import { describe, it, expect, vi } from 'vitest';
import { useImportImageWizard } from './import-image-wizard.logic';
import { selectedProjectState } from '../../../../state';
import { DiscoveredMarketplaceSubscription } from
  '../../../../services/API/proserve-wb-packaging-api';

const NO_DEDUPING = 0;

const STEP_SOURCE = 0;
const STEP_AMI = 1;

const mockServiceApi = {
  importImage: vi.fn(),
  discoverMarketplaceSubscriptions: vi.fn().mockResolvedValue({ subscriptions: [] }),
  listImportableAmis: vi.fn().mockResolvedValue({ amis: [] }),
};

const makeWrapper = (initialEntries: string[]) => {
  const initializeState = ({ set }: { set: SetRecoilState }) => {
    set(selectedProjectState, { projectId: 'proj-1', projectName: 'Test' });
  };
  return ({ children }: { children: React.ReactNode }) =>
    <MemoryRouter initialEntries={initialEntries}>
      <RecoilRoot initializeState={initializeState}>
        <SWRConfig value={{ provider: () => new Map(), dedupingInterval: NO_DEDUPING }}>
          {children}
        </SWRConfig>
      </RecoilRoot>
    </MemoryRouter>
  ;
};

describe('useImportImageWizard — marketplace deep-link handoff', () => {
  it('starts on step 0 with EXISTING_AMI when no ?source= query param', () => {
    const wrapper = makeWrapper(['/projects/proj-1/images/import']);
    const { result } = renderHook(
      () => useImportImageWizard({ serviceApi: mockServiceApi }),
      { wrapper },
    );
    expect(result.current.activeStepIndex).toBe(STEP_SOURCE);
    expect(result.current.imageSource).toBe('EXISTING_AMI');
  });

  it('starts on step 1 with MARKETPLACE_PRODUCT when ?source=marketplace', () => {
    const wrapper = makeWrapper(['/projects/proj-1/images/import?source=marketplace']);
    const { result } = renderHook(
      () => useImportImageWizard({ serviceApi: mockServiceApi }),
      { wrapper },
    );
    expect(result.current.activeStepIndex).toBe(STEP_AMI);
    expect(result.current.imageSource).toBe('MARKETPLACE_PRODUCT');
  });

  it('ignores unknown ?source= values (defaults to EXISTING_AMI)', () => {
    const wrapper = makeWrapper(['/projects/proj-1/images/import?source=bogus']);
    const { result } = renderHook(
      () => useImportImageWizard({ serviceApi: mockServiceApi }),
      { wrapper },
    );
    expect(result.current.activeStepIndex).toBe(STEP_SOURCE);
    expect(result.current.imageSource).toBe('EXISTING_AMI');
  });
});

describe('useImportImageWizard — preselecting the purchased product', () => {
  const PURCHASED: DiscoveredMarketplaceSubscription = {
    productName: 'Ubuntu Noble',
    productCode: 'code-ubuntu',
    productId: 'prod-ubuntu123',
    hubRegionAmiId: 'ami-ubuntu',
    subscriptionOwnership: 'VEW_MANAGED',
    alreadyImported: false,
  };
  const OTHER: DiscoveredMarketplaceSubscription = {
    productName: 'Debian 12',
    productCode: 'code-debian',
    productId: 'prod-debian12',
    hubRegionAmiId: 'ami-debian',
    subscriptionOwnership: 'VEW_MANAGED',
    alreadyImported: false,
  };
  // Same name as the purchase, different seller's product.
  const SAME_NAME_OTHER_PRODUCT: DiscoveredMarketplaceSubscription = {
    ...PURCHASED,
    productCode: 'code-ubuntu-other-seller',
    productId: 'prod-otherseller9',
  };

  const renderWith = (search: string, subscriptions: DiscoveredMarketplaceSubscription[]) => {
    const serviceApi = {
      ...mockServiceApi,
      discoverMarketplaceSubscriptions: vi.fn().mockResolvedValue({ subscriptions }),
    };
    const wrapper = makeWrapper([`/projects/proj-1/images/import${search}`]);
    return renderHook(() => useImportImageWizard({ serviceApi }), { wrapper });
  };

  const HANDOFF = '?source=marketplace&productId=prod-ubuntu123';

  it('preselects the subscription with the hand-off product id', async () => {
    const { result } = renderWith(HANDOFF, [OTHER, SAME_NAME_OTHER_PRODUCT, PURCHASED]);

    await waitFor(() => expect(result.current.handoffStatus).toBe('selected'));
    expect(result.current.selectedSubscription?.productCode).toBe('code-ubuntu');
    expect(result.current.imageName).toBe('Ubuntu Noble');
    expect(result.current.canProceedFromStep(STEP_AMI)).toBe(true);
  });

  it('does not preselect a same-named subscription for another product', async () => {
    const { result } = renderWith(HANDOFF, [OTHER, SAME_NAME_OTHER_PRODUCT]);

    await waitFor(() => expect(result.current.handoffStatus).toBe('unavailable'));
    expect(result.current.selectedSubscription).toBeNull();
    expect(result.current.activeStepIndex).toBe(STEP_AMI);
  });

  it('reports an already-imported, up-to-date subscription as such', async () => {
    const { result } = renderWith(HANDOFF, [{ ...PURCHASED, alreadyImported: true }]);

    await waitFor(() => expect(result.current.handoffStatus).toBe('alreadyImported'));
    expect(result.current.selectedSubscription).toBeNull();
  });

  it('preselects an imported subscription that has a newer version', async () => {
    const { result } = renderWith(
      HANDOFF,
      [{ ...PURCHASED, alreadyImported: true, newerVersionAvailable: true }],
    );

    await waitFor(() => expect(result.current.handoffStatus).toBe('selected'));
    expect(result.current.selectedSubscription?.productCode).toBe('code-ubuntu');
  });

  it.each([
    ['a malformed product id', '?source=marketplace&productId=..%2Fadmin'],
    ['a missing product id', '?source=marketplace'],
  ])('ignores a hand-off with %s and shows the plain picker', async (_label, search) => {
    const listed = [PURCHASED];
    const { result } = renderWith(search, listed);

    // Wait for the list itself, so a match would have had its chance.
    await waitFor(() => expect(result.current.subscriptions).toHaveLength(listed.length));
    expect(result.current.handoffStatus).toBe('none');
    expect(result.current.selectedSubscription).toBeNull();
    expect(result.current.imageSource).toBe('MARKETPLACE_PRODUCT');
  });
});
