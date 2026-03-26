/* eslint-disable complexity */
import {
  Badge,
  Box,
  ColumnLayout,
  Container,
  FormField,
  Header,
  HelpPanel,
  Icon,
  Popover,
  Select,
  SpaceBetween,
  Spinner,
  StatusIndicator,
  Table,
} from '@cloudscape-design/components';
import {
  useNavigationPaths,
} from '../../../layout/navigation/navigation-paths.logic';
import {
  RouteNames,
} from '../../../layout/navigation/navigation.static';
import {
  WorkbenchAppLayout,
} from '../../../layout/workbench-app-layout/workbench-app-layout';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../state';
import { useParams, useLocation } from 'react-router-dom';
import { publishingAPI } from '../../../../services/API/publishing-api';
import { i18n } from './compare-product-versions.translations';
import {
  useCompareProductVersions,
} from './compare-product-versions.logic';
import { YamlDiffViewer } from '../../shared/yaml-diff-viewer';
import { CopyText } from '../../shared';
import { rcompare } from 'semver';
import { REGION_NAMES } from '../../../user-preferences';

const SORT_HIGHER = 1;
const SORT_LOWER = -1;
const MIN_VERSIONS_FOR_COMPARE = 2;
const ARROW_PADDING_TOP = 24;

type RegionKey = keyof typeof REGION_NAMES;

type DistRow = {
  awsAccountId: string,
  stage: string,
  region: string,
  amiA: string,
  amiB: string,
  status: 'removed' | 'added' | 'changed' | 'unchanged',
};

const FIRST_CHAR = 0;
const AFTER_FIRST = 1;

const toTitleCase = (s: string) =>
  s.charAt(FIRST_CHAR).toUpperCase()
  + s.slice(AFTER_FIRST).toLowerCase();

export const CompareProductVersions = () => {
  const { getPathFor, navigateTo } = useNavigationPaths();
  const selectedProject = useRecoilValue(selectedProjectState);
  const { productId } = useParams();
  const { state } = useLocation();

  if (!productId) {
    navigateTo(RouteNames.Products);
    return <></>;
  }

  const {
    versions,
    productLoading,
    versionIdA,
    selectVersionA,
    versionIdB,
    selectVersionB,
    templateA,
    templateB,
    distributionsA,
    distributionsB,
    loadingA,
    loadingB,
    isReady,
  } = useCompareProductVersions({
    serviceApi: publishingAPI,
    projectId: selectedProject.projectId,
    productId,
    initialVersionIdA: state?.versionIdA || null,
  });

  const sortedVersions = [...versions].sort((a, b) => {
    try { return rcompare(a.name, b.name); } catch {
      return a.name < b.name ? SORT_HIGHER : SORT_LOWER;
    }
  });

  const versionOptions = sortedVersions.map(v => ({
    label: v.name,
    value: v.versionId,
    description: v.description || '',
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
        href: getPathFor(RouteNames.Products),
      },
      {
        path: i18n.breadcrumbLevel2,
        href: getPathFor(
          RouteNames.Product, { ':id': productId }
        ),
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
    if (productLoading) {
      return <Spinner size="large" />;
    }

    return <SpaceBetween direction="vertical" size="l">
      <Container header={
        <Header>{i18n.pageHeader}</Header>
      }>
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
              disabled={notEnoughVersions || !versionIdA}
              triggerVariant="option"
              data-test="select-version-b"
            />
          </FormField>
        </ColumnLayout>
      </Container>
      {(loadingA || loadingB) && <Spinner size="large" />}
      {isReady && <SpaceBetween direction="vertical" size="l">
        <Container header={
          <Header>{i18n.templateDiffHeader}</Header>
        }>
          <YamlDiffViewer
            originalYaml={templateA}
            modifiedYaml={templateB}
          />
        </Container>
        {renderDistributionsDiff()}
      </SpaceBetween>}
    </SpaceBetween>;
  }

  function renderDistributionsDiff() {
    const distKey = (d: {
      awsAccountId: string,
      stage: string,
      region: string,
    }) => `${d.awsAccountId}#${d.stage}#${d.region}`;

    const mapA = new Map(
      distributionsA.map(d => [distKey(d), d])
    );
    const mapB = new Map(
      distributionsB.map(d => [distKey(d), d])
    );
    const allKeys = new Set(
      [...mapA.keys(), ...mapB.keys()]
    );

    const rows: DistRow[] = [];

    allKeys.forEach(key => {
      const a = mapA.get(key);
      const b = mapB.get(key);
      const getAmi = (d: typeof a) =>
        d?.copiedAmiId || d?.originalAmiId || '-';

      if (a && !b) {
        rows.push({
          awsAccountId: a.awsAccountId,
          stage: a.stage,
          region: a.region,
          amiA: getAmi(a),
          amiB: '-',
          status: 'removed',
        });
      } else if (!a && b) {
        rows.push({
          awsAccountId: b.awsAccountId,
          stage: b.stage,
          region: b.region,
          amiA: '-',
          amiB: getAmi(b),
          status: 'added',
        });
      } else if (a && b) {
        const amiA = getAmi(a);
        const amiB = getAmi(b);
        rows.push({
          awsAccountId: a.awsAccountId,
          stage: a.stage,
          region: a.region,
          amiA,
          amiB,
          status: amiA !== amiB
            ? 'changed' : 'unchanged',
        });
      }
    });

    return <Container header={
      <Header>{i18n.amiDiffHeader}</Header>
    }>
      <Table
        variant="embedded"
        items={rows}
        columnDefinitions={
          getDistributionColumns()
        }
        empty={
          <Box textAlign="center" color="inherit">
            {i18n.amiNoDistributions}
          </Box>
        }
        data-test="distributions-diff-table"
      />
    </Container>;
  }
};

function getDistributionColumns() {
  return [
    {
      id: 'stage',
      header: i18n.amiColumnStage,
      cell: (r: DistRow) =>
        <Badge color="blue">{r.stage}</Badge>,
    },
    {
      id: 'region',
      header: i18n.amiColumnRegion,
      cell: (r: DistRow) => <Popover
        dismissButton={false}
        position="top"
        size="small"
        triggerType="text"
        content={
          <StatusIndicator type="info">
            {r.region}
          </StatusIndicator>
        }
      >
        {REGION_NAMES[r.region as RegionKey]
          || r.region}
      </Popover>,
    },
    {
      id: 'account',
      header: i18n.amiColumnAccount,
      cell: (r: DistRow) => r.awsAccountId,
    },
    {
      id: 'amiA',
      header: i18n.selectVersionA,
      cell: (r: DistRow) => r.amiA !== '-'
        ? <CopyText
          copyButtonLabel="AMI ID"
          copyText={r.amiA}
          successText={i18n.amiCopySuccess}
          errorText={i18n.amiCopyError}
        />
        : '-',
    },
    {
      id: 'amiB',
      header: i18n.selectVersionB,
      cell: (r: DistRow) => r.amiB !== '-'
        ? <CopyText
          copyButtonLabel="AMI ID"
          copyText={r.amiB}
          successText={i18n.amiCopySuccess}
          errorText={i18n.amiCopyError}
        />
        : '-',
    },
    {
      id: 'status',
      header: i18n.amiColumnStatus,
      cell: (r: DistRow) => {
        if (r.status === 'unchanged') {
          return <StatusIndicator type="info">
            {i18n.amiUnchanged}
          </StatusIndicator>;
        }
        return <StatusIndicator type="warning">
          {i18n.amiChanged}
        </StatusIndicator>;
      },
    },
  ];
}
