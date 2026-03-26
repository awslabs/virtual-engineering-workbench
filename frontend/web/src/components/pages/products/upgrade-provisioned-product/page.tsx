import { useLocation } from 'react-router-dom';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../state';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { useState } from 'react';
import { LocationState, UpgradeProvisionedProductProps } from './interface';
import { upgradeProvisionedProduct } from '../../../../hooks/provisioning/upgrade-provisioned-product.logic';
import { BreadcrumbItem } from '../../../layout';
import {
  Step1ConfigureSettingsHelp,
  Step2ConfigureSettingsHelp,
  Steps,
  UpgradeProvisionedProductWizard
} from './components';
import { HelpPanel } from '@cloudscape-design/components';

const STEP_HELP_PANEL_MAP: { [key in Steps]: JSX.Element } = {
  Step1: <Step1ConfigureSettingsHelp/>,
  Step2: <Step2ConfigureSettingsHelp/>,
  Step3: <HelpPanel/>,
};

/* eslint complexity: off */
export const UpgradeProvisionedProduct = ({
  translations,
  stepsTranslations,
  returnPage,
  serviceApi
}: UpgradeProvisionedProductProps): JSX.Element => {

  const selectedProject = useRecoilValue(selectedProjectState);
  const { navigateTo, getPathFor } = useNavigationPaths();
  const location = useLocation();
  const [activeHelpPanel, setActiveHelpPanel] = useState(Steps.Step1);
  const [toolsOpen, setToolsOpen] = useState(false);


  const {
    provisionedProduct,
  } = (location.state || {}) as LocationState;

  if (
    !provisionedProduct ||
    !selectedProject.projectId ||
    !provisionedProduct.newVersionId ||
    !provisionedProduct.newVersionName
  ) {
    navigateTo(returnPage);
    return <></>;
  }

  const {
    productVersionsLoading,
    versionForUpgrade,
    productParameterState,
    handleProductParameterChange,
    previouslyEnteredParameterNames,
    startingUpgradeInProcess,
    upgrade,
  } = upgradeProvisionedProduct({
    serviceApi,
    projectId: selectedProject.projectId,
    productId: provisionedProduct.productId,
    provisionedProductId: provisionedProduct.provisionedProductId,
    selectedVersionForUpgrade: {
      versionId: provisionedProduct.newVersionId,
      versionName: provisionedProduct.newVersionName,
      stage: provisionedProduct.stage,
      region: provisionedProduct.region,
    },
    previouslyEnteredParameters: provisionedProduct.provisioningParameters
  });

  return <WorkbenchAppLayout
    breadcrumbItems={getBreadcrumbItems()}
    content={<UpgradeProvisionedProductWizard
      translations={translations}
      stepsTranslations={stepsTranslations}
      returnPage={returnPage}
      startingUpgradeInProcess={startingUpgradeInProcess}
      provisionedProduct={provisionedProduct}
      selectedVersion={versionForUpgrade}
      productParameterState={productParameterState}
      productVersionsLoading={productVersionsLoading}
      handleProductParameterChange={handleProductParameterChange}
      previouslyEnteredParameterNames={previouslyEnteredParameterNames}
      setActiveHelpPanel={setActiveHelpPanel}
      setToolsOpen={setToolsOpen}
      toolsOpen={toolsOpen}
      upgradeWorkbench={upgrade}
    />}
    contentType="default"
    tools={renderTools()}
    toolsOpen={toolsOpen}
    onToolsChange={(evt) => setToolsOpen(evt.detail.open)}
  />;

  function getBreadcrumbItems(): BreadcrumbItem[] {
    return [
      { path: translations.breadcrumbL1, href: getPathFor(returnPage) },
      { path: translations.breadcrumbL2, href: '#' },
    ];
  }

  function renderTools() {
    if (activeHelpPanel in STEP_HELP_PANEL_MAP) {
      return STEP_HELP_PANEL_MAP[activeHelpPanel];
    }
    return (
      <HelpPanel/>
    );
  }


};