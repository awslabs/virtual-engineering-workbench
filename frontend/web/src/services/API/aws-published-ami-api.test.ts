// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Covers the AWS-published AMI resolve client: the call's shape, error
// handling, and the two pure helpers.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  awsPublishedAmiAPI,
  AwsPublishedAmiApiError,
  pickableCandidates,
  platformFromDetails,
  ResolveAwsPublishedAmiResponse,
} from './aws-published-ami-api';

const BASE = 'https://api.example.test';
const OK = 200;
const BAD_REQUEST = 400;
const SERVER_ERROR = 500;
const SINGLE_CALL = 1;
const FIRST_CALL = 0;
const FIRST_ARG = 0;
const SECOND_ARG = 1;

vi.mock('aws-amplify', () => ({
  Amplify: {
    getConfig: () => ({ API: { REST: { PackagingAPI: { endpoint: BASE } } } }),
  },
}));

vi.mock('..', () => ({
  getAccessToken: () => Promise.resolve('test-token'),
}));

const jsonResponse = (status: number, body: unknown): Response => ({
  ok: status === OK,
  status,
  json: () => Promise.resolve(body),
}) as Response;

const resolution = (
  overrides: Partial<ResolveAwsPublishedAmiResponse> = {},
): ResolveAwsPublishedAmiResponse => ({
  listingId: 'prodview-win2025',
  productId: 'prod-win2025',
  productName: 'Microsoft Windows Server 2025 Base',
  region: 'eu-west-1',
  unambiguous: true,
  resolved: {
    amiId: 'ami-111',
    amiName: 'Windows_Server-2025-English-Full-Base',
    ownerId: 'ownerid1234',
    architecture: 'x86_64',
    platformDetails: 'Windows',
    region: 'eu-west-1',
  },
  candidates: [],
  alreadyImportedAmiIds: [],
  ...overrides,
});

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

const lastCall = () => fetchMock.mock.calls[FIRST_CALL];
const lastUrl = (): string => String(lastCall()[FIRST_ARG]);
const lastInit = (): RequestInit => lastCall()[SECOND_ARG] as RequestInit;

describe('resolveAwsPublishedAmi', () => {
  it('POSTs the listing id to the resolve endpoint with an auth header', async () => {
    fetchMock.mockResolvedValue(jsonResponse(OK, resolution()));

    const res = await awsPublishedAmiAPI.resolveAwsPublishedAmi(
      'proj-1', 'prodview-win2025',
    );

    expect(fetchMock).toHaveBeenCalledTimes(SINGLE_CALL);
    expect(lastUrl()).toBe(
      `${BASE}/projects/proj-1/images/aws-published/resolve`,
    );
    expect(lastInit().method).toBe('POST');
    expect(JSON.parse(String(lastInit().body))).toEqual({
      listingId: 'prodview-win2025',
    });
    const headers = lastInit().headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer test-token');
    expect(res.productName).toBe('Microsoft Windows Server 2025 Base');
  });

  it('encodes the project id into the path', async () => {
    fetchMock.mockResolvedValue(jsonResponse(OK, resolution()));
    await awsPublishedAmiAPI.resolveAwsPublishedAmi('proj/1', 'prodview-x');
    expect(lastUrl()).toContain('/projects/proj%2F1/');
  });

  it('surfaces the backend message when a listing cannot be resolved', async () => {
    // The backend explains why (needs a subscription, several products...),
    // and that message is what the user has to act on.
    fetchMock.mockResolvedValue(jsonResponse(BAD_REQUEST, {
      message: 'No AMI could be identified for product prod-x.',
    }));

    await expect(
      awsPublishedAmiAPI.resolveAwsPublishedAmi('proj-1', 'prodview-x'),
    ).rejects.toThrow('No AMI could be identified for product prod-x.');
  });

  it('carries the status code on the error', async () => {
    fetchMock.mockResolvedValue(jsonResponse(BAD_REQUEST, { message: 'nope' }));
    await expect(
      awsPublishedAmiAPI.resolveAwsPublishedAmi('proj-1', 'prodview-x'),
    ).rejects.toBeInstanceOf(AwsPublishedAmiApiError);
    await expect(
      awsPublishedAmiAPI.resolveAwsPublishedAmi('proj-1', 'prodview-x'),
    ).rejects.toMatchObject({ status: BAD_REQUEST });
  });

  it('falls back to a status message when the error body is not JSON', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: SERVER_ERROR,
      json: () => Promise.reject(new Error('not json')),
    } as unknown as Response);

    await expect(
      awsPublishedAmiAPI.resolveAwsPublishedAmi('proj-1', 'prodview-x'),
    ).rejects.toThrow(`Request failed with status ${SERVER_ERROR}`);
  });
});

describe('pickableCandidates', () => {
  it('offers only the resolved AMI when the product is unambiguous', () => {
    // The other candidates are older builds of the same image.
    const res = resolution({
      candidates: [{
        amiId: 'ami-old',
        amiName: 'old',
        ownerId: 'ownerid1234',
        region: 'eu-west-1',
      }],
    });
    expect(pickableCandidates(res).map((c) => c.amiId)).toEqual(['ami-111']);
  });

  it('offers every candidate when nothing was resolved', () => {
    const res = resolution({
      unambiguous: false,
      resolved: undefined,
      candidates: [
        { amiId: 'ami-x86', amiName: 'x86', ownerId: 'o', region: 'eu-west-1' },
        { amiId: 'ami-arm', amiName: 'arm', ownerId: 'o', region: 'eu-west-1' },
      ],
    });
    expect(pickableCandidates(res).map((c) => c.amiId))
      .toEqual(['ami-x86', 'ami-arm']);
  });

  it('is empty before anything has resolved', () => {
    expect(pickableCandidates(null)).toEqual([]);
  });
});

describe('platformFromDetails', () => {
  it('maps Windows platform details to Windows', () => {
    expect(platformFromDetails('Windows')).toBe('Windows');
    expect(platformFromDetails('Windows with SQL Server Standard')).toBe('Windows');
  });

  it('maps everything else, including unknown values, to Linux', () => {
    expect(platformFromDetails('Red Hat Enterprise Linux')).toBe('Linux');
    expect(platformFromDetails('Linux/UNIX')).toBe('Linux');
    expect(platformFromDetails(null)).toBe('Linux');
    expect(platformFromDetails(undefined)).toBe('Linux');
  });
});
