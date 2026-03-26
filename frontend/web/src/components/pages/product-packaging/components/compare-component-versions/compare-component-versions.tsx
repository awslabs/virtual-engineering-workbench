/* eslint-disable complexity */
import {
  Box,
  Button,
  ColumnLayout,
  Container,
  FormField,
  Header,
  HelpPanel,
  Icon,
  Select,
  SpaceBetween,
  Spinner,
  StatusIndicator,
  Table,
} from '@cloudscape-design/components';
import {
  useNavigationPaths,
} from '../../../../layout/navigation/navigation-paths.logic';
import {
  RouteNames,
} from '../../../../layout/navigation/navigation.static';
import {
  WorkbenchAppLayout,
} from '../../../../layout/workbench-app-layout/workbench-app-layout';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../../state';
import { useParams, useLocation } from 'react-router-dom';
import {
  packagingAPI,
} from '../../../../../services/API/packaging-api';
import { i18n } from './compare-component-versions.translations';
import {
  useCompareComponentVersions,
} from './compare-component-versions.logic';
import {
  YamlDiffViewer,
} from '../../../shared/yaml-diff-viewer';
import { rcompare } from 'semver';

const SORT_HIGHER = 1;
const SORT_LOWER = -1;
const MIN_VERSIONS_FOR_COMPARE = 2;
const ARROW_PADDING_TOP = 24;

const FIRST_CHAR = 0;
const AFTER_FIRST = 1;

const toTitleCase = (s: string) =>
  s.charAt(FIRST_CHAR).toUpperCase()
  + s.slice(AFTER_FIRST).toLowerCase();

type DepRow = {
  componentId: string,
  componentName: string,
  versionA: string,
  versionB: string,
  status: string,
};

export const CompareComponentVersions = () => {
  const { getPathFor, navigateTo } = useNavigationPaths();
  const selectedProject = useRecoilValue(selectedProjectState);
  const { componentId } = useParams();
  const { state } = useLocation();

  if (!componentId) {
    navigateTo(RouteNames.Components);
    return <></>;
  }

  const {
    versions,
    versionsLoading,
    versionIdA,
    selectVersionA,
    versionIdB,
    selectVersionB,
    yamlA,
    yamlB,
    dependenciesA,
    dependenciesB,
    loadingA,
    loadingB,
    isReady,
  } = useCompareComponentVersions({
    serviceApi: packagingAPI,
    projectId: selectedProject.projectId,
    componentId,
    initialVersionIdA: state?.versionIdA || null,
  });

  const sortedVersions = [...versions].sort((a, b) => {
    try {
      return rcompare(
        a.componentVersionName,
        b.componentVersionName,
      );
    } catch {
      return a.componentVersionName
        < b.componentVersionName
        ? SORT_HIGHER : SORT_LOWER;
    }
  });

  const versionOptions = sortedVersions.map(v => ({
    label: v.componentVersionName,
    value: v.componentVersionId,
    description: v.componentVersionDescription,
    tags: [toTitleCase(v.status)],
  }));

  const notEnoughVersions =
    versions.length < MIN_VERSIONS_FOR_COMPARE;
  const versionOptionsB =
    versionOptions.filter(o => o.value !== versionIdA);

  return <WorkbenchAppLayout
    breadcrumbItems={[
      {
        path: i18n.breadcrumbLevel1,
        href: getPathFor(RouteNames.Components),
      },
      {
        path: i18n.breadcrumbLevel2,
        href: getPathFor(RouteNames.ViewComponent, {
          ':componentId': componentId,
        }),
      },
      { path: i18n.breadcrumbLevel3, href: '#' },
    ]}
    content={renderContent()}
    contentType="default"
    tools={
      <HelpPanel header={<h2>{i18n.pageHeader}</h2>}>
        <p>{i18n.selectBothVersions}</p>
      </HelpPanel>
    }
  />;

  function renderContent() {
    if (versionsLoading) {
      return <Spinner size="large" />;
    }

    return <SpaceBetween direction="vertical" size="l">
      <Container header={<Header actions={
        <Button
          variant="normal"
          disabled={!versionIdA}
          onClick={() => { selectVersionA(null); }}
          data-test="clear-selection"
        >
          {i18n.clearButton}
        </Button>
      }>{i18n.pageHeader}</Header>}>
        <ColumnLayout columns={3}>
          <FormField
            label={i18n.selectVersionA}
            description={i18n.selectVersionADescription}
          >
            <Select
              selectedOption={
                versionIdA
                  ? versionOptions.find(
                    o => o.value === versionIdA
                  ) || null
                  : null
              }
              onChange={({ detail }) =>
                selectVersionA(
                  detail.selectedOption.value || null
                )
              }
              options={versionOptions}
              placeholder={i18n.selectVersionPlaceholder}
              filteringType="auto"
              disabled={notEnoughVersions}
              triggerVariant="option"
              data-test="select-version-a"
            />
          </FormField>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            paddingTop: ARROW_PADDING_TOP,
          }}>
            <Icon
              name="angle-right-double"
              size="big"
            />
          </div>
          <FormField
            label={i18n.selectVersionB}
            description={i18n.selectVersionBDescription}
          >
            <Select
              selectedOption={
                versionIdB
                  ? versionOptionsB.find(
                    o => o.value === versionIdB
                  ) || null
                  : null
              }
              onChange={({ detail }) =>
                selectVersionB(
                  detail.selectedOption.value || null
                )
              }
              options={versionOptionsB}
              placeholder={i18n.selectVersionPlaceholder}
              filteringType="auto"
              disabled={
                notEnoughVersions || !versionIdA
              }
              triggerVariant="option"
              data-test="select-version-b"
            />
          </FormField>
        </ColumnLayout>
      </Container>
      {(loadingA || loadingB) &&
        <Spinner size="large" />}
      {isReady && renderDiff()}
    </SpaceBetween>;
  }

  function renderDiff() {
    return <SpaceBetween direction="vertical" size="l">
      <Container header={
        <Header>{i18n.yamlDiffHeader}</Header>
      }>
        <YamlDiffViewer
          originalYaml={yamlA}
          modifiedYaml={yamlB}
        />
      </Container>
      {renderDependenciesDiff()}
    </SpaceBetween>;
  }

  function renderDependenciesDiff() {
    const depsMapA = new Map(
      dependenciesA.map(d => [d.componentId, d])
    );
    const depsMapB = new Map(
      dependenciesB.map(d => [d.componentId, d])
    );
    const allIds = new Set(
      [...depsMapA.keys(), ...depsMapB.keys()]
    );

    const rows: DepRow[] = [];

    allIds.forEach(id => {
      const a = depsMapA.get(id);
      const b = depsMapB.get(id);
      const verName = (
        d: typeof a
      ) => d?.componentVersionName || '-';

      if (a && !b) {
        rows.push({
          componentId: id,
          componentName: a.componentName || id,
          versionA: verName(a),
          versionB: '-',
          status: 'changed',
        });
      } else if (!a && b) {
        rows.push({
          componentId: id,
          componentName: b.componentName || id,
          versionA: '-',
          versionB: verName(b),
          status: 'changed',
        });
      } else if (a && b) {
        const changed =
          a.componentVersionId !== b.componentVersionId;
        rows.push({
          componentId: id,
          componentName: a.componentName || id,
          versionA: verName(a),
          versionB: verName(b),
          status: changed ? 'changed' : 'unchanged',
        });
      }
    });

    return <Container header={
      <Header>{i18n.dependenciesDiffHeader}</Header>
    }>
      <Table
        variant="embedded"
        items={rows}
        columnDefinitions={[
          {
            id: 'component',
            header: i18n.dependencyColumnComponent,
            cell: r => r.componentName,
          },
          {
            id: 'versionA',
            header: i18n.selectVersionA,
            cell: r => r.versionA,
          },
          {
            id: 'versionB',
            header: i18n.selectVersionB,
            cell: r => r.versionB,
          },
          {
            id: 'status',
            header: 'Status',
            cell: r => r.status === 'changed'
              ? <StatusIndicator type="warning">
                {i18n.dependencyChanged}
              </StatusIndicator>
              : <StatusIndicator type="info">
                {i18n.dependencyUnchanged}
              </StatusIndicator>,
          },
        ]}
        empty={
          <Box textAlign="center" color="inherit">
            {i18n.noDependencies}
          </Box>
        }
        data-test="dependencies-diff-table"
      />
    </Container>;
  }
};
