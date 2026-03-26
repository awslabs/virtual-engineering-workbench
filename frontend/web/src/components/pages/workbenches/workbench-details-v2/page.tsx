import {
  Button,
  ButtonDropdown,
  ButtonDropdownProps,
  SpaceBetween,
} from '@cloudscape-design/components';
import { ProvisionedProductDetails } from '../../provisioned-products/provisioned-product-detail/page';
import { useWorkbenchDetails } from './logic';
import { ProvisionedProductLogin } from '../../provisioned-products/provisioned-product-actions/page';
import { useState } from 'react';
import { provisioningAPI } from '../../../../services/API/provisioning-api';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { i18nWorkbenchDetails } from './translations';
import { i18nWorkbenchLogin } from '../../provisioned-products/provisioned-product-actions';
import { StopProductPrompt } from '../../provisioned-products/stop-product-prompt/stop-product-prompt';
import {
  UpdateProvisionedProductPrompt
} from '../../provisioned-products/provisioned-product-update-prompt/update-provisioned-product-prompt';
import { useFeatureToggles } from '../../../feature-toggles/feature-toggle.hook';
import { Feature } from '../../../feature-toggles/feature-toggle.state';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { UserPrompt } from '../../shared/user-prompt';
import { ProvisionedProductsToDeleteList } from '../../provisioned-products/components';


export function WorkbenchDetails() {
  const { navigateTo } = useNavigationPaths();
  const [loginPromptVisible, setLoginPromptVisible] = useState(false);
  const [updatePromptVisible, setUpdatePromptVisible] = useState(false);
  const [turnDownConfirmVisible, setTurnDownConfirmVisible] = useState(false);
  const [updateType, setUpdateType] = useState('instance type');
  const productType = 'workbench';
  const { isFeatureEnabled } = useFeatureToggles();
  const props = {
    serviceAPI: provisioningAPI,
    provisionedProductDetailsRouteName: RouteNames.WorkbenchDetails,
    availableProvisionedProductRouteName: RouteNames.AvailableWorkbenches,
    productType: 'workbench',
    myProvisionedProductRouteName: RouteNames.MyWorkbenches,
    translations: i18nWorkbenchDetails,
  };
  const {
    handleStartProduct,
    handleStopProduct,
    stopInProgress,
    isInTurnDownMode,
    disableActionButtons,
    provisionedProduct,
    renderStopButtonRequired,
    renderStartButtonRequired,
    renderLoginButtonRequired,
    provisionedProductActionBusy,
    stopConfirmVisible,
    setStopConfirmVisible,
    mutate,
    handleRemoveProvisionedProduct,
  } = useWorkbenchDetails(props);

  async function handleRemoveConfirmSubmit () {
    const provisionedProductId = provisionedProduct?.provisionedProductId ?? '';
    const projectId = provisionedProduct?.projectId ?? '';
    await handleRemoveProvisionedProduct(projectId, provisionedProductId);
    setTurnDownConfirmVisible(false);
    navigateTo(RouteNames.MyWorkbenches);
  }

  function handleRemoveConfirmCancel() {
    setTurnDownConfirmVisible(false);
  }

  function renderLoginButton() {
    return (
      <Button
        variant="primary"
        onClick={() => setLoginPromptVisible(true)}
        disabled={isInTurnDownMode || stopInProgress}
        data-test="workbench-login-button"
      >
        {i18nWorkbenchDetails.loginPromptConfirm}
      </Button>
    );
  }

  // eslint-disable-next-line complexity
  function handleDropdownClick(
    { detail }: CustomEvent<ButtonDropdownProps.ItemClickDetails>
  ) {
    if (detail.id === 'updateInstanceType') {
      setUpdateType('instance type');
      setUpdatePromptVisible(true);
    }
    if (detail.id === 'updateVersion') {
      setUpdateType('version');
      setUpdatePromptVisible(true);
    }
    if (detail.id === 'start') {
      handleStartProduct();
    }
    if (detail.id === 'stop') {
      setStopConfirmVisible(true);
    }
    if (detail.id === 'remove') {
      setTurnDownConfirmVisible(true);
    }
  }

  function itemsArrayForActionsDropdown() {
    const actionItems = [
      { condition: renderStartButtonRequired, action: 'start', text: i18nWorkbenchDetails.startAction },
      { condition: renderStopButtonRequired, action: 'stop', text: i18nWorkbenchDetails.stopAction },
    ];

    const dynamicItems = actionItems
      .filter(item => item.condition)
      .map(item => ({
        text: item.text,
        id: item.action,
        disabled: disableActionButtons || isInTurnDownMode,
      }));

    const dropDownManualActions = [];
    if (isFeatureEnabled(Feature.ProvisionedProductManualUpdates)) {
      dropDownManualActions.push({
        text: i18nWorkbenchDetails.updateInstanceTypeAction,
        id: 'updateInstanceType',
      });
      dropDownManualActions.push({
        text: i18nWorkbenchDetails.updateVersionAction,
        id: 'updateVersion',
      });
    }

    dropDownManualActions.push({
      text: i18nWorkbenchDetails.removeWorkbench,
      id: 'remove'
    });

    return [
      ...dynamicItems,
      ...dropDownManualActions
    ];
  }

  function renderActionHeader() {
    return (
      <SpaceBetween size={'s'} direction="horizontal">
        {provisionedProduct ?
          <ButtonDropdown
            data-test="actions-dropdown"
            onItemClick={handleDropdownClick}
            loading={provisionedProductActionBusy}
            items={itemsArrayForActionsDropdown()}
          >
            {i18nWorkbenchDetails.actionsButton}
          </ButtonDropdown>
          : null }
        {renderLoginButtonRequired ? renderLoginButton() : null}
      </SpaceBetween>
    );
  }

  return (
    <>
      {provisionedProduct ?
        <UpdateProvisionedProductPrompt
          provisionedProduct={provisionedProduct}
          updateConfirmVisible={updatePromptVisible}
          setUpdatePromptVisible={setUpdatePromptVisible}
          serviceApi={provisioningAPI}
          stateActionCompleteHandler={mutate}
          updateType={updateType}
        />
        : null }
      <ProvisionedProductDetails
        {...props}
        dataTestPrefix="workbench"
        headerActions={renderActionHeader()}
      ></ProvisionedProductDetails>
      {provisionedProduct ?
        <ProvisionedProductLogin
          loginPromptVisible={loginPromptVisible}
          setLoginPromptVisible={setLoginPromptVisible}
          provisionedProduct={provisionedProduct}
          i18n={i18nWorkbenchLogin}
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
          headerText={i18nWorkbenchDetails.confirmRemoveLabel}
          content={
            <ProvisionedProductsToDeleteList
              targets={[provisionedProduct]}
              translations={i18nWorkbenchDetails}
            />
          }
          cancelText={i18nWorkbenchDetails.deprovisionModalCancel}
          confirmText={i18nWorkbenchDetails.deprovisionModalOK}
          confirmButtonLoading={false}
          visible={turnDownConfirmVisible}
        />
        : null }
    </>
  );
}
