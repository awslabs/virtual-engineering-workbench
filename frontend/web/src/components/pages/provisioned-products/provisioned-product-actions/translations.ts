import { i18n as provisionedProductsI18n } from '../../provisioned-products';

const ONE_ITEM_COUNT = 1;

export const i18n = {
  loginPromptHeader: 'Select your network',
  betaUserPromptContent: 'This is a testing environment and not intended for production data. ' +
    'Please refrain from uploading proprietary intellectual property to the provisioned products.',
  loginPromptCancel: 'Cancel',
  loginPromptConfirm: 'Continue',
  loginIPChoiceDescription: '',
  loginConnectionChoiceDescription: 'Choose the connection option',
  loginConnectionChoiceSSHLabel: 'SSH',
  loginConnectionChoiceSSHDescription: 'You will be presented with an SSH key to log in.',
  loginConnectionChoiceRDPLabel: 'RDP',
  loginConnectionChoiceDCVFileLabel: 'NICE DCV File',
  loginConnectionChoiceDCVBrowserLabel: 'NICE DCV Browser',
  loginConnectionChoiceRDPDescription: 'Download a RDP connection file.',
  loginConnectionChoiceDCVFileDescription: 'Download a NICE DCV connection file. ' +
    'Download instructions for DCV clients are ',
  loginConnectionChoiceDCVBrowserDescription: 'Connect to NICE DCV via the browser.',
  loginNetworkLabel: (networks: string[]) =>
    `Login from ${networks.join(', ')} network${pluralize(networks.length)}`,
  loginNetworkDescription: (networks: string[]) =>
    `Choose this, if you are working from ${networks.join(', ')} network${pluralize(networks.length)}.`,
  loginDomainChoiceDescription: 'Choose the domain',
  loginSelectedDomainDescription: (domain: string) => `Use ${domain} domain`,
  loginMultipleMonitorChoiceDescription:
    'Check this box if you want your provisioned product to be displayed on all of your monitors.',
  sshFetchErrorHeader: 'Unable to fetch the SSH key',
  dcvFetchErrorHeader: 'Unable to fetch the session credentials',
  authorizeUserIpError: 'Unable to authorize user IP address',
  loginUserCredentialRevealError: 'Error fetching user credentials',
  loginUserCredentialsShowButton: 'Show login credentials',
  loginUserCredentialsUsername: 'Username',
  loginUserCredentialsPassword: 'Password',
  loginError: 'Error while logging in',
  connectDirectly: 'Connect directly',
  connectDirectlyDescription: 'Check this to connect directly to the IP address of the provisioned product.',
  errorNoConnectionMethodSelected: 'No connection option selected',
  errorNoUserData: 'Unable to load user data.',
};

function pluralize(counter: number) {
  return counter <= ONE_ITEM_COUNT ? '' : 's';
}

export const i18nWorkbenchLogin = {
  ...i18n,
  betaUserPromptContent: 'This is a testing environment and not intended for production data. ' +
    'Please refrain from uploading proprietary intellectual property to the workbenches.',
  loginMultipleMonitorChoiceDescription:
    'Check this box if you want your workbench to be displayed on all of your monitors.'
};

export const i18nVirtualTargetLogin = {
  ...i18n,
  ...provisionedProductsI18n,
  betaUserPromptContent: 'This is a testing environment and not intended for production data. ' +
    'Please refrain from uploading proprietary intellectual property to the workbenches.',
  loginMultipleMonitorChoiceDescription:
    'Check this box if you want your workbench to be displayed on all of your monitors.',
  confirmRemoveLabel: 'Remove provisioned products',
  failedToLoadProvisionedProduct: 'Failed to load provisioned product details.',
  deprovisionModalCancel: 'Cancel',
  deprovisionModalOK: 'Confirm'
};
