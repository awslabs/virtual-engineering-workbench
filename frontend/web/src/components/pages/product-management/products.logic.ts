import { useState } from 'react';
import { publishingAPI } from '../../../services/API/publishing-api';
import { selectedProjectState } from '../../../state';
import { useRecoilValue } from 'recoil';
import { Product } from '../../../services/API/proserve-wb-publishing-api';
import { useNotifications } from '../../layout';
import { i18n, PRODUCT_STATUS_MAP } from './products.translations';
import { SelectProps } from '@cloudscape-design/components';
import { ProductState } from './products.static';
import useSWR, { useSWRConfig } from 'swr';


const FETCHER = ([, projectId, ]: [url: string, projectId: string]) => {
  return publishingAPI.getProducts(projectId);
};
const PRODUCT_FETCH_KEY = (projectId?: string,) => {
  if (!projectId) {
    return null;
  }
  return [
    `projects/${projectId}/products`,
    projectId,
  ];
};

export const useProducts = () => {
  const { cache } = useSWRConfig();
  const { showErrorNotification } = useNotifications();
  const selectedProject = useRecoilValue(selectedProjectState);
  const statusFirstOption = {
    value: i18n.statusFirstOptionValue,
    label: PRODUCT_STATUS_MAP[('CREATED') as ProductState],
  };
  const [status, setStatus] = useState<SelectProps.Option>(statusFirstOption);
  const { data, isLoading, mutate } = useSWR(
    PRODUCT_FETCH_KEY(selectedProject.projectId),
    FETCHER,
    {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.errorUnableToFetchProducts,
          content: err.message,
        });
      }
    }
  );
  const fetchData = () => {
    cache.delete(`projects/${selectedProject.projectId}/products`);
    mutate(undefined);
  };
  const filteredProducts: Product[] = data?.products ?
    data.products.filter(product =>
      product.status === status?.value || status.value === i18n.statusOptionAny) : [];
  const statuses = data?.products?.map(product => {
    return product.status;
  });
  const statusOptions = [i18n.statusOptionAny, ...new Set(statuses)].map((status) => {
    return {
      value: status,
      label: PRODUCT_STATUS_MAP[(status || 'UNKNOWN') as ProductState]
    } as SelectProps.Option;
  });

  return {
    products: filteredProducts,
    isLoading,
    loadProducts: fetchData,
    status,
    setStatus,
    statusOptions
  };
};
