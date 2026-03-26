import { useState } from 'react';
import { useNotifications } from '../../../../layout';
import { publishingAPI } from '../../../../../services/API';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { i18n } from './set-as-recommended-prompt.translations';
import { VersionSummary } from '../../../../../services/API/proserve-wb-publishing-api';

type PromoteVersionProps = {
  projectId?: string,
  productId?: string,
  selectedVersion?: VersionSummary,
  successCallback: () => void,
};

export const useSetAsRecommendedPrompt = ({
  projectId,
  productId,
  selectedVersion,
  successCallback,
}: PromoteVersionProps) => {

  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const [actionInProgress, setActionInProgress] = useState(false);


  function setAsRecommendedVersion() {

    if (!projectId || !productId || !selectedVersion?.versionId) {
      return;
    }

    setActionInProgress(true);

    publishingAPI.setAsRecommendedVersion(projectId, productId, selectedVersion.versionId).then(() => {
      showSuccessNotification({
        header: i18n.setAsRecommendedSuccessMessageHeader,
        content: i18n.setAsRecommendedSuccessMessageContent
      });
      successCallback();
    }).catch(async e => {
      showErrorNotification({
        header: i18n.setAsRecommendedFailMessageHeader,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setActionInProgress(false);
    });
  }

  return {
    actionInProgress,
    setAsRecommendedVersion,
  };
};