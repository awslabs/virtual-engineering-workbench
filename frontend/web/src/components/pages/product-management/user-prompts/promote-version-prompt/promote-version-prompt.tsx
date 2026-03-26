/* eslint-disable @stylistic/max-len */
import { FC } from 'react';
import { UserPrompt } from '../../../shared/user-prompt';
import { i18n } from './promote-version-prompt.translations';
import { usePromoteVersionPrompt } from './promote-version-prompt.logic';
import { VersionSummary } from '../../../../../services/API/proserve-wb-publishing-api';
import { Icon } from '@cloudscape-design/components';
import { GenericGlobeIcon } from '../../../../layout/vew-icons';

type Props = {
  projectId?: string,
  productId?: string,
  selectedVersion?: VersionSummary,
  promoteConfirmVisible: boolean,
  setPromoteConfirmVisible: (visible: boolean) => void,
  loadProductDetails: () => void,
};

export const PromoteVersionPrompt: FC<Props> = ({
  projectId,
  productId,
  selectedVersion,
  promoteConfirmVisible,
  setPromoteConfirmVisible,
  loadProductDetails
}) => {

  const selectedStages = selectedVersion?.stages;
  let currentStage = '';
  let stageToBePromotedTo = '';
  if (selectedStages?.includes('QA')) {
    currentStage = 'QA';
    stageToBePromotedTo = 'PROD';
  } else {
    currentStage = 'DEV';
    stageToBePromotedTo = 'QA';
  }

  const { productVersionPromotionInProgress, promoteProductVersion, } = usePromoteVersionPrompt({
    projectId: projectId,
    productId: productId,
    selectedVersion: selectedVersion,
    stageToBePromotedTo: stageToBePromotedTo,
    loadProductDetails: loadProductDetails
  });

  function createPromoteModalText() {
    const promoteStageText = `You are about to promote product version from ${currentStage} to ${stageToBePromotedTo}:`;
    const renderedName = selectedVersion?.recommendedVersion ? <><b>{selectedVersion?.name}</b><i> (recommended version)</i></> : <b>{selectedVersion?.name}</b>;

    const promoteVersionChecklist = () => {
      if (currentStage === 'QA' && stageToBePromotedTo === 'PROD') {
        return <>{i18n.promoteProductVersionChecklistMessage}
          <p style={{ paddingLeft: '1.5em' }}><Icon name='multiscreen' /> {i18n.promoteProductVersionChecklistPoint1}</p>
          <p style={{ paddingLeft: '1.5em' }}><Icon svg={<GenericGlobeIcon />} /> {i18n.promoteProductVersionChecklistPoint2}</p>
          <p style={{ paddingLeft: '1.5em' }}><Icon name='check' /> {i18n.promoteProductVersionChecklistPoint1}</p></>;
      }
      return null;
    };

    return <>{promoteStageText}<ul><li>{renderedName}</li></ul>
      {promoteVersionChecklist()}
      <p>{i18n.promoteModalText}</p></>;
  }

  function handlePromoteConfirm() {
    promoteProductVersion();
    setPromoteConfirmVisible(false);
  }

  return (
    <UserPrompt
      onConfirm={handlePromoteConfirm}
      onCancel={() => setPromoteConfirmVisible(false)}
      headerText={i18n.promoteModalHeader}
      content={createPromoteModalText()}
      cancelText={i18n.promoteModalCancel}
      confirmText={i18n.promoteModalOK}
      confirmButtonLoading={productVersionPromotionInProgress}
      visible={promoteConfirmVisible}
      data-test="promote-product-version-prompt"
    />
  );
};