// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { RecoilRoot } from 'recoil';
import { SWRConfig } from 'swr';
import { describe, it, expect, vi } from 'vitest';
import { useListMarketplaceAgreements } from './use-list-marketplace-agreements.logic';

const NO_DEDUPING = 0;
const ONE = 1;
const NONE = 0;

// No project is seeded: this hook is account-scoped and must not depend on a
// selected project at all.
const wrapper = ({ children }: { children: React.ReactNode }) =>

  <RecoilRoot>
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: NO_DEDUPING }}>
      {children}
    </SWRConfig>
  </RecoilRoot>
  ;

describe('useListMarketplaceAgreements', () => {
  it('returns the list of agreements on success', async () => {
    const listMarketplaceAgreements = vi.fn().mockResolvedValue({
      agreements: [
        { agreementId: 'agmt-1', productId: 'prod-1', offerId: 'offer-1', status: 'ACTIVE' },
      ],
    });
    const serviceApi = { listMarketplaceAgreements };

    const { result } = renderHook(
      () => useListMarketplaceAgreements({ serviceApi }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toHaveLength(ONE);
    expect(result.current.data[0].agreementId).toBe('agmt-1');
    // Account-scoped: called with NO arguments. The backend does not scope
    // agreements by project, so a projectId argument would mislead.
    expect(listMarketplaceAgreements).toHaveBeenCalledWith();
  });

  it('fetches without a selected project, because agreements are account-level', async () => {
    const listMarketplaceAgreements = vi.fn().mockResolvedValue({ agreements: [] });
    // No `result` binding — this test asserts on the service call, not hook state.
    renderHook(
      () => useListMarketplaceAgreements({ serviceApi: { listMarketplaceAgreements } }),
      { wrapper },
    );

    // An account-level resource must not be gated on a project selection:
    // the request is made even with no project selected.
    await waitFor(() => expect(listMarketplaceAgreements).toHaveBeenCalled());
  });

  it('surfaces errors from the service call', async () => {
    const listMarketplaceAgreements = vi.fn().mockRejectedValue(new Error('boom'));
    const serviceApi = { listMarketplaceAgreements };

    const { result } = renderHook(
      () => useListMarketplaceAgreements({ serviceApi }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.error).toBeDefined());
    expect(result.current.data).toHaveLength(NONE);
  });
});
