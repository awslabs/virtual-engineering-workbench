import { useState } from 'react';
import { useNotifications } from '../../../../layout';
import { publishingAPI } from '../../../../../services/API';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { i18n } from './restore-version-prompt.translations';
import { VersionSummary } from '../../../../../services/API/proserve-wb-publishing-api';

type RestoreVersionProps = {
  projectId: string,
  productId: string,
  selectedVersion: VersionSummary,
  loadProducts: () => void,
};

export const useRestoreVersionPrompt = ({
  projectId,
  productId,
  selectedVersion,
  loadProducts,
}: RestoreVersionProps) => {

  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const [productVersionRestoringInProgress, setProductVersionRestoringInProgress] = useState(false);
  const [reason, setReason] = useState('');

  function restoreProductVersion() {
    setProductVersionRestoringInProgress(true);
    publishingAPI.restoreProductVersion(projectId, productId, selectedVersion?.versionId)
      .then((response) => {
        showSuccessNotification({
          header: i18n.restoreSuccessMessageHeader,
          content: i18n.restoreSuccessMessageContent +
            response.restoredVersionName + i18n.restoreSuccessMessageContent2
        });
        loadProducts();
      }).catch(async e => {
        showErrorNotification({
          header: i18n.restoreFailMessageHeader,
          content: await extractErrorResponseMessage(e)
        });
      }).finally(() => {
        setProductVersionRestoringInProgress(false);
      });
  }


  return {
    productVersionRestoringInProgress,
    restoreProductVersion,
    reason,
    setReason
  };
};