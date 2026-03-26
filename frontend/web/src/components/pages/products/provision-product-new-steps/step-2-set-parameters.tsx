import {
  Alert,
  Box,
  Button,
  Container,
  FormField,
  Header,
  RadioGroup,
  SpaceBetween,
  Spinner
} from '@cloudscape-design/components';
import { FC } from 'react';
import { ProductParameter } from '../../../../services/API/proserve-wb-provisioning-api';
import {
  DropdownParameterRenderer,
  FreetextParameterRenderer,
  ParameterRenderer,
  ReadonlyParameterRenderer
} from '../product-parameters';
import {
  ProductParameterState,
  visibleParameters
} from '../../../../hooks/provisioning';
import { StepsTranslations } from '..';

interface Params {
  productParametersLoading?: boolean,
  productParameters: ProductParameter[],
  productParameterState: ProductParameterState,
  previouslyEnteredParameterNames?: Set<string>,
  showInfoForNewParameterNames?: boolean,
  handleProductParameterChange: (key: string, value?: string) => void,
  parameterInfoClicked?: () => void,
  i18nSteps: StepsTranslations,
  vvJobName?: string,
  vvPlatform?: string,
  vvVersion?: string,
  vvArtifactUpstreamPath?: string,
  isExperimentalWorkbench?: boolean,
  setIsExperimentalWorkbench?: (value: boolean) => void,
  isExperimentalWorkbenchAvailable?: boolean,
}

const PARAMETER_RENDERERS: ParameterRenderer[] = [
  new DropdownParameterRenderer(),
  new FreetextParameterRenderer(),
  new ReadonlyParameterRenderer(),
];

const setParametersStep: FC<Params> = ({
  productParametersLoading,
  productParameters,
  productParameterState,
  previouslyEnteredParameterNames,
  showInfoForNewParameterNames,
  handleProductParameterChange,
  parameterInfoClicked,
  i18nSteps,
  vvJobName,
  vvPlatform,
  vvVersion,
  vvArtifactUpstreamPath,
  isExperimentalWorkbench,
  setIsExperimentalWorkbench,
  isExperimentalWorkbenchAvailable,
}: Params) => {

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

  return <SpaceBetween size={'s'}>
    {getPlatformInfo()}
    <Container
      header={<Header variant="h2">{i18nSteps.parametersContainerHeader}</Header>}
      data-test='product-parameters'
    >
      {!!productParametersLoading && <Spinner />}
      {!productParametersLoading && renderAllParameters()}
    </Container>
  </SpaceBetween>;

  function renderAllParameters() {
    return <SpaceBetween direction="vertical" size="l">
      {renderWorkbenchParameters()}
    </SpaceBetween>;
  }

  function renderWorkbenchParameters() {
    return <>
      {renderExperimentalDisclaimer()}
      {renderExperimentalChoice()}
      {productParameters.filter(visibleParameters).map(p => renderProductParameter(p))}
    </>;
  }

  function renderProductParameter(value: ProductParameter): JSX.Element {
    const renderer = PARAMETER_RENDERERS.find(r => r.canHandle(value)) || new ReadonlyParameterRenderer();

    return <Box key={value.parameterKey}>
      {
        renderer.render({
          parameter: {
            ...value,
            defaultValue: value.parameterConstraints?.allowedValues?.includes(
              productParameterState[value.parameterKey] || ''
            ) ? productParameterState[value.parameterKey] : value.defaultValue
          },
          onChange: (newVal: string | undefined) => {
            handleProductParameterChange(value.parameterKey, newVal);
          },
          parameterLabelSubHeading: renderParameterLabelSubHeading(value.parameterKey),
        })
      }
    </Box>;
  }

  function renderParameterLabelSubHeading(parameterKey: string): JSX.Element | undefined {
    if (!showInfoForNewParameterNames || previouslyEnteredParameterNames?.has(parameterKey)) {
      return undefined;
    }
    return <SpaceBetween direction='horizontal' size='xxxs' data-test={`wb-new-param-${parameterKey}`}>
      <Box variant="strong"><i>{i18nSteps.parameterNew}</i></Box>
      <Box>|</Box>
      <Button variant="inline-link" onClick={parameterInfoClicked}>{i18nSteps.parameterInfo}</Button>
    </SpaceBetween>;
  }

  function renderExperimentalDisclaimer() {
    if (!isExperimentalWorkbenchAvailable) {
      return <></>;
    }

    return <Alert type="warning">
      {i18nSteps.experimentalDisclaimer}
    </Alert>;
  }

  function renderExperimentalChoice() {
    if (!isExperimentalWorkbenchAvailable) {
      return <></>;
    }

    return (
      <FormField
        label={i18nSteps.experimentalHeading}
        description={i18nSteps.experimentalDescription}
      >
        <RadioGroup
          onChange={({ detail: { value } }) => {
            setIsExperimentalWorkbench?.(value === i18nSteps.experimentalOptionYesValue);
          }}
          value={
            isExperimentalWorkbench
              ? i18nSteps.experimentalOptionYesValue
              : i18nSteps.experimentalOptionNoValue
          }
          items={[
            {
              value: i18nSteps.experimentalOptionNoValue,
              label: i18nSteps.experimentalOptionNoLabel,
            },
            {
              value: i18nSteps.experimentalOptionYesValue,
              label: i18nSteps.experimentalOptionYesLabel,
            },
          ]}
        />
      </FormField>
    );
  }
};

export { setParametersStep as SetParametersStep };