import { FC } from 'react';
import { UserPrompt } from '../../../shared/user-prompt';
import { i18n } from './archive-product-prompt.translations';
import { useArchiveProductPrompt } from './archive-product-prompt.logic';
import { Product } from '../../../../../services/API/proserve-wb-publishing-api';

type Props = {
  projectId?: string,
  productId?: string,
  selectedProduct?: Product,
  archiveConfirmVisible: boolean,
  setArchiveConfirmVisible: (visible: boolean) => void,
  loadProductDetails?: () => void,
};

export const ArchiveProductPrompt: FC<Props> = ({
  projectId,
  productId,
  selectedProduct,
  archiveConfirmVisible,
  setArchiveConfirmVisible,
  loadProductDetails,
}) => {

  const { productArchivingInProgress, archiveProduct, } = useArchiveProductPrompt({
    projectId: projectId,
    productId: productId,
    productStatus: selectedProduct?.status,
    loadProductDetails: loadProductDetails,
  });

  function createArchiveModalText() {
    return <>{i18n.archiveModalText1}<b>{selectedProduct?.productName}.</b>
      <p>{i18n.archiveModalText2}</p>
      <p>{i18n.archiveModalText3}</p></>;
  }

  function handleArchiveConfirm() {
    archiveProduct();
    setArchiveConfirmVisible(false);
  }

  return (
    <UserPrompt
      onConfirm={handleArchiveConfirm}
      onCancel={() => setArchiveConfirmVisible(false)}
      headerText={i18n.archiveModalHeader}
      content={createArchiveModalText()}
      cancelText={i18n.archiveModalCancel}
      confirmText={i18n.archiveModalOK}
      confirmButtonLoading={productArchivingInProgress}
      visible={archiveConfirmVisible}
      data-test="archive-product-prompt"
    />
  );
};