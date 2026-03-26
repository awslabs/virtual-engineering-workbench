import { useState } from 'react';
import { useNotifications } from '../../../../layout';
import { publishingAPI } from '../../../../../services/API';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { i18n } from './retire-version-prompt.translations';
import { VersionSummary } from '../../../../../services/API/proserve-wb-publishing-api';

type RetireVersionProps = {
  projectId: string,
  productId: string,
  selectedVersion: VersionSummary,
  loadProducts: () => void,
};

export const useRetireVersionPrompt = ({
  projectId,
  productId,
  selectedVersion,
  loadProducts,
}: RetireVersionProps) => {

  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const [productVersionRetiringInProgress, setProductVersionRetiringInProgress] = useState(false);
  const [reason, setReason] = useState('');


  function retireProductVersion() {
    setProductVersionRetiringInProgress(true);
    publishingAPI.retireProductVersion(projectId, productId, selectedVersion?.versionId, {
      retireReason: reason ?? ''
    }).then(() => {
      showSuccessNotification({
        header: i18n.retireSuccessMessageHeader,
        content: i18n.retireSuccessMessageContent
      });
      loadProducts();
    }).catch(async e => {
      showErrorNotification({
        header: i18n.retireFailMessageHeader,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setProductVersionRetiringInProgress(false);
    });
  }

  return {
    productVersionRetiringInProgress,
    retireProductVersion,
    reason,
    setReason
  };
};