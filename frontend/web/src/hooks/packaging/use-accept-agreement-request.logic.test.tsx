// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from 'react';
import { renderHook, act } from '@testing-library/react';
import { RecoilRoot } from 'recoil';
import { describe, it, expect, vi } from 'vitest';
import { useAcceptAgreementRequest } from './use-accept-agreement-request.logic';
import {
  AcceptAgreementRequestResponse,
  ProcurementApiError,
} from '../../services/API/marketplace-procurement-api';

const wrapper = ({ children }: { children: React.ReactNode }) =>
  <RecoilRoot>{children}</RecoilRoot>
;

const HTTP_BAD_REQUEST = 400;
const HTTP_INTERNAL_ERROR = 500;

describe('useAcceptAgreementRequest', () => {
  it('returns the durable agreementId on success', async () => {
    const acceptAgreementRequest = vi.fn().mockResolvedValue({ agreementId: 'agmt-1' });
    const { result } = renderHook(
      () => useAcceptAgreementRequest({ serviceApi: { acceptAgreementRequest } }),
      { wrapper },
    );

    let payload: AcceptAgreementRequestResponse | null = null;
    await act(async () => {
      payload = await result.current.run('ar-1');
    });

    // Vitest's async `act` narrows `let` bindings to `never` after the closure;
    // cast back to the actual type for the assertion.
    const observed = payload as AcceptAgreementRequestResponse | null;
    expect(observed?.agreementId).toBe('agmt-1');
    expect(result.current.data?.agreementId).toBe('agmt-1');
  });

  it('exposes error when accept fails', async () => {
    const acceptAgreementRequest = vi.fn().mockRejectedValue(new Error('nope'));
    const { result } = renderHook(
      () => useAcceptAgreementRequest({ serviceApi: { acceptAgreementRequest } }),
      { wrapper },
    );

    await act(async () => {
      await result.current.run('ar-1');
    });

    expect(result.current.error?.message).toBe('nope');
    expect(result.current.data).toBeNull();
    // Non-ProcurementApiError: no status/code/isClientError populated.
    expect(result.current.error?.status).toBeUndefined();
    expect(result.current.error?.isClientError).toBeUndefined();
  });

  it('surfaces status, code, and isClientError from ProcurementApiError on 4xx', async () => {
    const acceptAgreementRequest = vi.fn().mockRejectedValue(
      new ProcurementApiError('quote no longer valid', HTTP_BAD_REQUEST, 'ExpiredResourceException'),
    );
    const { result } = renderHook(
      () => useAcceptAgreementRequest({ serviceApi: { acceptAgreementRequest } }),
      { wrapper },
    );

    await act(async () => {
      await result.current.run('ar-1');
    });

    expect(result.current.error?.status).toBe(HTTP_BAD_REQUEST);
    expect(result.current.error?.code).toBe('ExpiredResourceException');
    expect(result.current.error?.isClientError).toBe(true);
  });

  it('flags 5xx as not a client error', async () => {
    const acceptAgreementRequest = vi.fn().mockRejectedValue(
      new ProcurementApiError('internal', HTTP_INTERNAL_ERROR, 'InternalServerError'),
    );
    const { result } = renderHook(
      () => useAcceptAgreementRequest({ serviceApi: { acceptAgreementRequest } }),
      { wrapper },
    );

    await act(async () => {
      await result.current.run('ar-1');
    });

    expect(result.current.error?.status).toBe(HTTP_INTERNAL_ERROR);
    expect(result.current.error?.isClientError).toBe(false);
  });

  it('reset() clears data and error', async () => {
    const acceptAgreementRequest = vi.fn().mockResolvedValue({ agreementId: 'agmt-1' });
    const { result } = renderHook(
      () => useAcceptAgreementRequest({ serviceApi: { acceptAgreementRequest } }),
      { wrapper },
    );

    await act(async () => {
      await result.current.run('ar-1');
    });
    expect(result.current.data?.agreementId).toBe('agmt-1');

    act(() => {
      result.current.reset();
    });
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });
});
