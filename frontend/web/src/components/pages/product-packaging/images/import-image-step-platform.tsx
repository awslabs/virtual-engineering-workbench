import {
  Container, FormField, Header, Input, RadioGroup,
  SpaceBetween,
} from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n } from './import-image-wizard.translations';

interface Props {
  platform: string,
  setPlatform: (value: string) => void,
  osVersion: string,
  setOsVersion: (value: string) => void,
}

export const ImportImageStepPlatform: FC<Props> = ({
  platform, setPlatform, osVersion, setOsVersion,
}) =>
  <Container header={<Header variant="h2">{i18n.step4Header}</Header>}>
    <SpaceBetween size="m">
      <FormField label={i18n.platformLabel}>
        <RadioGroup
          value={platform}
          onChange={({ detail }) => {
            setPlatform(detail.value);
            setOsVersion('');
          }}
          items={[
            { value: 'Windows', label: 'Windows', description: 'Microsoft Windows Server' },
            { value: 'Linux', label: 'Linux', description: 'Linux-based operating systems' },
          ]}
          data-test="platform-radio"
        />
      </FormField>
      <FormField
        label={i18n.osVersionLabel}
        description="Architecture is detected automatically from the AMI."
      >
        <Input
          value={osVersion}
          onChange={({ detail }) => setOsVersion(detail.value)}
          placeholder={i18n.osVersionPlaceholder}
          data-test="os-version-input"
        />
      </FormField>
    </SpaceBetween>
  </Container>
;
