export interface FeatureToggleConfigItem {
  version: string,
  feature: string,
  description?: string,
  enabled: boolean,
  environmentOverride?: { [key: string]: boolean },
}

const features: FeatureToggleConfigItem[] = [
  {
    version: '1.0.0',
    feature: 'BetaUserInfoText',
    description: `Shows a warning to the new users that this is a test environment. 
It is intended to prevent users from uploading production data to the workbenches.`,
    enabled: true,
    environmentOverride: {
      prod: false,
    }
  },
  {
    version: '1.0.0',
    feature: 'WithdrawFromProgram',
    description: 'Allows users to withdraw from VEW programs.',
    enabled: false,
  },
  {
    version: '1.0.0',
    feature: 'DCVConnectionOptions',
    description: 'Allows users to use NICE DCV to login to a workbench.',
    enabled: false,
  },
  {
    version: '1.0.0',
    feature: 'RDPConnectionOption',
    description: 'Allows users to use Remote Desktop Protocol to login to a workbench.',
    enabled: false
  },
  {
    version: '1.0.0',
    feature: 'ExperimentalWorkbench',
    description: 'Allows users to provision an experimental workbench',
    enabled: false,
    environmentOverride: {
      local: true,
      dev: true,
    }
  },
  {
    version: '1.0.0',
    feature: 'ProductMetadata',
    description: 'Shows installed tools and OS version in provisioning.',
    enabled: false,
    environmentOverride: {
      local: true,
      dev: true,
    }
  },
  {
    version: '1.0.0',
    feature: 'AuthorizeUserIp',
    description: 'Authorize user\'s IP address before login to workbench and virtual target',
    enabled: true,
  },
  {
    version: '1.0.0',
    feature: 'WorkbenchWorkingDirectoryEnabled',
    description: 'Shows if an individual provisioned product has a working directory.',
    enabled: false,
  },
  {
    version: '1.0.0',
    feature: 'ProvisionedProductManualUpdates',
    description: 'Allows platform users to update provisioned product parameters and version',
    enabled: false,
    environmentOverride: {
      local: true,
      dev: true,
    }
  },
];

export default features;
