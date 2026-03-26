import { useState } from 'react';
import { useNotifications } from '../../../../layout';
import { publishingAPI } from '../../../../../services/API';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { i18n } from './promote-version-prompt.translations';
import { VersionSummary } from '../../../../../services/API/proserve-wb-publishing-api';

type PromoteVersionProps = {
  projectId?: string,
  productId?: string,
  selectedVersion?: VersionSummary,
  stageToBePromotedTo?: string,
  loadProductDetails: () => void,
};

export const usePromoteVersionPrompt = ({
  projectId,
  productId,
  selectedVersion,
  stageToBePromotedTo,
  loadProductDetails
}: PromoteVersionProps) => {

  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const [productVersionPromotionInProgress, setProductVersionPromotionInProgress] = useState(false);

  // eslint-disable-next-line complexity
  function promoteProductVersion() {
    if (selectedVersion?.stages.includes('PROD')) {
      showErrorNotification({
        header: i18n.promoteErrorAlreadyInProdHeader,
        content: i18n.promoteErrorAlreadyInProdContent
      });
    }
    setProductVersionPromotionInProgress(true);
    publishingAPI.promoteProductVersion(projectId ?? '', productId ?? '', selectedVersion?.versionId ?? '', {
      stage: stageToBePromotedTo ?? ''
    }).then(() => {
      showSuccessNotification({
        header: i18n.promoteSuccessMessageHeader,
        content: i18n.promoteSuccessMessageContent
      });
      loadProductDetails();
    }).catch(async e => {
      showErrorNotification({
        header: i18n.promoteFailMessageHeader,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setProductVersionPromotionInProgress(false);
    });
  }

  return {
    productVersionPromotionInProgress,
    promoteProductVersion,
  };
};