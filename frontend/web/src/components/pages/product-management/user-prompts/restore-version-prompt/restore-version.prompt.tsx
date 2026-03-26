import { FC } from 'react';
import { UserPrompt } from '../../../shared/user-prompt';
import { i18n } from './restore-version-prompt.translations';
import { VersionSummary } from '../../../../../services/API/proserve-wb-publishing-api';
import { useRestoreVersionPrompt } from './restore-version-prompt.logic';

type Props = {
  projectId: string,
  productId: string,
  selectedVersion: VersionSummary,
  restoreConfirmVisible: boolean,
  setRestoreConfirmVisible: (visible: boolean) => void,
  loadProducts: () => void,
};

export const RestoreVersionPrompt: FC<Props> = ({
  projectId,
  productId,
  selectedVersion,
  restoreConfirmVisible,
  setRestoreConfirmVisible,
  loadProducts,
}) => {

  const { productVersionRestoringInProgress, restoreProductVersion } = useRestoreVersionPrompt({
    projectId: projectId!,
    productId: productId!,
    selectedVersion: selectedVersion!,
    loadProducts: loadProducts,
  });

  function createModalText() {
    return <>
      <p>{i18n.restoreModalTextInfo}<b>{selectedVersion?.name}</b>.</p>
      <p>{i18n.restoreModalTextDescription}</p>
      <p>{i18n.restoreModalTextQuestion}</p>
    </>;
  }

  function handleRestoreConfirm() {
    restoreProductVersion();
    setRestoreConfirmVisible(false);
  }

  return (
    <UserPrompt
      onConfirm={handleRestoreConfirm}
      onCancel={() => setRestoreConfirmVisible(false)}
      headerText={i18n.restoreModalHeader}
      content={createModalText()}
      cancelText={i18n.restoreModalCancel}
      confirmText={i18n.restoreModalOK}
      confirmButtonLoading={productVersionRestoringInProgress}
      visible={restoreConfirmVisible}
      data-test="restore-product-version-prompt"
    />
  );
};