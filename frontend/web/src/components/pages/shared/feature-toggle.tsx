// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { ReactNode, FC } from 'react';
import { useFeatureToggles } from '../../feature-toggles/feature-toggle.hook';
import { Feature } from '../../feature-toggles/feature-toggle.state';


type Props = {
  children: ReactNode,
  feature: Feature,
};

const featureToggle: FC<Props> = ({ children, feature }: Props) => {

  const { isFeatureEnabled } = useFeatureToggles();

  if (isFeatureEnabled(feature)) {
    return (
      <>{children}</>
    );
  }

  return null;
};

export { featureToggle as FeatureToggle };