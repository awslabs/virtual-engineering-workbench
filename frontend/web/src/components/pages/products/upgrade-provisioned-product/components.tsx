import { Alert, Box, HelpPanel } from '@cloudscape-design/components';
import { FC, useState } from 'react';
import { UpgradeProvisionedProductWizardProps, UpgradeWarningProps } from './interface';
import { ProvisionProductWizard } from '..';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { getWorkbenchFeatureToggles } from '../../../feature-toggles/feature-toggle-workbench.hook';
import { ProvisionedProduct } from '../../../../services/API/proserve-wb-provisioning-api';
import { Feature } from '../../../feature-toggles/feature-toggle.state';

export const Step1ConfigureSettingsHelp: FC<object> = () => {
  return <HelpPanel
    header={<h2>View settings</h2>}
  >
    <Box variant="p">
      Shows the default settings for the workbench upgrade.
    </Box>
    <Box variant='h4'>Default settings</Box>
    <Box variant="p">
      The workbench will be upgraded in its current stage and region to the latest released version.
    </Box>
    <Box variant="p">
      If you require different settings then you must create a new workbench.
    </Box>
  </HelpPanel>;
};

export const Step2ConfigureSettingsHelp: FC<object> = () => {
  return <HelpPanel
    header={<h2>Set parameters</h2>}
  >
    <Box variant="p">
      Setting parameters for the workbench upgrade.
    </Box>
    <Box variant="p">
      The workbench will be upgraded based on this parameter setting.
    </Box>
    <Box variant='h4'>Preset parameters</Box>
    <Box variant="p">
      Parameters of the current workbench.
      They are displayed as default values in the selection fields.
      These can be maintained or modified as required for the upgraded workbench.
    </Box>
    <Box variant='h4'>New parameters</Box>
    <Box variant="p">
      A new workbench version may include new parameters.
      These must be set up for the first time to proceed with the workbench upgrade.
    </Box>
  </HelpPanel>;
};

export enum Steps {
  Step1 = 'Step1',
  Step2 = 'Step2',
  Step3 = 'Step3'
}

export const UpgradeWarning: FC<UpgradeWarningProps> = ({ translations }: UpgradeWarningProps) => {
  return <Alert header={translations.warningHeader} type="warning">{translations.warningContent}</Alert>;
};

export const UpgradeProvisionedProductWizard = ({
  translations,
  stepsTranslations,
  returnPage,
  startingUpgradeInProcess,
  provisionedProduct,
  selectedVersion,
  productParameterState,
  productVersionsLoading,
  handleProductParameterChange,
  previouslyEnteredParameterNames,
  setActiveHelpPanel,
  setToolsOpen,
  toolsOpen,
  upgradeWorkbench,
}: UpgradeProvisionedProductWizardProps) => {

  const { navigateTo } = useNavigationPaths();

  const EMPTY_ARRAY_LENGTH = 0;
  const [activeStepIndex, setActiveStepIndex] = useState(EMPTY_ARRAY_LENGTH);

  const workingDirectoryEnabled = isWorkingDirectoryEnabled(provisionedProduct);

  return <>
    <ProvisionProductWizard
      hideMaintenanceWindow={true}
      wizardSubmitInProgress={startingUpgradeInProcess}
      wizardSubmitAction={() => upgradeWorkbench().then(() => {
        navigateTo(returnPage);
      })}
      wizardCancelAction={() => navigateTo(returnPage)}
      activeStepChanged={(step) => setActiveHelpPanel(Object.values(Steps)[step])}
      step1Params={{
        selectedVersionRegion: provisionedProduct.region,
        selectedVersionStage: provisionedProduct.stage,
        selectedVersion,
        availableRegions: [provisionedProduct.region],
        availableStages: [provisionedProduct.stage],
        productVersions: selectedVersion ? [selectedVersion] : [],
        productVersionsLoading,
        disabled: true,
        productVersionMetadata: selectedVersion?.metadata,
        i18nSteps: stepsTranslations,
      }}
      step2Params={{
        productParameters: selectedVersion?.parameters || [],
        productParametersLoading: productVersionsLoading,
        productParameterState,
        handleProductParameterChange,
        previouslyEnteredParameterNames,
        showInfoForNewParameterNames: true,
        parameterInfoClicked: () => setToolsOpen(!toolsOpen),
        i18nSteps: stepsTranslations
      }}
      step3Params={{
        selectedVersionRegion: provisionedProduct.region,
        selectedVersionStage: provisionedProduct.stage,
        selectedVersion,
        productParameterState,
        productParameters: selectedVersion?.parameters || [],
        additionalInfo: getUpgradeWarning(),
        i18nSteps: stepsTranslations
      }}
      i18nStrings={translations}
      activeStepIndex={activeStepIndex}
      setActiveStepIndex={setActiveStepIndex} />
  </>;

  function isWorkingDirectoryEnabled(provisionedProduct: ProvisionedProduct): boolean {
    const featureToggle = getWorkbenchFeatureToggles(provisionedProduct.outputs || []).find(
      (ftr) => ftr.feature === Feature.WorkbenchWorkingDirectoryEnabled
    );

    return featureToggle?.enabled || false;
  }

  function getUpgradeWarning() {
    if (!workingDirectoryEnabled) {
      return <UpgradeWarning translations={translations} />;
    }
    return undefined;
  }
};