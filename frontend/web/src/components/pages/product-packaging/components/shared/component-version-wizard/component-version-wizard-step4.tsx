import {
  Alert,
  Button,
  ColumnLayout,
  Container,
  FormField,
  Header,
  Select,
  SelectProps,
  SpaceBetween,
  Spinner,
  Toggle,
} from '@cloudscape-design/components';
import { FC, useEffect, useState } from 'react';
import { i18n } from './component-version-wizard.translations';
import { ValueWithLabel } from '../../../../shared/value-with-label';
import { ComponentVersionEntriesView } from '../../../shared/component-version-entries-view';
import {
  ComponentVersion,
  ComponentVersionEntry
} from '../../../../../../services/API/proserve-wb-packaging-api';
import { YamlCodeEditor, YamlDiffViewer } from '../../../../shared';

export interface ComponentVersionWizardStep4Props {
  setActiveStepIndex: (index: number) => void,
  description: string,
  softwareVendor: string,
  softwareVersion: string,
  licenseDashboard: string,
  notes: string,
  yamlDefinition: string,
  originalYamlDefinition?: string,
  releasedVersions?: ComponentVersion[],
  fetchVersionYaml?: (versionId: string) => Promise<string>,
  versionReleaseType: string,
  componentVersionDependencies: ComponentVersionEntry[],
}

const noop = <T,>(e: T) => e;

const DetailsSection: FC<{
  setActiveStepIndex: (index: number) => void,
  description: string,
  softwareVendor: string,
  softwareVersion: string,
  licenseDashboard: string,
  notes: string,
  versionReleaseType: string,
}> = ({
  setActiveStepIndex,
  description,
  softwareVendor,
  softwareVersion,
  licenseDashboard,
  notes,
  versionReleaseType,
}) => {
  return <SpaceBetween direction="vertical" size="xs">
    <Header
      variant="h3"
      actions={
        // eslint-disable-next-line @typescript-eslint/no-magic-numbers
        <Button onClick={() => setActiveStepIndex(0)}>
          {i18n.step4ButtonEdit}
        </Button>
      }
    >
      {i18n.step4Step1Header}
    </Header>
    <Container header={<Header variant="h2">{i18n.step4DetailsHeader}</Header>}>
      <ColumnLayout columns={2}>
        <ValueWithLabel key="description" label={i18n.step1InputDescription} data-test="version-description">
          {description}
        </ValueWithLabel>
        <ValueWithLabel
          key="release-type"
          label={i18n.step1InputReleaseType}
          data-test="version-release-type"
        >
          {versionReleaseType}
        </ValueWithLabel>
        <ValueWithLabel
          key="software-vendor"
          label={i18n.step1InputSoftwareVendor}
          data-test="version-software-vendor"
        >
          {softwareVendor}
        </ValueWithLabel>
        <ValueWithLabel
          key="software-version"
          label={i18n.step1InputSoftwareVersion}
          data-test="version-software-version"
        >
          {softwareVersion}
        </ValueWithLabel>
        {licenseDashboard
          ? <ValueWithLabel
            key="license-dashboard"
            label={i18n.step1InputLicenseDashboard}
            data-test="version-license-dashboard"
          >
            {licenseDashboard}
          </ValueWithLabel>
          : null
        }
        {notes
          ? <ValueWithLabel key="notes" label={i18n.step1InputNotes} data-test="version-notes">
            {notes}
          </ValueWithLabel>
          : null
        }
      </ColumnLayout>
    </Container>
  </SpaceBetween>;
};

const YamlContent: FC<{
  isDiffBaseLoading: boolean,
  showDiff: boolean,
  diffBaseYaml: string | undefined,
  yamlDefinition: string,
}> = ({ isDiffBaseLoading, showDiff, diffBaseYaml, yamlDefinition }) => {
  if (isDiffBaseLoading) { return <Spinner />; }
  if (showDiff && diffBaseYaml) {
    return <YamlDiffViewer originalYaml={diffBaseYaml} modifiedYaml={yamlDefinition} />;
  }
  return <YamlCodeEditor
    yamlDefinition={yamlDefinition}
    setYamlDefinition={noop}
    setYamlDefinitionValid={noop}
    disabled={true}
  />;
};

const loadVersionYaml = async (
  option: SelectProps.Option,
  fetchVersionYaml: (versionId: string) => Promise<string>,
  setDiffBaseYaml: (yaml: string | undefined) => void,
  setIsDiffBaseLoading: (loading: boolean) => void,
) => {
  if (!option.value) { return; }
  setIsDiffBaseLoading(true);
  try {
    const yaml = await fetchVersionYaml(option.value);
    setDiffBaseYaml(yaml || undefined);
  } catch {
    setDiffBaseYaml(undefined);
  } finally {
    setIsDiffBaseLoading(false);
  }
};

const VersionSelector: FC<{
  showComparison: boolean,
  setShowComparison: (v: boolean) => void,
  selectedVersion: SelectProps.Option | null,
  versionOptions: SelectProps.Option[],
  versionsAreSame: boolean,
  onVersionChange: (option: SelectProps.Option) => void,
}> = ({
  showComparison, setShowComparison, selectedVersion, versionOptions, versionsAreSame, onVersionChange,
}) =>
  <SpaceBetween direction="vertical" size="s">
    <Toggle checked={showComparison} onChange={({ detail }) => setShowComparison(detail.checked)}>
      {i18n.step4ShowComparisonToggleLabel}
    </Toggle>
    {showComparison &&
      <FormField label={i18n.step4DiffVersionLabel}>
        <Select
          selectedOption={selectedVersion}
          onChange={({ detail }) => onVersionChange(detail.selectedOption)}
          options={versionOptions}
          placeholder={i18n.step4DiffVersionPlaceholder}
        />
      </FormField>
    }
    {versionsAreSame && <Alert type="info">{i18n.step4DiffVersionsSameAlert}</Alert>}
  </SpaceBetween>
;

const useYamlComparison = (
  originalYamlDefinition: string | undefined,
  yamlDefinition: string,
  releasedVersions: ComponentVersion[] | undefined,
  fetchVersionYaml: ((versionId: string) => Promise<string>) | undefined,
) => {
  const NO_RELEASES = 0;
  const [diffBaseYaml, setDiffBaseYaml] = useState(originalYamlDefinition);
  const [isDiffBaseLoading, setIsDiffBaseLoading] = useState(false);
  const [showComparison, setShowComparison] = useState(true);

  const versionOptions: SelectProps.Option[] = (releasedVersions || []).map(v => ({
    label: `${v.componentVersionName} — ${v.componentVersionDescription}`,
    value: v.componentVersionId,
  }));

  const defaultSelectedVersion = versionOptions.length > NO_RELEASES
    ? { label: versionOptions[0].label, value: versionOptions[0].value }
    : null;

  const [selectedVersion, setSelectedVersion] = useState<SelectProps.Option | null>(defaultSelectedVersion);

  useEffect(() => { setDiffBaseYaml(originalYamlDefinition); }, [originalYamlDefinition]);

  const handleVersionChange = (option: SelectProps.Option) => {
    setSelectedVersion(option);
    setDiffBaseYaml(undefined);
    if (fetchVersionYaml) {
      loadVersionYaml(option, fetchVersionYaml, setDiffBaseYaml, setIsDiffBaseLoading);
    }
  };

  const hasVersionSelector = releasedVersions && releasedVersions.length > NO_RELEASES && fetchVersionYaml;
  const versionsAreSame =
    showComparison && !!diffBaseYaml && !!selectedVersion && diffBaseYaml === yamlDefinition;
  const showDiff = showComparison && !!diffBaseYaml && !versionsAreSame;

  return {
    diffBaseYaml, isDiffBaseLoading, showComparison, setShowComparison,
    versionOptions, selectedVersion, handleVersionChange,
    hasVersionSelector, versionsAreSame, showDiff,
  };
};

const YamlSection: FC<{
  setActiveStepIndex: (index: number) => void,
  yamlDefinition: string,
  originalYamlDefinition?: string,
  releasedVersions?: ComponentVersion[],
  fetchVersionYaml?: (versionId: string) => Promise<string>,
}> = ({ setActiveStepIndex, yamlDefinition, originalYamlDefinition, releasedVersions, fetchVersionYaml }) => {
  const {
    diffBaseYaml, isDiffBaseLoading, showComparison, setShowComparison,
    versionOptions, selectedVersion, handleVersionChange,
    hasVersionSelector, versionsAreSame, showDiff,
  } = useYamlComparison(originalYamlDefinition, yamlDefinition, releasedVersions, fetchVersionYaml);

  return (
    <SpaceBetween direction="vertical" size="xs">
      <Header
        variant="h3"
        actions={
          // eslint-disable-next-line @typescript-eslint/no-magic-numbers
          <Button onClick={() => setActiveStepIndex(1)}>
            {i18n.step4ButtonEdit}
          </Button>
        }
      >
        {i18n.step4Step2Header}
      </Header>
      <Container header={<Header variant="h2">{i18n.step4YamlHeader}</Header>}>
        <SpaceBetween direction="vertical" size="s">
          {hasVersionSelector && <VersionSelector
            showComparison={showComparison}
            setShowComparison={setShowComparison}
            selectedVersion={selectedVersion}
            versionOptions={versionOptions}
            versionsAreSame={versionsAreSame}
            onVersionChange={handleVersionChange}
          />}
          <FormField stretch>
            <YamlContent
              isDiffBaseLoading={isDiffBaseLoading}
              showDiff={showDiff}
              diffBaseYaml={diffBaseYaml}
              yamlDefinition={yamlDefinition}
            />
          </FormField>
        </SpaceBetween>
      </Container>
    </SpaceBetween>
  );
};

export const ComponentVersionWizardStep4: FC<ComponentVersionWizardStep4Props> = ({
  setActiveStepIndex,
  description,
  softwareVendor,
  softwareVersion,
  licenseDashboard,
  notes,
  yamlDefinition,
  originalYamlDefinition,
  releasedVersions,
  fetchVersionYaml,
  versionReleaseType,
  componentVersionDependencies
}) => {
  return <SpaceBetween direction="vertical" size="l">
    <DetailsSection
      setActiveStepIndex={setActiveStepIndex}
      description={description}
      softwareVendor={softwareVendor}
      softwareVersion={softwareVersion}
      licenseDashboard={licenseDashboard}
      notes={notes}
      versionReleaseType={versionReleaseType}
    />
    <YamlSection
      setActiveStepIndex={setActiveStepIndex}
      yamlDefinition={yamlDefinition}
      originalYamlDefinition={originalYamlDefinition}
      releasedVersions={releasedVersions}
      fetchVersionYaml={fetchVersionYaml}
    />
    <SpaceBetween direction='vertical' size='xs'>
      <Header
        variant='h3'
        actions={
          // eslint-disable-next-line @typescript-eslint/no-magic-numbers
          <Button onClick={() => setActiveStepIndex(2)}>
            {i18n.step4ButtonEdit}
          </Button>
        }
      >
        {i18n.step4Step3Header}
      </Header>
      <ComponentVersionEntriesView
        componentVersionEntries={componentVersionDependencies}
      />
    </SpaceBetween>
  </SpaceBetween>;
};
