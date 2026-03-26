import { SelectProps } from '@cloudscape-design/components';

export const PACKAGING_OS_TRANSLATIONS: { [key: string]: string } = {
  ubuntu24: 'Linux Ubuntu 24.04',
  WindowsServer2025: 'Windows Server 2025',
};

export const PACKAGING_OS_VERSIONS: { [key: string]: SelectProps.Option[] } = {
  Windows: [{
    value: 'Microsoft Windows Server 2025',
    description: PACKAGING_OS_TRANSLATIONS.WindowsServer2025
  }],
  Linux: [{
    value: 'Ubuntu 24',
    description: PACKAGING_OS_TRANSLATIONS.ubuntu24
  }],
};

export const PACKAGING_SUPPORTED_ARCHITECTURES: { [key: string]: SelectProps.Option[] } = {
  Windows: [{
    value: 'amd64',
    description: 'amd64'
  }],
  Linux: [{
    value: 'amd64',
    description: 'amd64'
  }, {
    value: 'arm64',
    description: 'arm64'
  }],
};