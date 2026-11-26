// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from 'react';
import { renderHook, act } from '@testing-library/react';
import { RecoilRoot } from 'recoil';
import { describe, it, expect, vi } from 'vitest';
import { useGetMarketplaceOffer } from './use-get-marketplace-offer.logic';

const wrapper = ({ children }: { children: React.ReactNode }) =>
  <RecoilRoot>{children}</RecoilRoot>
;

describe('useGetMarketplaceOffer', () => {
  it('loads the offer + terms on success', async () => {
    const getOffer = vi.fn().mockResolvedValue({
      offerId: 'offer-1',
      catalog: 'AWSMarketplace',
      agreementProposalId: 'ap-1',
      associatedProducts: [],
      terms: [{ termId: 'term-1', termType: 'LegalTerm', rawTerm: {} }],
    });
    const { result } = renderHook(
      () => useGetMarketplaceOffer({ serviceApi: { getOffer }, projectId: 'proj-1' }),
      { wrapper },
    );

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let payload: any;
    await act(async () => {
      payload = await result.current.run('offer-1');
    });

    expect(payload?.offerId).toBe('offer-1');
    expect(getOffer).toHaveBeenCalledWith('proj-1', 'offer-1');
    expect(result.current.data?.offerId).toBe('offer-1');
  });

  it('captures errors and surfaces them', async () => {
    const getOffer = vi.fn().mockRejectedValue(new Error('offer bust'));
    const { result } = renderHook(
      () => useGetMarketplaceOffer({ serviceApi: { getOffer }, projectId: 'proj-1' }),
      { wrapper },
    );

    await act(async () => {
      await result.current.run('offer-1');
    });

    expect(result.current.error?.message).toBe('offer bust');
    expect(result.current.data).toBeNull();
  });
});
