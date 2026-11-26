// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import useSWR from 'swr';
import { useRecoilValue } from 'recoil';
import { useNotifications } from '../../components/layout';
import {
  MarketplaceListingSummary,
  SearchListingsParams,
  SearchMarketplaceListingsResponse,
} from '../../services/API/marketplace-listings-api';
import { selectedProjectState } from '../../state';

interface ServiceAPI {
  searchListings: (
    projectId: string,
    params?: SearchListingsParams,
  ) => Promise<SearchMarketplaceListingsResponse>,
}

// The SWR key includes the params object so a fresh search with different
// filters/text/next-token gets its own cache entry.
const LISTINGS_KEY = (projectId?: string, params?: SearchListingsParams) => {
  if (!projectId) { return null; }
  return [
    `projects/${projectId}/marketplace/listings`,
    projectId,
    JSON.stringify(params || {}),
  ];
};

export const useSearchMarketplaceListings = ({
  serviceApi,
  params,
  enabled = true,
}: {
  serviceApi: ServiceAPI,
  params: SearchListingsParams,
  enabled?: boolean,
}) => {
  const { showErrorNotification } = useNotifications();
  const selectedProject = useRecoilValue(selectedProjectState);

  const fetcher = ([, projectId, paramsJson]: [string, string, string]) =>
    serviceApi.searchListings(projectId, JSON.parse(paramsJson) as SearchListingsParams);

  const { data, isLoading, error, mutate } = useSWR(
    enabled ? LISTINGS_KEY(selectedProject.projectId, params) : null,
    fetcher,
    {
      shouldRetryOnError: false,
      keepPreviousData: true,
      onError: (err) => {
        showErrorNotification({
          header: 'Failed to search Marketplace listings',
          content: err.message,
        });
      },
    },
  );

  const run = () => { mutate(undefined); };

  const listings: MarketplaceListingSummary[] = data?.listings || [];
  const nextToken: string | undefined = data?.nextToken || undefined;
  const totalResults: number | undefined = data?.totalResults ?? undefined;
  return { data: listings, nextToken, totalResults, isLoading, error, run };
};
