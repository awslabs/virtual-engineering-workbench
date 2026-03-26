import { useRecoilState } from 'recoil';
import {
  ProvisionedProductActionState,
  provisionedProductActionState
} from '../../../state';
import { useState } from 'react';
import {
  CommonProvisionedProductStateHookProps,
  CommonProvisionedProductStateHookResponse
} from './interface';
import { extractErrorResponseMessage } from '../../../utils/api-helpers';
import { i18n } from './translations';
import { useNotifications } from '../../layout';
import { provisioningAPI } from '../../../services';

export function useCommonProvisionedProduct() {
  const [turnDownInProgress, setTurnDownInProgress] = useState(false);
  const [turnDownMode, setTurnDownMode] = useState<boolean>(false);
  const [turnDownConfirmVisible, setTurnDownConfirmVisible] = useState(false);
  const [turnDownTimeOutInProgress, setTurnDownTimeOutInProgress] = useState(false);

  return {
    turnDownInProgress,
    setTurnDownInProgress,

    isInTurnDownMode: turnDownMode,
    setTurnDownMode,

    turnDownConfirmVisible,
    setTurnDownConfirmVisible,

    turnDownTimeOutInProgress,
    setTurnDownTimeOutInProgress,
  };
}


export function useCommonProvisionedProductState({
  provisionedProduct,
  stateActionCompleteHandler,
  setStopConfirmVisible
}: CommonProvisionedProductStateHookProps): CommonProvisionedProductStateHookResponse {

  const [
    actionState,
    setActionState
  ] = useRecoilState(provisionedProductActionState(
    provisionedProduct?.provisionedProductId || 'default')
  );

  const { showErrorNotification } = useNotifications();
  const serviceAPI = provisioningAPI;

  function handleStartProduct(): void {

    if (!provisionedProduct) { return; }

    setActionState(ProvisionedProductActionState.InitiatingStart);
    serviceAPI
      .startProvisionedProduct(provisionedProduct.projectId, provisionedProduct.provisionedProductId)
      .catch(async (e) => {
        showErrorNotification({
          header: i18n.errorStart,
          content: await extractErrorResponseMessage(e),
        });
      })
      .finally(() => {
        setActionState(ProvisionedProductActionState.None);
      })
      .then(() => {
        stateActionCompleteHandler?.();
      });
  }

  function handleStopProduct(): void {

    if (!provisionedProduct) { return; }

    setActionState(ProvisionedProductActionState.InitiatingStop);
    serviceAPI
      .stopProvisionedProduct(provisionedProduct.projectId, provisionedProduct.provisionedProductId)
      .catch(async (e) => {
        showErrorNotification({
          header: i18n.errorStop,
          content: await extractErrorResponseMessage(e),
        });
      })
      .finally(() => {
        setActionState(ProvisionedProductActionState.None);
      })
      .then(() => {
        stateActionCompleteHandler?.();
        setStopConfirmVisible(false);
      });
  }

  return {
    handleStartProduct,
    handleStopProduct,
    startInProgress: actionState === ProvisionedProductActionState.InitiatingStart,
    stopInProgress: actionState === ProvisionedProductActionState.InitiatingStop,
  };
}