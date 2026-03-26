// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import {
  SideNavigation,
  SideNavigationProps,
} from '@cloudscape-design/components';
import { FC } from 'react';
import { RoleBasedFeature } from '../../../state';
import { UserType } from '../../session-management/logged-user';
import { Feature } from '../../feature-toggles/feature-toggle.state';
import { useLocation, useNavigate } from 'react-router-dom';
import { useFeatureToggles } from '../../feature-toggles/feature-toggle.hook';
import { useRoleAccessToggle } from '../../../hooks/role-access-toggle';
import { useNavigationPaths } from './navigation-paths.logic';
import { RouteNames } from './navigation.static';
import { NavigationPreset } from './navigation-preset.logic';

/* eslint @typescript-eslint/no-explicit-any: "off" */
interface Props {
  user?: UserType,
}

const i18n = {
  userNavigationHeaderWorkbenches: 'Workbenches',
  userNavigationMyWorkbenches: 'My workbenches',
  userNavigationAllWorkbenches: 'All workbenches',
  adminNavigationHeaderAdministration: 'Administration',
  adminNavigationMembers: 'Members',
  adminNavigationTechnologies: 'Technologies',
  productNavigationHeaderProductManagement: 'Product management',
  productNavigationProducts: 'Products',
  productNavigationComponents: 'Components',
  productNavigationRecipes: 'Recipes',
  productNavigationImages: 'Images',
  productNavigationPipelines: 'Pipelines',
  productNavigationMandatoryComponentsLists: 'Mandatory components lists',
  provisionedProductsAdministration: 'Provisioned products',
  userNavigationHeaderVirtualTargets: 'Virtual targets',
  userNavigationMyVirtualTargets: 'My virtual targets',
  userNavigationAllVirtualTargets: 'All virtual targets',
};

/* eslint complexity: "off" */
export const Navigation: FC<Props> = ({ user }) => {
  const history = useLocation();
  const navigate = useNavigate();
  const { getActiveItem, getPathFor } = useNavigationPaths();
  const { isFeatureEnabled } = useFeatureToggles();
  const isFeatureAccessible = useRoleAccessToggle();
  const navigation = NavigationPreset.getInstance();

  function getWorkbenchAuthItems(): SideNavigationProps.Item[] {
    const availableWorkbenchesLink: SideNavigationProps.Item = {
      type: 'link',
      text: i18n.userNavigationAllWorkbenches,
      href: getPathFor(RouteNames.AvailableWorkbenches),
    };

    const myWorkbenchesLink: SideNavigationProps.Item = {
      type: 'link',
      text: i18n.userNavigationMyWorkbenches,
      href: getPathFor(RouteNames.MyWorkbenches),
    };

    const currentMyWorkbenchesLink = tryGetLink(
      RoleBasedFeature.ListMyWorkbenches,
      myWorkbenchesLink
    );

    const menuItems: SideNavigationProps.Item[] = [
      {
        type: 'section',
        text: i18n.userNavigationHeaderWorkbenches,
        items: [availableWorkbenchesLink, ...currentMyWorkbenchesLink],
        defaultExpanded: navigation.getItem(i18n.userNavigationHeaderWorkbenches),
      },
    ];

    const availableVirtualTargetsLink: SideNavigationProps.Item = {
      type: 'link',
      text: i18n.userNavigationAllVirtualTargets,
      href: getPathFor(RouteNames.AvailableVirtualTargets),
    };

    const virtualTargetsLink: SideNavigationProps.Item = {
      type: 'link',
      text: i18n.userNavigationMyVirtualTargets,
      href: getPathFor(RouteNames.MyVirtualTargets),
    };

    menuItems.push({
      type: 'section',
      text: i18n.userNavigationHeaderVirtualTargets,
      items: [availableVirtualTargetsLink, virtualTargetsLink],
      defaultExpanded: navigation.getItem(i18n.userNavigationHeaderVirtualTargets),
    });

    if (isFeatureAccessible(RoleBasedFeature.ManageProducts)) {
      menuItems.push({
        type: 'section',
        text: i18n.productNavigationHeaderProductManagement,
        items: [
          {
            type: 'link',
            text: i18n.productNavigationMandatoryComponentsLists,
            href: getPathFor(RouteNames.MandatoryComponentsLists),
          },
          {
            type: 'link',
            text: i18n.productNavigationComponents,
            href: getPathFor(RouteNames.Components),
          },
          {
            type: 'link',
            text: i18n.productNavigationRecipes,
            href: getPathFor(RouteNames.Recipes),
          },
          {
            type: 'link',
            text: i18n.productNavigationImages,
            href: getPathFor(RouteNames.Images),
          },
          {
            type: 'link',
            text: i18n.productNavigationPipelines,
            href: getPathFor(RouteNames.Pipelines),
          },
          {
            type: 'link',
            text: i18n.productNavigationProducts,
            href: getPathFor(RouteNames.Products),
          },
        ],
        defaultExpanded: navigation.getItem(i18n.productNavigationHeaderProductManagement),
      });
    }

    if (
      isFeatureAccessible(RoleBasedFeature.ManageEnrolments) ||
      isFeatureAccessible(RoleBasedFeature.ManageTechnologies) ||
      isFeatureAccessible(RoleBasedFeature.ProvisionedProductsAdministration)
    ) {
      menuItems.push({
        type: 'section',
        text: i18n.adminNavigationHeaderAdministration,
        items: [
          ...tryGetLink(
            RoleBasedFeature.ProvisionedProductsAdministration,
            {
              type: 'link',
              text: i18n.provisionedProductsAdministration,
              href: getPathFor(RouteNames.ProvisionedProductsAdministration),
            }),
          ...tryGetLink(
            RoleBasedFeature.ManageEnrolments,
            {
              type: 'link',
              text: i18n.adminNavigationMembers,
              href: getPathFor(RouteNames.ProjectMembers),
            }),
          ...tryGetLink(
            RoleBasedFeature.ManageTechnologies,
            {
              type: 'link',
              text: i18n.adminNavigationTechnologies,
              href: getPathFor(RouteNames.Technologies),
            }),
        ],
        defaultExpanded: navigation.getItem(i18n.adminNavigationHeaderAdministration),
      });
    }
    return menuItems;
  }

  type BothFeature = Feature | RoleBasedFeature;
  function isFeatureToggle(item: BothFeature): item is Feature {
    return (item as Feature).trim !== undefined;
  }

  function tryGetLink(
    feature: BothFeature,
    item: SideNavigationProps.Item
  ): SideNavigationProps.Item[] {
    if (isFeatureToggle(feature)) {
      return isFeatureEnabled(feature) ? [item] : [];
    }
    return isFeatureAccessible(feature) ? [item] : [];
  }

  function renderNavigation(): SideNavigationProps.Item[] {
    return getWorkbenchAuthItems();
  }

  if (user) {
    return (
      <SideNavigation
        items={renderNavigation()}
        activeHref={getActiveItem(history.pathname)}
        onFollow={(evt) => {
          if (!evt.detail.external) {
            evt.preventDefault();
            navigate(evt.detail.href);
          }
        }}
        onChange={(event) => navigation.setItem(event.detail.item.text, event.detail.expanded)}
        data-test="side-navigation"
        data-custom-navbar
      />
    );
  }

  return (
    <SideNavigation
      items={[]}
    />
  );
};
