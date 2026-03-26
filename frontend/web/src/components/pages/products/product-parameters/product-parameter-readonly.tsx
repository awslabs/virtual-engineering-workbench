import { Box, FormField } from '@cloudscape-design/components';
import { FC } from 'react';
import { ParameterLabel, ParameterProps } from './parameter-types';

type ReadOnlyParameterProps = ParameterProps;

const productParameterReadonly: FC<ReadOnlyParameterProps> = ({ parameter, parameterLabelSubHeading }) => {

  const parameterLabel = parameter.parameterMetaData?.label || parameter.parameterKey;

  return <>
    <FormField
      label={renderLabel()}
      description={parameter.description}
    >
      <Box data-test={`param-readonly-${parameter.parameterKey}`}>{parameter.defaultValue}</Box>
    </FormField>
  </>;

  function renderLabel() {
    return <>
      <ParameterLabel
        parameterLabel={parameterLabel}
        parameterLabelSubHeading={parameterLabelSubHeading}
      />
    </>;
  }
};

export { productParameterReadonly as ProductParameterReadonly };
