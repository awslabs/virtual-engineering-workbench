import { useState } from 'react';
import useSwr from 'swr';
import {
  GetProductResponse,
  GetProductVersionResponse,
} from '../../../../services/API/proserve-wb-publishing-api';
import { useNotifications } from '../../../layout';
import { i18n } from './compare-product-versions.translations';

interface ServiceAPI {
  getProduct: (
    projectId: string, productId: string
  ) => Promise<GetProductResponse>,
  getProductVersion: (
    projectId: string, productId: string, versionId: string
  ) => Promise<GetProductVersionResponse>,
}

interface Props {
  serviceApi: ServiceAPI,
  projectId?: string,
  productId: string,
  initialVersionIdA?: string | null,
}

function useVersionFetch(
  serviceApi: ServiceAPI,
  projectId: string | undefined,
  productId: string,
  versionId: string | null,
  keyPrefix: string,
  showErrorNotification: ReturnType<
    typeof useNotifications
  >['showErrorNotification'],
) {
  const fetcher = (
    [, pid, prodId, vid]: [string, string, string, string]
  ) => serviceApi.getProductVersion(pid, prodId, vid);

  return useSwr(
    projectId && versionId
      ? [`${keyPrefix}/${productId}/${versionId}`,
        projectId, productId, versionId]
      : null,
    fetcher,
    {
      shouldRetryOnError: false,
      onError: (err) => showErrorNotification({
        header: i18n.errorLoadingVersion,
        content: err.message,
      }),
    }
  );
}

// eslint-disable-next-line complexity
export function useCompareProductVersions(
  { serviceApi, projectId, productId, initialVersionIdA }: Props
) {
  const { showErrorNotification } = useNotifications();
  const [versionIdA, setVersionIdA] =
    useState<string | null>(initialVersionIdA || null);
  const [versionIdB, setVersionIdB] = useState<string | null>(null);

  function selectVersionA(id: string | null) {
    setVersionIdA(id);
    setVersionIdB(null);
  }

  function selectVersionB(id: string | null) {
    setVersionIdB(id);
  }

  const productFetcher = (
    [, pid, prodId]: [string, string, string]
  ) => serviceApi.getProduct(pid, prodId);

  const { data: productData, isLoading: productLoading } = useSwr(
    projectId
      ? [`compare-product/${productId}`, projectId, productId]
      : null,
    productFetcher,
    {
      shouldRetryOnError: false,
      onError: (err) => showErrorNotification({
        header: i18n.errorLoadingProduct,
        content: err.message,
      }),
    }
  );

  const { data: dataA, isLoading: loadingA } = useVersionFetch(
    serviceApi, projectId, productId,
    versionIdA, 'compare-pv-a', showErrorNotification,
  );

  const { data: dataB, isLoading: loadingB } = useVersionFetch(
    serviceApi, projectId, productId,
    versionIdB, 'compare-pv-b', showErrorNotification,
  );

  return {
    versions: productData?.product?.versions || [],
    productLoading,
    versionIdA,
    selectVersionA,
    versionIdB,
    selectVersionB,
    templateA: dataA?.draftTemplate || '',
    templateB: dataB?.draftTemplate || '',
    distributionsA: dataA?.distributions || [],
    distributionsB: dataB?.distributions || [],
    loadingA,
    loadingB,
    isReady: !!(versionIdA && versionIdB && !loadingA && !loadingB),
  };
}
