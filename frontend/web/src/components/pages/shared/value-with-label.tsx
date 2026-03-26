import React from 'react';
import { Box, SpaceBetween } from '@cloudscape-design/components';

type ValueWithLabelProps = {
  label: string,
  children: React.ReactNode,
  labelPostfix?: React.ReactNode,
} & {
  [key: `data-${string}`]: object,
};

export const ValueWithLabel = ({
  label,
  children,
  labelPostfix = undefined,
  ...rest
}: ValueWithLabelProps) => {
  return (
    <div {...rest}>
      <SpaceBetween direction="horizontal" size="xxs">
        <Box variant="awsui-key-label">
          {label}
        </Box>
        {labelPostfix}
      </SpaceBetween>
      <div>{children}</div>
    </div>
  );
};