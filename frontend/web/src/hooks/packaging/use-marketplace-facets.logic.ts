// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import useSWR from 'swr';
import { useRecoilValue } from 'recoil';
import { useNotifications } from '../../components/layout';
import { GetMarketplaceFacetsResponse } from '../../services/API/marketplace-listings-api';
import { selectedProjectState } from '../../state';

interface ServiceAPI {
  getFacets: (projectId: string) => Promise<GetMarketplaceFacetsResponse>,
}

const FACETS_KEY = (projectId?: string) => {
  if (!projectId) { return null; }
  return [`projects/${projectId}/marketplace/facets`, projectId];
};

/** Facets rarely change; 5 minutes. */
const SECONDS_PER_MINUTE = 60;
const MS_PER_SECOND = 1000;
const FACETS_DEDUPE_MINUTES = 5;
const FACETS_DEDUPE_MS = FACETS_DEDUPE_MINUTES * SECONDS_PER_MINUTE * MS_PER_SECOND;

export const useMarketplaceFacets = ({
  serviceApi,
  enabled = true,
}: {
  serviceApi: ServiceAPI,
  enabled?: boolean,
}) => {
  const { showErrorNotification } = useNotifications();
  const selectedProject = useRecoilValue(selectedProjectState);

  const fetcher = ([, projectId]: [string, string]) =>
    serviceApi.getFacets(projectId);

  const { data, isLoading, error, mutate } = useSWR(
    enabled ? FACETS_KEY(selectedProject.projectId) : null,
    fetcher,
    {
      shouldRetryOnError: false,
      // Facets rarely change — 5-minute dedupe is fine.
      dedupingInterval: FACETS_DEDUPE_MS,
      onError: (err) => {
        showErrorNotification({
          header: 'Failed to load Marketplace filter facets',
          content: err.message,
        });
      },
    },
  );

  const run = () => { mutate(undefined); };
  return { data: data || null, isLoading, error, run };
};
