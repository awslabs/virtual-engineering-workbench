import { FC } from 'react';
import { ProductParameter } from '../../../../services/API/proserve-wb-provisioning-api';
import { Box, SpaceBetween } from '@cloudscape-design/components';

export type ParameterProps = {
  parameter: ProductParameter,
  parameterLabelSubHeading?: JSX.Element,
};

type ParameterLabelProps = {
  parameterLabel: string,
  parameterLabelSubHeading?: JSX.Element,
};

export const ParameterLabel: FC<ParameterLabelProps> = ({
  parameterLabel,
  parameterLabelSubHeading,
}) => {
  if (!parameterLabelSubHeading) {
    return <>{parameterLabel}</>;
  }
  return <SpaceBetween direction="horizontal" size="xxs">
    <Box variant='strong'>{parameterLabel}</Box>
    <Box>-</Box>
    {parameterLabelSubHeading}
  </SpaceBetween>;
};