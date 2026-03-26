/* eslint-disable @stylistic/max-len */
import { FC } from 'react';
import { UserPrompt } from '../../../shared/user-prompt';
import { i18n } from './set-as-recommended-prompt.translations';
import { useSetAsRecommendedPrompt } from './set-as-recommended-prompt.logic';
import { VersionSummary } from '../../../../../services/API/proserve-wb-publishing-api';
import { Box } from '@cloudscape-design/components';

type Props = {
  projectId?: string,
  productId?: string,
  selectedVersion?: VersionSummary,
  promptVisible: boolean,
  setPromptVisible: (visible: boolean) => void,
  successCallback: () => void,
};

export const SetAsRecommendedPrompt: FC<Props> = ({
  projectId,
  productId,
  selectedVersion,
  promptVisible,
  setPromptVisible,
  successCallback,
}) => {

  const { actionInProgress, setAsRecommendedVersion, } = useSetAsRecommendedPrompt({
    projectId: projectId,
    productId: productId,
    selectedVersion: selectedVersion,
    successCallback,
  });

  function renderPromptContent() {
    return <Box>
      <Box variant='p'>
        You are about to set version <Box variant='strong'>{selectedVersion?.name}</Box> as a recommended version.
      </Box>
      <Box variant='p'>
        {i18n.setAsRecommendedModalText}
      </Box>
    </Box>;
  }

  function handleSetAsRecommendedConfirm() {
    setAsRecommendedVersion();
  }

  return (
    <UserPrompt
      onConfirm={handleSetAsRecommendedConfirm}
      onCancel={() => setPromptVisible(false)}
      headerText={i18n.setAsRecommendedModalHeader}
      content={renderPromptContent()}
      cancelText={i18n.setAsRecommendedModalCancel}
      confirmText={i18n.setAsRecommendedModalOK}
      confirmButtonLoading={actionInProgress}
      visible={promptVisible}
      data-test="set-as-recommended-version-prompt"
    />
  );
};