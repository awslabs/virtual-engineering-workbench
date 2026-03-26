// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { ReactNode, FC } from 'react';
import { useRoleAccessToggle } from '../../../hooks/role-access-toggle';
import { RoleBasedFeature } from '../../../state';

type Props = {
  children: ReactNode,
  feature: RoleBasedFeature,
};

const roleAccessToggle: FC<Props> = ({ children, feature }: Props) => {

  const isFeatureAccessible = useRoleAccessToggle();

  if (isFeatureAccessible(feature)) {
    return (
      <>{children}</>
    );
  }

  return null;
};

export { roleAccessToggle as RoleAccessToggle };