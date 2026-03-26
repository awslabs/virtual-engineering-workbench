import { useCallback, useEffect, useState } from 'react';
import {
  VersionDistribution,
  VersionSummary
} from '../../../services/API/proserve-wb-publishing-api';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../state';
import { publishingAPI } from '../../../services/API/publishing-api';
import { i18n } from './view-product-version-details.translations';
import { extractErrorResponseMessage } from '../../../utils/api-helpers';
import { useNotifications } from '../../layout';
import { useParams } from 'react-router-dom';

export const useProductVersionDetails = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [productVersion, setProductVersion] = useState<VersionSummary>();
  const [productVersionDistributions, setProductVersionDistributions] = useState<VersionDistribution[]>([]);
  const [productVersionTemplate, setProductVersionTemplate] = useState('');
  const selectedProject = useRecoilValue(selectedProjectState);
  const { showErrorNotification } = useNotifications();
  const { productId, versionId } = useParams();

  /** Helper function to check if required IDs exist */
  const hasRequiredIds = () => selectedProject.projectId && productId && versionId;

  /** Helper function to handle errors */
  const handleError = async (error: unknown, header: string) => {
    showErrorNotification({
      header,
      content: await extractErrorResponseMessage(error),
    });
  };

  /** Function to fetch product version details */
  const fetchProductVersion = async () => {
    try {
      const response = await publishingAPI.getProductVersion(
        selectedProject.projectId!,
        productId!,
        versionId!
      );
      setProductVersion(response.version);
      setProductVersionDistributions(response.distributions);
      setProductVersionTemplate(response.draftTemplate);
    } catch (error) {
      await handleError(error, i18n.versionError);
    }
  };

  /** Loads product version details */
  const loadProductVersion = useCallback(async () => {
    if (!hasRequiredIds() || isLoading) { return; }
    setIsLoading(true);
    await fetchProductVersion();
    setIsLoading(false);
  }, [selectedProject, productId, versionId]);

  /** Retries distribution for given AWS account IDs */
  const retryDistribution = useCallback(async (awsAccountIds: string[]) => {
    if (!hasRequiredIds()) { return; }
    setIsRetrying(true);
    try {
      await publishingAPI.retryProductVersion(
        selectedProject.projectId!,
        productId!,
        versionId!,
        awsAccountIds
      );
    } catch (error) {
      await handleError(error, i18n.retryError);
    }
    setIsRetrying(false);
  }, [selectedProject, productId, versionId]);

  useEffect(() => {
    loadProductVersion();
  }, [loadProductVersion]);

  return {
    isLoading,
    isRetrying,
    productVersion,
    loadProductVersion,
    retryDistribution,
    productVersionDistributions,
    productVersionTemplate,
  };
};
