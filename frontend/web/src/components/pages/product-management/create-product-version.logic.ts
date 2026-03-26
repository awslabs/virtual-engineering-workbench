import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useNotifications } from '../../layout';
import { publishingAPI } from '../../../services';
import { extractErrorResponseMessage } from '../../../utils/api-helpers';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../layout/navigation/navigation.static';
import { i18n } from './create-product-version.translations';
import { PRODUCT_VERSION_RELEASE_TYPE_MAP } from './products.translations';

type CreateProductVersionProps = {
  projectId: string,
  productId: string,
};

export const useCreateProductVersion = ({ projectId, productId }: CreateProductVersionProps) => {
  const versionReleaseTypes = Object.keys(PRODUCT_VERSION_RELEASE_TYPE_MAP);

  const { showErrorNotification, showSuccessNotification } = useNotifications();

  const [productVersionCreationInProgress, setProductVersionCreationInProgress] = useState(false);
  const { getPathFor } = useNavigationPaths();
  const navigate = useNavigate();

  function navigateToCreateProductDetails() {
    const createProductVersionPath = getPathFor(RouteNames.Product).replace(':id', productId);
    navigate(createProductVersionPath);
  }



  function createProductVersion({
    amiId,
    imageTag,
    imageDigest,
    productVersionDescription,
    versionReleaseType,
    versionTemplateDefinition,
    baseMajorVersion
  }:{
    amiId?: string,
    imageTag?: string,
    imageDigest?: string,
    productVersionDescription: string,
    versionReleaseType: string,
    versionTemplateDefinition: string,
    baseMajorVersion?: number,
  }) {
    setProductVersionCreationInProgress(true);
    publishingAPI.createProductVersion(projectId, productId, {
      amiId: amiId,
      imageTag: imageTag,
      imageDigest: imageDigest,
      productVersionDescription: productVersionDescription.trim(),
      versionReleaseType: versionReleaseType,
      versionTemplateDefinition: versionTemplateDefinition,
      ...baseMajorVersion && versionReleaseType !== versionReleaseTypes[0] &&
      { majorVersionName: baseMajorVersion }
    }).then(() => {
      showSuccessNotification({
        header: i18n.createSuccessMessageHeader,
        content: i18n.createSuccessMessageContent
      });
      navigateToCreateProductDetails();
    }).catch(async e => {
      showErrorNotification({
        header: i18n.createFailMessageHeader,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setProductVersionCreationInProgress(false);
    });
  }

  return {
    createProductVersion,
    productVersionCreationInProgress,
  };
};
