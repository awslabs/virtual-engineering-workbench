import {
  Box,
  HelpPanel,
  SpaceBetween,
} from '@cloudscape-design/components';
import { FC, useState } from 'react';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { useLocation, useParams } from 'react-router-dom';
import { BreadcrumbItem } from '../../../layout';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout';
import './style.scss';
import { ProvisionProductWizard, Step1Version, i18nWorkbenchSteps } from '../provision-product-new-steps';
import { AvailableVersionDistribution as WorkbenchVersionDistribution }
  from '../../../../services/API/proserve-wb-publishing-api';
import { AvailableVersionDistribution as VirtualTargetVersionDistribution }
  from '../../../../services/API/proserve-wb-provisioning-api';
import { useProvisionProduct } from '../../../../hooks/provisioning/provision-product.logic';
import { i18nProvisionWorkbench } from '.';

/* eslint complexity: "off" */

interface LocationState {
  productName?: string,
  productDescription?: string,
  productType?: string,
  productAccountId?: string,
  availableRegions?: string[],
  availableStages?: string[],
  vvJobName?: string,
  vvPlatform?: string,
  vvVersion?: string,
  vvArtifactUpstreamPath?: string,
}

export type ProvisionProductTranslations = typeof i18nProvisionWorkbench;
export type StepsTranslations = typeof i18nWorkbenchSteps;

interface ProvisionProductProps {
  i18n: ProvisionProductTranslations,
  i18nSteps: StepsTranslations,
  baseRouteName: RouteNames,
  completionRouteName: RouteNames,
}

const ProvisionProductNew: FC<ProvisionProductProps> = ({
  i18n,
  i18nSteps,
  baseRouteName,
  completionRouteName,
}) => {
  const { navigateTo, getPathFor } = useNavigationPaths();
  const location = useLocation();
  const { id } = useParams();

  const EMPTY_ARRAY_LENGTH = 0;
  const STEP_ONE = 0;
  const STEP_TWO = 1;
  const STEP_THREE = 2;
  const [activeStepIndex, setActiveStepIndex] = useState(EMPTY_ARRAY_LENGTH);

  const {
    productType,
    availableRegions,
    availableStages,
    vvJobName,
    vvPlatform,
    vvVersion,
    vvArtifactUpstreamPath
  } = (location.state || {}) as LocationState;

  if (!id) {
    navigateTo(baseRouteName);
  }

  const isWorkbench = () => {
    return productType === 'WORKBENCH';
  };

  const {
    selectedVersionRegion,
    setSelectedVersionRegion,
    selectedVersionStage,
    setSelectedVersionStage,
    selectedVersion,
    setSelectedVersion,
    productVersionsLoading,
    handleProductParameterChange,
    productParameters,
    productParametersLoading,
    productParameterState,
    provisionProduct,
    productProvisionInProgress,
    productVersionMetadata,
    productVersions,
    isExperimentalWorkbench,
    setIsExperimentalWorkbench,
    isExperimentalWorkbenchAvailable,
    selectedAvailableProduct,
  } = useProvisionProduct({
    productId: id || '',
    availableRegions: availableRegions || [],
    availableStages: availableStages || [],
    i18n: i18n,
    onProvisioned: () => navigateTo(completionRouteName),
    vvJobName: vvJobName,
    vvPlatform: vvPlatform,
    vvVersion: vvVersion,
    vvArtifactUpstreamPath: vvArtifactUpstreamPath,
    productType: productType,
  });

  return <>
    <WorkbenchAppLayout
      breadcrumbItems={getBreadcrumbItems()}
      content={renderContent()}
      contentType="default"
      tools={renderTools()}
    />
  </>;

  function renderContent() {
    return <>
      <ProvisionProductWizard
        wizardSubmitInProgress={productProvisionInProgress}
        wizardSubmitAction={provisionProduct}
        wizardCancelAction={() => navigateTo(baseRouteName)}
        activeStepIndex={activeStepIndex}
        setActiveStepIndex={setActiveStepIndex}
        step1Params={{
          selectedVersionRegion,
          setSelectedVersionRegion,
          selectedVersionStage,
          setSelectedVersionStage,
          selectedVersion,
          setSelectedVersion: handleSelectedVersion,
          availableRegions: availableRegions || [],
          availableStages: availableStages || [],
          productVersions,
          productVersionsLoading,
          productVersionMetadata,
          i18nSteps,
          vvJobName,
          vvPlatform,
          vvVersion,
          vvArtifactUpstreamPath,
          productType,
        }}
        step2Params={{
          productParameters: productParameters ?? [],
          productParametersLoading,
          productParameterState,
          handleProductParameterChange,
          i18nSteps,
          vvJobName,
          vvPlatform,
          vvVersion,
          vvArtifactUpstreamPath,
          isExperimentalWorkbench,
          setIsExperimentalWorkbench,
          isExperimentalWorkbenchAvailable,
        }}
        step3Params={{
          selectedVersionRegion,
          selectedVersionStage,
          selectedVersion,
          productParameterState,
          productParameters: productParameters ?? [],
          i18nSteps,
          vvJobName,
          vvPlatform,
          vvVersion,
          vvArtifactUpstreamPath,
          isExperimentalWorkbench,
          isExperimentalWorkbenchAvailable,
        }}
        i18nStrings={i18n}
      />
    </>;
  }

  function handleSelectedVersion(version?: Step1Version) {
    const versions = productVersions as unknown[];
    if (!isWorkbench()) {
      setSelectedVersion((versions as VirtualTargetVersionDistribution[])
        .find(x => x.versionId === version?.versionId) as WorkbenchVersionDistribution);
    } else {
      setSelectedVersion((versions as WorkbenchVersionDistribution[])
        .find(x => x.versionId === version?.versionId));
    }
  }

  function getBreadCrumbPathWithProdname() {
    return selectedAvailableProduct?.productName ?
      `${i18n.breadcrumbL2}: ${selectedAvailableProduct?.productName}` :
      i18n.breadcrumbL2;
  }

  function getBreadcrumbItems(): BreadcrumbItem[] {
    return [
      {
        path: i18n.breadcrumbL1,
        href: getPathFor(baseRouteName)
      },
      { path: getBreadCrumbPathWithProdname(), href: '#' },
    ];
  }

  function renderTools() {
    return (
      <>
        {activeStepIndex === STEP_ONE && <HelpPanel header={<h2>{i18n.step1InfoPanelHeader}</h2>}>
          <SpaceBetween size={'s'}>
            <Box variant="awsui-key-label">{i18n.step1InfoPanelLabel}</Box>
            <Box variant="p">{i18n.step1InfoPanelMessage1}</Box>
            {isExperimentalWorkbenchAvailable &&
                <Box variant="p">
                  {i18n.step1InfoPanelMessageExperimentalInstance}
                </Box>
            }
            <Box variant="p">{i18n.step1InfoPanelMessage2}</Box>
            <Box variant="p">{i18n.step1InfoPanelMessage3}</Box>
          </SpaceBetween>
        </HelpPanel>}

        {activeStepIndex === STEP_TWO && <HelpPanel header={<h2>{i18n.step2InfoPanelHeader}</h2>}>
          <SpaceBetween size={'s'}>
            <Box variant="awsui-key-label">{i18n.step2InfoPanelLabel}</Box>
            <Box variant="p">{i18n.step2InfoPanelMessage1}</Box>
            <Box variant="p">{i18n.step2InfoPanelMessage2}</Box>
          </SpaceBetween>
        </HelpPanel>}

        {activeStepIndex === STEP_THREE && <HelpPanel header={<h2>{i18n.step3InfoPanelHeader}</h2>}>
          <SpaceBetween size={'s'}>
            <Box variant="p">{i18n.step3InfoPanelMessage1}</Box>
          </SpaceBetween>
        </HelpPanel>}
      </>
    );
  }
};

export { ProvisionProductNew };
