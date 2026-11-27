// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// AWS-published AMI resolve client.
//
// Products AWS sells itself (Windows Server, RHEL, SUSE, Ubuntu Pro, Amazon
// Linux) have no buyer-side subscription, so they never appear in the
// Marketplace subscriptions list. Resolve reads the AMI back from the
// listing instead. Wraps the ResolveAwsPublishedAmi operation of the
// generated packaging client.
import { AwsPublishedAmiCandidateItem, ResolveAwsPublishedAmiResponse } from './proserve-wb-packaging-api';
import { callApi } from './marketplace-api-support';

export type { ResolveAwsPublishedAmiResponse };
/** One AMI the listing's product can be imported from. */
export type AwsPublishedAmiCandidate = AwsPublishedAmiCandidateItem;

class AwsPublishedAmiApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = 'AwsPublishedAmiApiError';
    this.status = status;
    this.code = code;
  }
}

const makeError = (message: string, status: number, code?: string) =>
  new AwsPublishedAmiApiError(message, status, code);

export const awsPublishedAmiAPI = {
  /**
   * Resolve a listing to the AMI(s) it can be imported from. Read-only. The
   * backend returns 400 when the listing needs a subscription first, or when
   * no AMI can be identified for its product; the message explains which.
   * When `unambiguous` is false, `resolved` is absent and the user must
   * choose from `candidates`, which differ by architecture.
   */
  resolveAwsPublishedAmi: (
    projectId: string,
    listingId: string,
  ): Promise<ResolveAwsPublishedAmiResponse> =>
    callApi(
      (api, authorization) => api.resolveAwsPublishedAmi({
        authorization,
        projectId,
        resolveAwsPublishedAmiRequest: { listingId },
      }),
      makeError,
    ),
};

export type AwsPublishedAmiAPI = typeof awsPublishedAmiAPI;
export { AwsPublishedAmiApiError };

// `resolved` can arrive as null: the backend serialises an absent value that
// way and the generated model passes it through.
type ResolutionView = Omit<ResolveAwsPublishedAmiResponse, 'resolved'>
  & { resolved?: AwsPublishedAmiCandidate | null };

/**
 * The AMIs the picker offers. An unambiguous product shows only the AMI the
 * backend resolved; an ambiguous one shows every candidate so the user
 * chooses, because they differ by architecture.
 */
export const pickableCandidates = (
  resolution: ResolutionView | null,
): AwsPublishedAmiCandidate[] => {
  if (!resolution) { return []; }
  if (resolution.resolved) { return [resolution.resolved]; }
  return resolution.candidates || [];
};

/**
 * Platform implied by the AMI's EC2 PlatformDetails ("Windows", "Red Hat
 * Enterprise Linux", "Linux/UNIX"). Everything that is not Windows is
 * imported as Linux.
 */
export const platformFromDetails = (details?: string | null): 'Windows' | 'Linux' =>
  (details || '').toLowerCase().includes('windows') ? 'Windows' : 'Linux';
