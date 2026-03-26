import { FC } from 'react';
import { UserPrompt } from '../../shared/user-prompt';
import { ProvisionedProduct } from '../../../../services/API/proserve-wb-provisioning-api';
import { PRODUCT_TYPE_MAP, i18n } from './stop-product-prompt.translations';

type Props = {
  provisionedProduct?: ProvisionedProduct,
  stopConfirmVisible: boolean,
  setStopConfirmVisible: (visible: boolean) => void,
  productType?: string,
  handleStopProduct: () => void,
  stopInProgress: boolean,
};

export const StopProductPrompt: FC<Props> = ({
  provisionedProduct,
  stopConfirmVisible,
  setStopConfirmVisible,
  productType,
  handleStopProduct,
  stopInProgress
}) => {

  function createStopModalText() {
    return <>{i18n.stopModalText1}<b>{provisionedProduct?.productName} </b>
      {PRODUCT_TYPE_MAP[productType || 'product']}.
      <p>{i18n.stopModalText2(PRODUCT_TYPE_MAP[productType || 'product'])}</p>
      <p>{i18n.stopModalText3}</p></>;
  }

  return (
    <UserPrompt
      onConfirm={handleStopProduct}
      onCancel={() => setStopConfirmVisible(false)}
      headerText={i18n.stopModalHeader(PRODUCT_TYPE_MAP[productType || 'product'])}
      content={createStopModalText()}
      cancelText={i18n.stopModalCancel}
      confirmText={i18n.stopModalOK}
      confirmButtonLoading={stopInProgress}
      visible={stopConfirmVisible}
      data-test="stop-product-prompt"
    />
  );
};