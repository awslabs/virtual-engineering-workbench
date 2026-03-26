const userTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

/* eslint @stylistic/max-len: "off" */
export const i18nWorkbenchSteps = {
  settingsContainerHeader: 'Workbench settings',
  dropdownVersionNotSelected: 'Choose a version',
  formFieldRegionHeader: 'Region',
  formFieldRegionDescription:
    'Location where the workbench will be hosted. Default option based on user profile preferences.',
  formFieldRegionDescriptionLatencies:
    'Location where the workbench will be hosted. The recommended option, offering the best performance, will be automatically selected during each latency check. You may override this selection if needed.',
  formFieldRegionCheckingLatency: 'Checking latency',
  formFieldRegionLatencyUnreachable: 'Latency: unreachable',
  formFieldRegionLatency: (latency?: number) => `Latency: ${latency} ms`,
  formFieldRegionRecommended: 'Recommended',
  formFieldStageHeader: 'Stage',
  formFieldStageDescription:
    'Stage at which the workbench is available from DEV, QA and PROD.',
  formFieldVersionHeader: 'Version',
  formFieldVersionDescription:
    "Available versions of the product. Only the product versions fulfilling your region and stage requirements are shown.", // eslint-disable-line
  formFieldVersionError: 'Please select an available workbench version.',
  productVersionsLoading: 'Loading versions...',
  recommendedVersionTag: 'Recommended',
  latencyCheckWhichRegion: 'Which region should I choose?',
  latencyCheckAgain: 'Check Again',
  latencyCheckUnableToTest: 'Unable to test',
  latencyCheckResult: (regionName: string) =>
    `Based on the round-trip network performance check, ${regionName} 
 region has best performance from your location.`,
  latencyCheckMS: (latency: number) => `${latency} ms`,
  latencyCheckUnreachable: 'Unreachable',
  latencyCheckNetwork: (networks: string) => ` using ${networks} network IP`,
  mappingInfo: (jobName: string, platformType: string, version: string, path: string) =>
    `Configured with ${jobName} ${platformType} platform version ${version} (path: ${path}).`,
  headerOsVersion: 'Operating system',
  headerVersionDetails: 'Version details',

  componentVersionTypeAnyOption: 'Any type',
  emptyInstalledTools: 'List of tools unavailable',
  emptyInstalledToolsSubTitle: 'List of tools unavailable',
  findInstalledToolsPlaceholder: 'Find installed tools',
  selectComponentVersionTypePlaceholder: 'Any type',
  selectSoftwareVendorPlaceholder: 'Any vendor',
  softwareVendorAnyOption: 'Any vendor',
  tableHeaderComponentName: 'Tool name',
  tableHeaderSoftwareVersion: 'Version',
  tableHeaderComponentVersionType: 'Type',
  tableHeaderSoftwareVendor: 'Vendor',
  tableHeaderNotes: 'Notes',
  tableHeaderLicenseDashboard: 'License info',
  tableFilterNoResultActionText: 'Clear filter',
  tableFilterNoResultSubtitle: 'No installed tools were found using your search criteria.',
  tableFilterNoResultTitle: 'List of tools unavailable',
  tableHeader: 'Installed tools',

  parametersContainerHeader: 'Workbench parameters',
  productAdvancedDetails: `Maintenance window [Time zone: ${userTimeZone}]`,
  productAdvancedDescription:
    'Period of time during which patches and security updates will be applied.',
  parameterNew: 'New',
  parameterInfo: 'Info',

  experimentalWarning:
    `The Experimental Mode feature is available only in the QA stage.
    To set it up, select the QA stage and then designate the Experimental Mode parameter as 'Yes' 
    in the next step. Learn more about the Experimental Mode feature `,
  experimentalWarningLinkText: 'here',
  experimentalWarningLinkUrl: '',
  experimentalHeading: 'Experimental Mode',
  experimentalLabel: 'Experimental',
  experimentalDescription:
    'Define whether this instance will be used for experimental purposes or not.',
  experimentalOptionYesValue: 'True',
  experimentalOptionYesLabel:
    'Yes, permit experimentation with tool versions, new installations, or OS configuration changes.',
  experimentalOptionNoValue: 'False',
  experimentalOptionNoLabel: 'No, use the existing predefined setup.',
  experimentalDisclaimer:
    `Experimental Mode is expressly designed for experimentation and must never be used for production 
    purposes, therefore all git push and artifact upload requests are forbidden.`,

  stepOne: 'Step 1: Configure settings',
  stepTwo: 'Step 2: Set parameters',
  region: 'Region',
  stage: 'Stage',
  version: 'Version',
  mainSoftware: 'Main software',
  instanceType: 'Instance type',
  editButton: 'Edit',

  estimatedCostsLabel: 'Estimated costs',
  estimatedCostsDescription: 'The estimated costs of running this workbench over a selected period of time.',
  hourly: 'Hourly',
  daily: 'Daily',
  weekly: 'Weekly',
  costInfo: 'The estimated cost of running this workbench is: '
};