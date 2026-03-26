import { Button, SpaceBetween } from '@cloudscape-design/components';
import { ProvisionedProductDetails } from '../../provisioned-products/provisioned-product-detail/page';
import { useVirtualTargetDetails } from './logic';
import { provisioningAPI } from '../../../../services/API/provisioning-api';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { i18nVirtualTargetDetails } from './translations';
import {
  ProvisionedProductLogin,
  i18nVirtualTargetLogin
} from '../../provisioned-products/provisioned-product-actions';
import { useState } from 'react';
import { StopProductPrompt } from '../../provisioned-products/stop-product-prompt/stop-product-prompt';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { UserPrompt } from '../../shared/user-prompt';
import { ProvisionedProductsToDeleteList } from '../../provisioned-products/components';

export function VirtualTargetDetails() {
  const { navigateTo } = useNavigationPaths();
  const [loginPromptVisible, setLoginPromptVisible] = useState(false);
  const [turnDownConfirmVisible, setTurnDownConfirmVisible] = useState(false);
  const productType = 'virtualTarget';
  const props = {
    serviceAPI: provisioningAPI,
    provisionedProductDetailsRouteName: RouteNames.VirtualTargetDetails,
    availableProvisionedProductRouteName: RouteNames.AvailableWorkbenches,
    productType: 'workbench',
    myProvisionedProductRouteName: RouteNames.MyWorkbenches,
    translations: i18nVirtualTargetDetails,
  };
  const {
    isInTurnDownMode,
    disableActionButtons,
    provisionedProduct,
    renderStopButtonRequred,
    renderStartButtonRequred,
    provisionedProductActionBusy,
    renderLoginButtonRequred,
    handleStartProduct,
    handleStopProduct,
    stopInProgress,
    stopConfirmVisible,
    setStopConfirmVisible,
    handleRemoveProvisionedProduct,
  } = useVirtualTargetDetails(props);

  async function handleRemoveConfirmSubmit () {
    const projectId = provisionedProduct?.projectId ?? '';
    const provisionedProductId = provisionedProduct?.provisionedProductId ?? '';
    await handleRemoveProvisionedProduct(projectId, provisionedProductId);
    setTurnDownConfirmVisible(false);
    navigateTo(RouteNames.MyVirtualTargets);
  }

  function handleRemoveConfirmCancel() {
    setTurnDownConfirmVisible(false);
  }

  function renderStopButton() {
    return provisionedProduct ?
      <Button
        variant="normal"
        onClick={() => setStopConfirmVisible(true)}
        loading={provisionedProductActionBusy}
        disabled={disableActionButtons || isInTurnDownMode}
        data-test="virtual-target-stop-button"
      >
        {i18nVirtualTargetDetails.stopButton}
      </Button>
      : null;
  }
  function renderStartButton() {
    return provisionedProduct ?
      <Button
        variant="primary"
        onClick={handleStartProduct}
        loading={provisionedProductActionBusy}
        disabled={disableActionButtons || isInTurnDownMode}
        data-test="virtual-target-start-button"
      >
        {i18nVirtualTargetDetails.startButton}
      </Button>
      : null;
  }

  function renderLoginButton() {
    return (
      <Button
        variant="primary"
        onClick={() => setLoginPromptVisible(true)}
        disabled={isInTurnDownMode || stopInProgress}
        data-test="vt-login-button"
      >
        {i18nVirtualTargetDetails.loginPromptConfirm}
      </Button>
    );
  }

  function renderActionHeader() {
    return (
      <SpaceBetween size={'s'} direction="horizontal">
        {renderStopButtonRequred ? renderStopButton() : null}
        {renderStartButtonRequred ? renderStartButton() : null}
        {renderLoginButtonRequred ? renderLoginButton() : null}
        <Button onClick={(e) => {
          e.preventDefault();
          setTurnDownConfirmVisible(true);
        }
        } variant='primary'>{i18nVirtualTargetDetails.removeVirtualTarget}</Button>
      </SpaceBetween>
    );
  }

  return <>
    <ProvisionedProductDetails
      {...props}
      dataTestPrefix="virtual-target"
      headerActions={renderActionHeader()}
    ></ProvisionedProductDetails>
    {provisionedProduct ?
      <ProvisionedProductLogin
        loginPromptVisible={loginPromptVisible}
        setLoginPromptVisible={setLoginPromptVisible}
        provisionedProduct={provisionedProduct}
        i18n={i18nVirtualTargetLogin}
        headlessLogin
      />
      : null }
    <StopProductPrompt
      provisionedProduct={provisionedProduct}
      stopConfirmVisible={stopConfirmVisible}
      setStopConfirmVisible={setStopConfirmVisible}
      productType={productType}
      handleStopProduct={handleStopProduct}
      stopInProgress={stopInProgress} />
    {provisionedProduct ?
      <UserPrompt
        onConfirm={handleRemoveConfirmSubmit}
        onCancel={handleRemoveConfirmCancel}
        headerText={i18nVirtualTargetLogin.confirmRemoveLabel}
        content={
          <ProvisionedProductsToDeleteList
            targets={[provisionedProduct]}
            translations={i18nVirtualTargetLogin}
          />
        }
        cancelText={i18nVirtualTargetLogin.deprovisionModalCancel}
        confirmText={i18nVirtualTargetLogin.deprovisionModalOK}
        confirmButtonLoading={false}
        visible={turnDownConfirmVisible}
      />
      : null }
  </>;
}
