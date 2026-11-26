// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from 'react';
import { renderHook, act } from '@testing-library/react';
import { RecoilRoot } from 'recoil';
import { describe, it, expect, vi } from 'vitest';
import { useCancelMarketplaceAgreement } from './use-cancel-marketplace-agreement.logic';

const ONCE = 1;

const wrapper = ({ children }: { children: React.ReactNode }) =>
  <RecoilRoot>{children}</RecoilRoot>
;

describe('useCancelMarketplaceAgreement', () => {
  it('cancels an agreement on success', async () => {
    const cancelAgreement = vi.fn().mockResolvedValue({ agreementId: 'agmt-1' });
    const { result } = renderHook(
      () => useCancelMarketplaceAgreement({ serviceApi: { cancelAgreement } }),
      { wrapper },
    );

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let payload: any;
    await act(async () => {
      payload = await result.current.run('agmt-1');
    });

    expect(payload?.agreementId).toBe('agmt-1');
    // Account-scoped: the agreement id is the ONLY argument. A projectId here
    // would be a scope the caller believes in and the backend never enforces.
    expect(cancelAgreement).toHaveBeenCalledWith('agmt-1');
    expect(cancelAgreement).toHaveBeenCalledTimes(ONCE);
  });

  it('surfaces error when cancellation fails', async () => {
    const cancelAgreement = vi.fn().mockRejectedValue(new Error('cant cancel'));
    const { result } = renderHook(
      () => useCancelMarketplaceAgreement({ serviceApi: { cancelAgreement } }),
      { wrapper },
    );

    await act(async () => {
      await result.current.run('agmt-1');
    });

    expect(result.current.error?.message).toBe('cant cancel');
  });
});
