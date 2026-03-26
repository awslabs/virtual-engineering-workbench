import { i18n, VERSION_STATUS_MAP, VERSION_STATUS_COLOR_MAP } from './view-product.translations.ts';
import {
  Badge,
  Header,
  SpaceBetween,
  StatusIndicator,
  Table,
  Button,
  TextFilter,
  Pagination,
  TableProps,
  ButtonDropdown,
  ButtonDropdownProps,
  Link,
} from '@cloudscape-design/components';
import React from 'react';
import { VersionSummary } from '../../../../services/API/proserve-wb-publishing-api';
import { RoleBasedFeature } from '../../../../state';
import { EmptyGridNotification, NoMatchTableNotification, UserDate } from '../../shared';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { compare } from '../../../../utils/semantic-versioning.ts';
import { useRoleAccessToggle } from '../../../../hooks/role-access-toggle';
import { RecommendedVersionIndicator } from './recommended-version-indicator.tsx';
import { RestoredVersionIndicator } from './restored-version-indicator.tsx';

import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../layout/navigation/navigation.static';

/* eslint-disable @stylistic/max-len */
/* eslint-disable complexity */

const PAGE_SIZE = 20;
const PAGE_INDEX = 1;
const ZERO_INDEX = 0;
const MIN_VERSIONS_FOR_COMPARE = 2;


const StageIndicator = ({ stages }: { stages?: string[] }) => {
  const availableStages = ['DEV', 'QA', 'PROD'];
  return (
    <SpaceBetween direction='horizontal' size='xxxs'>
      {stages?.map((stage, index) => <Badge color='blue' key={index}>{stage}</Badge>)}
      {availableStages
        .filter(stage => !stages?.includes(stage))
        .map((stage, index) => <Badge color='grey' key={index}>{stage}</Badge>)}
    </SpaceBetween>
  );
};



const LESS_THAN = -1;
const GREATER_THAN = 1;
const EQUAL = 0;

function compareAdditionalInfo(
  a: VersionSummary,
  b: VersionSummary) {
  const infoA = a.recommendedVersion ? 'recommended' : a.restoredFromVersionName !== undefined ? 'restored' : '';
  const infoB = b.recommendedVersion ? 'recommended' : b.restoredFromVersionName !== undefined ? 'restored' : '';
  return infoA < infoB ? LESS_THAN : infoA > infoB ? GREATER_THAN : EQUAL;
}

type ProductVersionsProps = {
  productId?: string,
  versions?: VersionSummary[],
  selectedVersion?: VersionSummary,
  setSelectedVersion?: (version: VersionSummary | undefined) => void,
  isLoading: boolean,
  loadVersions: () => void,
  viewVersionDetails: (versionId: string) => void,
  updateVersionDetails: () => void,
  promoteVersion: () => void,
  emptyVersionResolveAction: () => void,
  retireVersion: () => void,
  isProductArchived: () => boolean,
  restoreVersion: () => void,
  setRecommendedVersion: () => void,
};

export const ProductVersions = ({
  productId,
  versions = [],
  isLoading,
  setSelectedVersion,
  loadVersions,
  viewVersionDetails,
  updateVersionDetails,
  promoteVersion,
  emptyVersionResolveAction,
  retireVersion,
  isProductArchived,
  restoreVersion,
  setRecommendedVersion,
}: ProductVersionsProps) => {

  const { navigateTo } = useNavigationPaths();

  const columnDefinitions: TableProps.ColumnDefinition<VersionSummary>[] = [
    {
      id: 'version',
      header: i18n.tableHeaderVersion,
      cell: (e) => {
        return <div>
          <Link onFollow={() => { viewVersionDetails(e.versionId); }}>{e.name}</Link>
        </div>;
      },
      sortingComparator: (a, b) => compare(a.name, b.name)
    },
    {
      id: 'description',
      header: i18n.tableHeaderProductVersionDescription,
      cell: e => e.description,
    },
    {
      id: 'stage',
      header: i18n.tableHeaderStage,
      cell: e => <StageIndicator stages={e.stages} />,
    },
    {
      id: 'status',
      header: i18n.tableHeaderStatus,
      cell: e =>
        <SpaceBetween size={'xs'} direction='horizontal'>
          <StatusIndicator
            type={VERSION_STATUS_COLOR_MAP[e.status]}
          >
            {VERSION_STATUS_MAP[e.status]}
          </StatusIndicator>
        </SpaceBetween>,
      sortingField: 'status',
    },
    {
      id: 'lastUpdate',
      header: i18n.tableHeaderLastUpdate,
      cell: e => <UserDate date={e.lastUpdate} />,
      sortingField: 'lastUpdate'
    },
    {
      id: 'lastUpdatedBy',
      header: i18n.tableHeaderLastContributor,
      cell: e => e.lastUpdatedBy,
      sortingField: 'lastUpdatedBy'
    },
    {
      id: 'recommendedVersion',
      header: i18n.tableHeaderAdditionalInfo,
      cell: e => <>
        <RecommendedVersionIndicator isRecommendedVersion={e.recommendedVersion} />
        <RestoredVersionIndicator productVersion={e} />
      </>,
      sortingComparator: compareAdditionalInfo
    },
  ];

  const { items, actions, filterProps, collectionProps, paginationProps } = useCollection(
    versions,
    {
      filtering: {
        empty: <NoMatchTableNotification
          title={i18n.tableFilterNoResultTitle}
          buttonAction={() => actions.setFiltering('')}
          buttonText={i18n.tableFilterNoResultActionText}
          subtitle={i18n.tableFilterNoResultSubtitle}
        />,
        noMatch: <NoMatchTableNotification
          title={i18n.tableFilterNoResultTitle}
          buttonAction={() => actions.setFiltering('')}
          buttonText={i18n.tableFilterNoResultActionText}
          subtitle={i18n.tableFilterNoResultSubtitle} />,
      },
      selection: {},
      sorting: { defaultState: { sortingColumn: columnDefinitions[0] } },
      pagination: { defaultPage: PAGE_INDEX, pageSize: PAGE_SIZE }
    }
  );

  React.useEffect(() => {
    setSelectedVersion?.(collectionProps.selectedItems && collectionProps.selectedItems[0]);
  }, [collectionProps, setSelectedVersion]);

  const isFeatureAccessible = useRoleAccessToggle();

  function handleDropdownClick({ detail }: CustomEvent<ButtonDropdownProps.ItemClickDetails>) {
    if (detail.id === 'update') {
      updateVersionDetails();
    }
    if (detail.id === 'promote') {
      promoteVersion();
    }
    if (detail.id === 'retire') {
      retireVersion();
    }
    if (detail.id === 'restore') {
      restoreVersion();
    }
    if (detail.id === 'set-recommended') {
      setRecommendedVersion();
    }
  }

  let labelId = '';

  const restoreOrRetire = () => {
    if (collectionProps.selectedItems && collectionProps.selectedItems[0] && collectionProps.selectedItems[0].status !== undefined) {
      if (collectionProps.selectedItems[0].status === 'RETIRED') {
        labelId = 'restore';
        return i18n.productVersionRestore;
      }
      labelId = 'retire';
      return i18n.productVersionRetire;
    }
    return '';
  };

  function isItemSelected(predicate?: (vs: VersionSummary) => boolean) {
    return collectionProps.selectedItems !== undefined &&
      collectionProps.selectedItems?.length >= ZERO_INDEX &&
      collectionProps.selectedItems[0] !== undefined &&
      (!predicate || predicate(collectionProps.selectedItems[0]));
  }

  function preventAnyAction() {
    return !isItemSelected() || isItemSelected(vs => vs.status === 'PROCESSING');
  }

  function preventPromote() {
    const canManageProdProducts = isFeatureAccessible(RoleBasedFeature.ManageProdProducts);
    return !isItemSelected() ||
      isItemSelected(vs => vs.status !== 'CREATED' ||
        vs.stages.includes('PROD') ||
        vs.stages.includes('QA') &&
        (!canManageProdProducts || vs.versionType === 'RESTORED')
      );
  }

  function preventSetRecommended() {
    return !isItemSelected() ||
      isItemSelected(vs => vs.status !== 'CREATED' || !vs.stages.includes('PROD') || vs.recommendedVersion);
  }

  function preventUpdate() {
    return !isItemSelected() || isItemSelected(vs => vs.status !== 'CREATED' &&
      vs.status !== 'FAILED' ||
      vs.stages.includes('PROD') ||
      vs.versionType === 'RESTORED');
  }

  function preventRetireOrRestore() {
    return !isItemSelected || isItemSelected(vs => vs.status !== 'CREATED' && (vs.status !== 'RETIRED' ||
     vs.status === 'RETIRED' && !vs.stages.includes('PROD')));
  }

  return (
    <Table
      data-test="table-product-versions"
      {...collectionProps}
      header={
        <Header
          variant='h2'
          counter={`(${versions.length})`}
          actions={
            <SpaceBetween direction='horizontal' size='m'>
              <Button data-test='button-refresh-table' iconName='refresh' loading={isLoading} onClick={loadVersions} />
              <Button
                data-test='button-compare-versions'
                disabled={versions.length < MIN_VERSIONS_FOR_COMPARE}
                onClick={() => navigateTo(
                  RouteNames.CompareProductVersions,
                  { ':productId': productId },
                  {
                    versionIdA: collectionProps
                      .selectedItems?.[ZERO_INDEX]?.versionId,
                  },
                )}
              >
                {i18n.buttonCompareVersions}
              </Button>
              <Button
                data-test='button-view-version'
                disabled={collectionProps.selectedItems?.length === ZERO_INDEX}
                onClick={() => viewVersionDetails(collectionProps.selectedItems ?
                  collectionProps.selectedItems[0].versionId : '')}>
                {i18n.productVersionViewDetails}
              </Button>
              {!isProductArchived() &&
                <ButtonDropdown
                  data-test="actions-dropdown"
                  onItemClick={handleDropdownClick}
                  disabled={preventAnyAction()}
                  items={[
                    {
                      text: i18n.productVersionPromote, id: 'promote',
                      disabled: preventPromote()
                    },
                    {
                      text: i18n.productVersionSetAsRecommended, id: 'set-recommended',
                      disabled: preventSetRecommended()
                    },
                    {
                      text: i18n.productVersionUpdateDetails, id: 'update',
                      disabled: preventUpdate()
                    },
                    {
                      text: restoreOrRetire(), id: labelId,
                      disabled: preventRetireOrRestore()
                    },
                  ]}
                >
                  {i18n.productVersionActions}
                </ButtonDropdown>}
            </SpaceBetween>
          }
        >
          {i18n.productVersionsHeader}
        </Header>
      }
      visibleColumns={[
        'version',
        'description',
        'stage',
        'recommendedVersion',
        'status',
        'lastUpdate',
        'lastUpdatedBy'
      ]}
      loading={isLoading}
      items={items}
      selectionType='single'
      empty={
        <EmptyGridNotification title={i18n.emptyVersions}
          subTitle={i18n.emptyVersionsSubTitle}
          actionButtonText={i18n.emptyVersionsResolve}
          actionButtonOnClick={emptyVersionResolveAction}
        />
      }
      filter={
        <TextFilter
          {...filterProps}
          filteringPlaceholder={i18n.findProductVersionsPlaceholder}
          filteringAriaLabel={i18n.findProductVersionsPlaceholder}
        />
      }
      pagination={<Pagination
        {...paginationProps}
      />}
      columnDefinitions={columnDefinitions}
    />
  );
};
