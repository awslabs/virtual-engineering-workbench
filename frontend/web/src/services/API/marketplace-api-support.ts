// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Shared plumbing for the Marketplace API wrappers: the generated packaging
// client, the bearer token, and the mapping of a failed response to an error
// that carries the HTTP status and the backend's error code.
import { Amplify } from 'aws-amplify';
import { getAccessToken } from '..';
import { Configuration, DefaultApi, ResponseError } from './proserve-wb-packaging-api';

const PACKAGING_API_NAME = 'PackagingAPI';

export function prepareClient(): DefaultApi {
  const config = Amplify.getConfig();
  const basePath = config.API?.REST?.[PACKAGING_API_NAME]?.endpoint || '';
  return new DefaultApi(new Configuration({ basePath }));
}

export async function bearer(): Promise<string> {
  return `Bearer ${await getAccessToken()}`;
}

export type ApiErrorFactory<E extends Error> = (message: string, status: number, code?: string) => E;

async function errorFromResponse<E extends Error>(
  error: ResponseError,
  makeError: ApiErrorFactory<E>,
): Promise<E> {
  const { response } = error;
  let body: { message?: string, code?: string } = {};
  try {
    body = await response.json();
  } catch {
    /* the body is not JSON; fall back to the status */
  }
  return makeError(
    body.message || `Request failed with status ${response.status}`,
    response.status,
    body.code,
  );
}

/**
 * Run one generated-client call. A non-2xx response is rethrown as the
 * wrapper's own error type; any other failure (network, abort) is rethrown
 * unchanged.
 */
export async function callApi<T, E extends Error>(
  call: (api: DefaultApi, authorization: string) => Promise<T>,
  makeError: ApiErrorFactory<E>,
): Promise<T> {
  const authorization = await bearer();
  try {
    return await call(prepareClient(), authorization);
  } catch (e) {
    if (e instanceof ResponseError) {
      throw await errorFromResponse(e, makeError);
    }
    throw e;
  }
}
