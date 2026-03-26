import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useNotifications } from '../../layout';
import { publishingAPI } from '../../../services/API/publishing-api';
import { extractErrorResponseMessage } from '../../../utils/api-helpers';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../layout/navigation/navigation.static';
import { i18n } from './update-product-version.translations';
import useSWR from 'swr';
import { GetProductVersionResponse } from '../../../services/API/proserve-wb-publishing-api';

type UpdateProductVersionProps = {
  projectId: string,
  productId: string,
  versionId: string,
};

type VersionServiceAPI = {
  getProductVersion: (
    projectId: string,
    productId: string,
    versionId: string) => Promise<GetProductVersionResponse>,
};

type VersionFetcherProps = {
  projectId: string,
  productId: string,
  versionId: string,
};


const VERSION_FETCH_KEY = (
  productId?: string,
  productVersionId?: string,
) => {
  if (!productId || !productVersionId) {
    return null;
  }
  return [
    `products/${productId}/versions/${productVersionId}`,
    productId,
    productVersionId,
  ];
};


const versionFetcherFactory = (serviceAPI: VersionServiceAPI) =>
  async ({ projectId, productId, versionId }: VersionFetcherProps) => {
    return serviceAPI.getProductVersion(projectId, productId, versionId);
  };


export const useUpdateProductVersion = ({
  projectId,
  productId,
  versionId,
}: UpdateProductVersionProps) => {

  const { showErrorNotification, showSuccessNotification } = useNotifications();

  const { data: productVersionData, isLoading: isProductVersionLoading } = useSWR(
    {
      key: VERSION_FETCH_KEY(productId, versionId),
      projectId: projectId,
      productId: productId,
      versionId: versionId
    },
    versionFetcherFactory(publishingAPI),
    {
      shouldRetryOnError: false,
    });


  const [productVersionUpdateInProgress, setProductVersionUpdateInProgress] = useState(false);
  const { getPathFor } = useNavigationPaths();
  const navigate = useNavigate();


  function navigateToProductDetails() {
    const productVersionDetailsPath = getPathFor(RouteNames.Product).replace(':id', productId);
    navigate(productVersionDetailsPath);
  }

  function updateProductVersion({
    amiId,
    imageTag,
    imageDigest,
    productVersionDescription,
    versionTemplateDefinition
  }:{
    amiId?: string,
    imageTag?: string,
    imageDigest?: string,
    productVersionDescription: string,
    versionTemplateDefinition: string,
  }) {

    setProductVersionUpdateInProgress(true);
    publishingAPI.updateProductVersion(projectId, productId, versionId, {
      amiId: amiId,
      imageTag: imageTag,
      imageDigest: imageDigest,
      productVersionDescription: productVersionDescription.trim(),
      versionTemplateDefinition: versionTemplateDefinition
    }).then(() => {
      showSuccessNotification({
        header: i18n.updateSuccessMessageHeader,
        content: i18n.updateSuccessMessageContent
      });
      navigateToProductDetails();
    }).catch(async e => {
      showErrorNotification({
        header: i18n.updateFailMessageHeader,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setProductVersionUpdateInProgress(false);
    });
  }

  return {
    productVersion: productVersionData?.version,
    productVersionDistributions: productVersionData?.distributions,
    isProductVersionLoading,
    productVersionUpdateInProgress,
    updateProductVersion,
  };
};
