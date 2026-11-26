// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from 'react';
import { renderHook, act } from '@testing-library/react';
import { RecoilRoot } from 'recoil';
import { describe, it, expect, vi } from 'vitest';
import { useCreateAgreementRequest } from './use-create-agreement-request.logic';

const wrapper = ({ children }: { children: React.ReactNode }) =>
  <RecoilRoot>{children}</RecoilRoot>
;

describe('useCreateAgreementRequest', () => {
  it('creates a quote on success and returns the id', async () => {
    const createAgreementRequest = vi.fn().mockResolvedValue({
      agreementRequestId: 'ar-1',
      estimatedAgreementValue: '100',
      estimatedCurrencyCode: 'USD',
    });
    const { result } = renderHook(
      () => useCreateAgreementRequest({
        serviceApi: { createAgreementRequest },
        projectId: 'proj-1',
      }),
      { wrapper },
    );

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let payload: any;
    await act(async () => {
      payload = await result.current.run('offer-1', { requestedTerms: [{ id: 'term-1' }] });
    });

    expect(payload?.agreementRequestId).toBe('ar-1');
    expect(createAgreementRequest).toHaveBeenCalledWith(
      'proj-1',
      'offer-1',
      { requestedTerms: [{ id: 'term-1' }] },
    );
  });

  it('surfaces errors when creating a quote fails', async () => {
    const createAgreementRequest = vi.fn().mockRejectedValue(new Error('quote fail'));
    const { result } = renderHook(
      () => useCreateAgreementRequest({
        serviceApi: { createAgreementRequest },
        projectId: 'proj-1',
      }),
      { wrapper },
    );

    await act(async () => {
      await result.current.run('offer-1', { requestedTerms: [] });
    });

    expect(result.current.error?.message).toBe('quote fail');
    expect(result.current.data).toBeNull();
  });
});

// A quote is a priced commitment, so a response for a superseded request must
// never become the quote the Accept step reads. `reset()` cannot cancel an
// HTTP request already in flight, so the hook tracks a monotonic request id and
// drops any settled response that is no longer the current one.
describe('useCreateAgreementRequest in-flight supersede', () => {
  /** A promise plus the handles to settle it later. */
  const deferred = <T, >() => {
    let resolve!: (v: T) => void;
    let reject!: (e: unknown) => void;
    const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
    return { promise, resolve, reject };
  };

  it('discards a response that resolves after reset()', async () => {
    const first = deferred<{ agreementRequestId: string }>();
    const createAgreementRequest = vi.fn().mockReturnValue(first.promise);
    const { result } = renderHook(
      () => useCreateAgreementRequest({
        serviceApi: { createAgreementRequest },
        projectId: 'proj-1',
      }),
      { wrapper },
    );

    // Fire a request but do NOT settle it yet.
    let runPromise!: Promise<unknown>;
    act(() => {
      runPromise = result.current.run('offer-1', { requestedTerms: [{ id: 'old-config' }] });
    });
    expect(result.current.isLoading).toBe(true);

    // The buyer changes their pricing configuration — the wizard resets.
    act(() => {
      result.current.reset();
    });
    // isLoading must clear too: the request it referred to is now disowned, and
    // a stuck flag would wedge the wizard's Next button forever.
    expect(result.current.isLoading).toBe(false);

    // Only now does the abandoned request come back.
    await act(async () => {
      first.resolve({ agreementRequestId: 'ar-stale' });
      await runPromise;
    });

    // THE ASSERTION THAT MATTERS: the stale quote did not land.
    expect(result.current.data).toBeNull();
  });

  it('keeps only the latest response when two requests overlap', async () => {
    const first = deferred<{ agreementRequestId: string }>();
    const second = deferred<{ agreementRequestId: string }>();
    const createAgreementRequest = vi.fn()
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const { result } = renderHook(
      () => useCreateAgreementRequest({
        serviceApi: { createAgreementRequest },
        projectId: 'proj-1',
      }),
      { wrapper },
    );

    let firstRun!: Promise<unknown>;
    let secondRun!: Promise<unknown>;
    act(() => {
      firstRun = result.current.run('offer-1', { requestedTerms: [{ id: 'config-a' }] });
    });
    act(() => {
      secondRun = result.current.run('offer-1', { requestedTerms: [{ id: 'config-b' }] });
    });

    // The SECOND request resolves first, then the first arrives late — the
    // out-of-order case a naive "last setData wins" implementation gets wrong.
    await act(async () => {
      second.resolve({ agreementRequestId: 'ar-new' });
      await secondRun;
    });
    expect(result.current.data?.agreementRequestId).toBe('ar-new');

    await act(async () => {
      first.resolve({ agreementRequestId: 'ar-old' });
      await firstRun;
    });
    expect(result.current.data?.agreementRequestId).toBe('ar-new');
  });

  it('does not surface an error from a superseded request', async () => {
    const first = deferred<{ agreementRequestId: string }>();
    const createAgreementRequest = vi.fn().mockReturnValue(first.promise);
    const { result } = renderHook(
      () => useCreateAgreementRequest({
        serviceApi: { createAgreementRequest },
        projectId: 'proj-1',
      }),
      { wrapper },
    );

    let runPromise!: Promise<unknown>;
    act(() => {
      runPromise = result.current.run('offer-1', { requestedTerms: [] });
    });
    act(() => {
      result.current.reset();
    });
    await act(async () => {
      first.reject(new Error('stale config rejected'));
      await runPromise;
    });

    // Showing this error would blame the buyer's CURRENT configuration for a
    // failure that belongs to one they already abandoned.
    expect(result.current.error).toBeNull();
  });

  // Calibration: the guard must not break the ordinary single-request path.
  it('still stores the response when nothing supersedes it', async () => {
    const createAgreementRequest = vi.fn().mockResolvedValue({ agreementRequestId: 'ar-ok' });
    const { result } = renderHook(
      () => useCreateAgreementRequest({
        serviceApi: { createAgreementRequest },
        projectId: 'proj-1',
      }),
      { wrapper },
    );

    await act(async () => {
      await result.current.run('offer-1', { requestedTerms: [] });
    });

    expect(result.current.data?.agreementRequestId).toBe('ar-ok');
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });
});
