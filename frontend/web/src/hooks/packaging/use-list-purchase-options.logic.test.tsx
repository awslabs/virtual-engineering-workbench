// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { RecoilRoot, SetRecoilState } from 'recoil';
import { SWRConfig } from 'swr';
import { describe, it, expect, vi } from 'vitest';
import { selectedProjectState } from '../../state';
import { useListPurchaseOptions } from './use-list-purchase-options.logic';

const NO_DEDUPING = 0;
const ONE = 1;
const NONE = 0;

const wrapperWithProject = (projectId: string) => ({ children }: { children: React.ReactNode }) => {
  const initializeState = ({ set }: { set: SetRecoilState }) => {
    set(selectedProjectState, { projectId });
  };
  return (
    <RecoilRoot initializeState={initializeState}>
      <SWRConfig value={{ provider: () => new Map(), dedupingInterval: NO_DEDUPING }}>
        {children}
      </SWRConfig>
    </RecoilRoot>
  );
};

describe('useListPurchaseOptions', () => {
  it('returns the purchase-options list on success', async () => {
    const listPurchaseOptions = vi.fn().mockResolvedValue({
      purchaseOptions: [
        {
          purchaseOptionId: 'po-1',
          purchaseOptionType: 'OFFER',
          catalog: 'AWSMarketplace',
          offerId: 'offer-1',
          productId: 'prod-1',
          productName: 'Test AMI',
        },
      ],
    });
    const { result } = renderHook(
      () => useListPurchaseOptions({ serviceApi: { listPurchaseOptions } }),
      { wrapper: wrapperWithProject('proj-1') },
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toHaveLength(ONE);
    expect(result.current.data[0].offerId).toBe('offer-1');
  });

  it('exposes error state on failure', async () => {
    const listPurchaseOptions = vi.fn().mockRejectedValue(new Error('nope'));
    const { result } = renderHook(
      () => useListPurchaseOptions({ serviceApi: { listPurchaseOptions } }),
      { wrapper: wrapperWithProject('proj-1') },
    );

    await waitFor(() => expect(result.current.error).toBeDefined());
    expect(result.current.data).toHaveLength(NONE);
  });
});
