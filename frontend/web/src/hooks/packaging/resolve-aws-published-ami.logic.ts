// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import useSWR from 'swr';
import { useRecoilValue } from 'recoil';
import {
  ResolveAwsPublishedAmiResponse,
} from '../../services/API/aws-published-ami-api';
import { selectedProjectState } from '../../state';

export interface AwsPublishedAmiServiceAPI {
  resolveAwsPublishedAmi: (
    projectId: string, listingId: string,
  ) => Promise<ResolveAwsPublishedAmiResponse>,
}

const RESOLVE_KEY = (projectId?: string, listingId?: string) => {
  if (!projectId || !listingId) { return null; }
  return [`projects/${projectId}/images/aws-published/resolve`, projectId, listingId];
};

/**
 * Resolve an AWS-published Marketplace listing to the AMI(s) it offers.
 *
 * Unlike the neighbouring hooks this raises no notification on failure: the
 * import step renders the backend's message inline and blocks the wizard
 * there, so a toast would only repeat it.
 */
export const useResolveAwsPublishedAmi = ({
  serviceApi,
  listingId,
  enabled = true,
}: {
  serviceApi?: AwsPublishedAmiServiceAPI,
  listingId: string | null,
  enabled?: boolean,
}) => {
  const selectedProject = useRecoilValue(selectedProjectState);

  const fetcher = ([, projectId, id]: [string, string, string]) => {
    if (!serviceApi) { return Promise.reject(new Error('No AWS-published client')); }
    return serviceApi.resolveAwsPublishedAmi(projectId, id);
  };

  const key = enabled && listingId && serviceApi
    ? RESOLVE_KEY(selectedProject.projectId, listingId)
    : null;

  const { data, isLoading, error } = useSWR(key, fetcher, {
    shouldRetryOnError: false,
  });

  return {
    resolution: data || null,
    isLoading,
    error: error instanceof Error ? error : null,
  };
};
