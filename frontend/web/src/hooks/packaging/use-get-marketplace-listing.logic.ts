// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import useSWR from 'swr';
import { useRecoilValue } from 'recoil';
import { useNotifications } from '../../components/layout';
import { GetMarketplaceListingResponse } from '../../services/API/marketplace-listings-api';
import { selectedProjectState } from '../../state';

interface ServiceAPI {
  getListing: (projectId: string, listingId: string) => Promise<GetMarketplaceListingResponse>,
}

const LISTING_KEY = (projectId?: string, listingId?: string) => {
  if (!projectId || !listingId) { return null; }
  return [`projects/${projectId}/marketplace/listings/${listingId}`, projectId, listingId];
};

export const useGetMarketplaceListing = ({
  serviceApi,
  listingId,
  enabled = true,
}: {
  serviceApi: ServiceAPI,
  listingId: string | null,
  enabled?: boolean,
}) => {
  const { showErrorNotification } = useNotifications();
  const selectedProject = useRecoilValue(selectedProjectState);

  const fetcher = ([, projectId, id]: [string, string, string]) =>
    serviceApi.getListing(projectId, id);

  const key = enabled && listingId
    ? LISTING_KEY(selectedProject.projectId, listingId)
    : null;

  const { data, isLoading, error, mutate } = useSWR(key, fetcher, {
    shouldRetryOnError: false,
    onError: (err) => {
      showErrorNotification({
        header: 'Failed to load Marketplace listing',
        content: err.message,
      });
    },
  });

  const run = () => { mutate(undefined); };
  return { data: data || null, isLoading, error, run };
};
