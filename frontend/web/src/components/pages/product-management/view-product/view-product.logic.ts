import useSWR from 'swr';
import { GetProductResponse } from '../../../../services/API/proserve-wb-publishing-api';

const FETCH_KEY = 'products/product/details';

type ServiceAPI = {
  getProduct: (projectId: string, productId: string) => Promise<GetProductResponse>,
};

type FetcherProps = {
  projectId: string,
  productId: string,
};

const fetcherFactory = (serviceAPI: ServiceAPI) => async ({ projectId, productId }: FetcherProps) => {
  return serviceAPI.getProduct(projectId, productId);
};

type ProductDetailsProps = {
  projectId?: string,
  productId?: string,
  serviceAPI: ServiceAPI,
};

export const useProductDetails = ({ projectId, productId, serviceAPI }: ProductDetailsProps) => {
  const { data, error, isLoading, mutate } = useSWR(
    { key: FETCH_KEY, projectId: projectId, productId: productId },
    fetcherFactory(serviceAPI),
    {
      shouldRetryOnError: false,
    });

  return {
    product: data?.product,
    loadProductDetails: mutate,
    error,
    isLoading,
  };
};