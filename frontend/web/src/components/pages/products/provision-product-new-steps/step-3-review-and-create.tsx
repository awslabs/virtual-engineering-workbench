import {
  Alert,
  Box,
  ColumnLayout,
  Container,
  Header,
  SpaceBetween,
} from '@cloudscape-design/components';
import { FC } from 'react';
import { InfoBox } from '../../shared/info-box';
import {
  ProductParameterState,
  visibleParameters
} from '../../../../hooks/provisioning';
import { ProductParameter } from '../../../../services/API/proserve-wb-provisioning-api';
import { StepsTranslations } from '../../../../hooks/provisioning/provision-product.logic';
import { EnabledRegion, REGION_NAMES } from '../../../user-preferences';

export interface Step3SelectedVersion {
  versionName: string,
}

interface Params {
  selectedVersionRegion: string,
  selectedVersionStage: string,
  selectedVersion?: Step3SelectedVersion,
  productParameterState: ProductParameterState,
  productParameters: ProductParameter[],
  additionalInfo?: JSX.Element,
  i18nSteps: StepsTranslations,
  vvJobName?: string,
  vvPlatform?: string,
  vvVersion?: string,
  vvArtifactUpstreamPath?: string,
  isExperimentalWorkbench?: boolean,
  isExperimentalWorkbenchAvailable?: boolean,
}

// eslint-disable-next-line complexity
const reviewAndCreateStep: FC<Params> = ({
  selectedVersionRegion,
  selectedVersionStage,
  selectedVersion,
  productParameterState,
  productParameters,
  additionalInfo,
  i18nSteps,
  vvJobName,
  vvPlatform,
  vvVersion,
  vvArtifactUpstreamPath,
  isExperimentalWorkbench,
  isExperimentalWorkbenchAvailable,
}) => {
  const translatedRegionName = REGION_NAMES[
    selectedVersionRegion as EnabledRegion
  ] || selectedVersionRegion;

  function renderWorkbenchParameters() {
    return <>
      {productParameters.filter(visibleParameters).map(p => renderProductParameters(p))}
    </>;
  }

  // eslint-disable-next-line complexity
  function renderProductParameters(productParameter: ProductParameter) {
    const productParameterValue = productParameterState[productParameter.parameterKey] ||
      (productParameter.defaultValue ?? '');
    const optionLabels = productParameter.parameterMetaData?.optionLabels;
    return <InfoBox
      label={productParameter.parameterMetaData?.label ?? productParameter.parameterKey}
      value={(optionLabels as { [key: string]: string })?.[productParameterValue] ||
        productParameterValue}
      key={productParameter.parameterKey} />;
  }

  const isVVAdditionalConfiguration = () => {
    return vvJobName || vvPlatform || vvVersion || vvArtifactUpstreamPath;
  };

  const getValue = (value: string | undefined) => {
    return value ? value : 'N/A';
  };

  const getPlatformInfo = () => {
    return isVVAdditionalConfiguration() && <Alert statusIconAriaLabel="Info">
      {i18nSteps.mappingInfo(
        getValue(vvJobName),
        getValue(vvPlatform),
        getValue(vvVersion),
        getValue(vvArtifactUpstreamPath)
      )}
    </Alert>;
  };

  function renderExperimentalDisclaimer() {
    if (!isExperimentalWorkbenchAvailable || !isExperimentalWorkbench) {
      return <></>;
    }

    return <Alert type="warning">
      {i18nSteps.experimentalDisclaimer}
    </Alert>;
  }

  return (
    <SpaceBetween size={'xxl'}>
      {getPlatformInfo()}
      {!!additionalInfo &&
        <Box>
          {additionalInfo}
        </Box>
      }
      <Box>
        <SpaceBetween size={'s'}>
          {renderExperimentalDisclaimer()}
          <Box variant='h3'>{i18nSteps.stepOne}</Box>
          <Container
            data-test="workbench-settings-panel"
            header={
              <Header variant="h2">{i18nSteps.settingsContainerHeader}</Header>
            }
          >
            <SpaceBetween size={'m'}>
              <ColumnLayout columns={
                // eslint-disable-next-line @typescript-eslint/no-magic-numbers
                isExperimentalWorkbenchAvailable ? 4 : 3
              }>
                <InfoBox label={i18nSteps.region} value={translatedRegionName} />
                {isExperimentalWorkbenchAvailable &&
                  <InfoBox
                    label={i18nSteps.experimentalLabel}
                    value={isExperimentalWorkbench ? 'Yes' : 'No'}
                  />
                }
                <InfoBox label={i18nSteps.stage} value={selectedVersionStage} />
                <InfoBox label={i18nSteps.version} value={selectedVersion!.versionName} />
              </ColumnLayout>
            </SpaceBetween>
          </Container>
        </SpaceBetween>
      </Box>

      <Box>
        <SpaceBetween size='s'>
          <Box variant='h3'>{i18nSteps.stepTwo}</Box>
          <Container
            data-test="workbench-parameters-panel"
            header={
              <Header variant="h2">{i18nSteps.parametersContainerHeader}</Header>
            }
          >
            <SpaceBetween size={'m'}>
              {renderWorkbenchParameters()}
            </SpaceBetween>
          </Container>
        </SpaceBetween>
      </Box>
    </SpaceBetween>
  );
};

export { reviewAndCreateStep as ReviewAndCreateStep };