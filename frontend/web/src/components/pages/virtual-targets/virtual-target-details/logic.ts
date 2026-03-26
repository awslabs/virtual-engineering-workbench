import { PRODUCT_INSTANCE_STATES } from '../../provisioned-products';
import {
  ProvisionedProductDetailsHookPorps
} from '../../provisioned-products/provisioned-product-detail/interface';
import { useProvisionedProductDetails } from '../../provisioned-products/provisioned-product-detail/logic';
export type VirtualTargetDetailsHookPorps = ProvisionedProductDetailsHookPorps;

export function useVirtualTargetDetails(props: VirtualTargetDetailsHookPorps) {
  const genHookRet = useProvisionedProductDetails(props);

  const disableActionButtons = genHookRet.isLoading;

  const provisionedProductStatus =
    genHookRet.provisionedProduct?.status ?? 'unkown';

  const provisionedProductActionBusy =
    genHookRet.startInProgress ||
    genHookRet.stopInProgress ||
    ![
      PRODUCT_INSTANCE_STATES.Running,
      PRODUCT_INSTANCE_STATES.Stopped,
    ].includes(provisionedProductStatus);

  const renderStopButtonRequred = [
    PRODUCT_INSTANCE_STATES.Running,
    PRODUCT_INSTANCE_STATES.Stopping,
  ].includes(provisionedProductStatus);

  const renderStartButtonRequred = [
    PRODUCT_INSTANCE_STATES.Stopped,
    PRODUCT_INSTANCE_STATES.Starting,
  ].includes(provisionedProductStatus);

  const renderLoginButtonRequred =
    provisionedProductStatus === PRODUCT_INSTANCE_STATES.Running;

  return {
    ...genHookRet,
    ...{
      disableActionButtons,
      provisionedProductActionBusy,
      renderStopButtonRequred,
      renderStartButtonRequred,
      renderLoginButtonRequred,
    },
  };
}
