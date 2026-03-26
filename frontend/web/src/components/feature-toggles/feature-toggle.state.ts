// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { atom, atomFamily } from 'recoil';
import features, { FeatureToggleConfigItem } from './features';
import { AppConfig } from '../../utils/app-config';


export enum Feature {
  // Permanent features
  AuthorizeUserIp = 'AuthorizeUserIp',
  BetaUserInfoText = 'BetaUserInfoText',

  // Permanent workbench features
  DCVConnectionOptions = 'DCVConnectionOptions',
  RDPConnectionOption = 'RDPConnectionOption',
  WorkbenchWorkingDirectoryEnabled = 'WorkbenchWorkingDirectoryEnabled',

  // Feature Toggles
  ExperimentalWorkbench = 'ExperimentalWorkbench',
  ProductMetadata = 'ProductMetadata',
  ProvisionedProductManualUpdates = 'ProvisionedProductManualUpdates',
  WithdrawFromProgram = 'WithdrawFromProgram',
}

export interface FeatureToggleItem {
  version: string,
  feature: Feature,
  description?: string,
  enabled: boolean,
}

export interface WorkbenchFeatureToggleItem {
  feature: Feature,
  description?: string,
  enabled: boolean,
  userOverrides: string[],
}

export function loadFeaturesToggleItems():FeatureToggleItem[] {
  const items:FeatureToggleItem[] = [];
  for (const fet of features) {
    items.push({
      version: fet.version,
      feature: Feature[fet.feature as keyof typeof Feature],
      description: fet.description,
      enabled: isFeatureEnabled(fet)
    });
  }
  return items;

  function isFeatureEnabled(fet: FeatureToggleConfigItem) {
    if (fet.environmentOverride !== undefined && AppConfig.Environment in fet.environmentOverride) {
      return fet.environmentOverride[AppConfig.Environment];
    }
    return fet.enabled;
  }
}

export const featuresToggleState = atom<FeatureToggleItem[]>({
  key: 'featuresToggles',
  default: loadFeaturesToggleItems()
});

export const workbenchFeatureToggleStateConfigured = atomFamily<boolean, string>({
  key: 'workbenchFeatureTogglesConfigured',
  default: false

});

export const featureTogglesInitialised = atom<boolean>({
  key: 'featureTogglesInitialised',
  default: false,
});