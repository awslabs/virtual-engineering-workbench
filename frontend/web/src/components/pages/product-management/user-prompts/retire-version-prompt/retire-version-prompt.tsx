import { FC } from 'react';
import { UserPrompt } from '../../../shared/user-prompt';
import { i18n } from './retire-version-prompt.translations';
import { VersionSummary } from '../../../../../services/API/proserve-wb-publishing-api';
import { useRetireVersionPrompt } from './retire-version-prompt.logic';
import { Box, Input } from '@cloudscape-design/components';

type Props = {
  projectId: string,
  productId: string,
  selectedVersion: VersionSummary,
  retireConfirmVisible: boolean,
  setRetireConfirmVisible: (visible: boolean) => void,
  loadProducts: () => void,
};

export const RetireVersionPrompt: FC<Props> = ({
  projectId,
  productId,
  selectedVersion,
  retireConfirmVisible,
  setRetireConfirmVisible,
  loadProducts,
}) => {

  const { productVersionRetiringInProgress, retireProductVersion, reason, setReason }
    = useRetireVersionPrompt({
      projectId: projectId,
      productId: productId,
      selectedVersion: selectedVersion,
      loadProducts: loadProducts,
    });


  function createModalText() {
    return <>
      <Box variant="p">{i18n.retireModalTextInfo}<b>{selectedVersion?.name}</b></Box>
      <Box variant="p">{i18n.retireModalTextDescription}</Box>
      <Box variant="p">{i18n.retireModalTextQuestion}</Box>
      <Box>
        <b>{i18n.retireModalTextReason}<i>{i18n.retireModalTextOptional}</i></b>
        <Input
          onChange={({ detail }) => setReason(detail.value)}
          value={reason}
        />
      </Box>
    </>;
  }

  function handleRetireConfirm() {
    retireProductVersion();
    setRetireConfirmVisible(false);
    loadProducts();
  }

  return (
    <UserPrompt
      onConfirm={handleRetireConfirm}
      onCancel={() => setRetireConfirmVisible(false)}
      headerText={i18n.retireModalHeader}
      content={createModalText()}
      cancelText={i18n.retireModalCancel}
      confirmText={i18n.retireModalOK}
      confirmButtonLoading={productVersionRetiringInProgress}
      visible={retireConfirmVisible}
      data-test="retire-product-version-prompt"
    />
  );
};