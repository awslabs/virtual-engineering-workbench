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
import { i18n } from './product-version-wizard.translations';
import { ValueWithLabel } from '../../../shared/value-with-label';
import { YamlCodeEditor, YamlDiffViewer } from '../../../shared';
import { VersionSummary } from '../../../../../services/API/proserve-wb-publishing-api';

export interface ProductVersionWizardStep3Props {
  setActiveStepIndex: (index: number) => void,
  productVersionDescription: string,
  yamlDefinition: string,
  originalYamlDefinition?: string,
  releasedVersions?: VersionSummary[],
  fetchVersionYaml?: (versionId: string) => Promise<string>,
  versionReleaseType: string,
}

const noop = <T,>(e: T) => e;

const YamlContent: FC<{
  isDiffBaseLoading: boolean,
  showDiff: boolean,
  diffBaseYaml: string | undefined,
  yamlDefinition: string,
}> = ({ isDiffBaseLoading, showDiff, diffBaseYaml, yamlDefinition }) => {
  if (isDiffBaseLoading) { return <Spinner />; }
  if (showDiff && diffBaseYaml) {
    return <YamlDiffViewer originalYaml={diffBaseYaml} modifiedYaml={yamlDefinition} cfCompatible />;
  }
  return <YamlCodeEditor
    yamlDefinition={yamlDefinition}
    setYamlDefinition={noop}
    setYamlDefinitionValid={noop}
    disabled={true}
    cfCompatible
  />;
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
      {i18n.step3ShowComparisonToggleLabel}
    </Toggle>
    {showComparison &&
      <FormField label={i18n.step3DiffVersionLabel}>
        <Select
          selectedOption={selectedVersion}
          onChange={({ detail }) => onVersionChange(detail.selectedOption)}
          options={versionOptions}
          placeholder={i18n.step3DiffVersionPlaceholder}
        />
      </FormField>
    }
    {versionsAreSame && <Alert type="info">{i18n.step3DiffVersionsSameAlert}</Alert>}
  </SpaceBetween>
;

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

const useYamlComparison = (
  originalYamlDefinition: string | undefined,
  yamlDefinition: string,
  releasedVersions: VersionSummary[] | undefined,
  fetchVersionYaml: ((versionId: string) => Promise<string>) | undefined,
) => {
  const NO_RELEASES = 0;
  const [diffBaseYaml, setDiffBaseYaml] = useState(originalYamlDefinition);
  const [isDiffBaseLoading, setIsDiffBaseLoading] = useState(false);
  const [showComparison, setShowComparison] = useState(true);

  const versionOptions: SelectProps.Option[] = (releasedVersions || []).map(v => ({
    label: `${v.name} — ${v.description || ''}`,
    value: v.versionId,
  }));

  const defaultSelectedVersion = versionOptions.length > NO_RELEASES
    ? { label: versionOptions[0].label, value: versionOptions[0].value }
    : null;

  const [selectedVersion, setSelectedVersion] = useState<SelectProps.Option | null>(defaultSelectedVersion);

  useEffect(() => {
    if (versionOptions.length > NO_RELEASES) {
      setSelectedVersion({ label: versionOptions[0].label, value: versionOptions[0].value });
    }
  }, [releasedVersions]);

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

export const ProductVersionWizardStep3: FC<ProductVersionWizardStep3Props> = ({
  setActiveStepIndex,
  productVersionDescription,
  yamlDefinition,
  originalYamlDefinition,
  releasedVersions,
  fetchVersionYaml,
  versionReleaseType,
}) => {
  const {
    diffBaseYaml, isDiffBaseLoading, showComparison, setShowComparison,
    versionOptions, selectedVersion, handleVersionChange,
    hasVersionSelector, versionsAreSame, showDiff,
  } = useYamlComparison(originalYamlDefinition, yamlDefinition, releasedVersions, fetchVersionYaml);

  return (
    <SpaceBetween direction="vertical" size="l">
      <SpaceBetween direction="vertical" size="xs">
        <Header
          variant="h3"
          actions={
            // eslint-disable-next-line @typescript-eslint/no-magic-numbers
            <Button onClick={() => setActiveStepIndex(0)}>
              {i18n.step3ButtonEdit}
            </Button>
          }
        >
          {i18n.step3Step1Header}
        </Header>
        <Container
          header={<Header variant="h2">{i18n.step3DetailsHeader}</Header>}
        >
          <ColumnLayout columns={2}>
            <ValueWithLabel
              label={i18n.step1InputDescription}
              data-test="version-description"
            >
              {productVersionDescription}
            </ValueWithLabel>
            <ValueWithLabel
              label={i18n.step1InputReleaseType}
              data-test="version-release-type"
            >
              {versionReleaseType}
            </ValueWithLabel>
          </ColumnLayout>
        </Container>
      </SpaceBetween>
      <SpaceBetween direction="vertical" size="xs">
        <Header
          variant="h3"
          actions={
            // eslint-disable-next-line @typescript-eslint/no-magic-numbers
            <Button onClick={() => setActiveStepIndex(1)}>
              {i18n.step3ButtonEdit}
            </Button>
          }
        >
          {i18n.step3Step2Header}
        </Header>
        <Container
          header={<Header variant="h2">{i18n.step3YamlHeader}</Header>}
        >
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
    </SpaceBetween>
  );
};
