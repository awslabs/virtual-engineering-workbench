/* eslint-disable complexity */
import {
  Button,
  ButtonDropdown,
  ButtonDropdownProps,
  Header,
  Pagination,
  SpaceBetween,
  Table,
  TableProps,
  TextFilter
} from '@cloudscape-design/components';
import { ComponentVersion, Component } from '../../../../../services/API/proserve-wb-packaging-api';
import { i18n } from './view-component.translations';
import { EmptyGridNotification, NoMatchTableNotification, UserDate } from '../../../shared';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { compare } from '../../../../../utils/semantic-versioning';
import { useEffect } from 'react';
import { RetireVersionModal, ReleaseVersionModal } from '../../shared';
import { packagingAPI } from '../../../../../services';
import { useComponentVersions } from './view-component-versions.logic';
import {
  COMPONENT_VERSION_STATES_FOR_FORCE_RELEASE,
  COMPONENT_VERSION_STATES_FOR_RELEASE,
  COMPONENT_VERSION_STATES_FOR_RETIRE,
  COMPONENT_VERSION_STATES_FOR_UPDATE,
  ComponentVersionState,
  ComponentVersionStatus
} from '..';
import { useRoleAccessToggle } from '../../../../../hooks/role-access-toggle';
import { RoleBasedFeature, selectedProjectState } from '../../../../../state';
import { useComponent } from './view-component.logic';
import { useRecoilValue } from 'recoil';

const PAGE_SIZE = 20;
const PAGE_INDEX = 1;
const ZERO_INDEX = 0;
const MIN_COMPONENT_VERSIONS_COMPARE_LENGTH = 2;

export const ViewComponentVersions = ({
  component
}: {
  component?: Component,
}) => {
  const { navigateTo } = useNavigationPaths();
  const isFeatureAccessible = useRoleAccessToggle();
  const selectedProject = useRecoilValue(selectedProjectState);
  const projectId = selectedProject?.projectId;

  // Call hooks before any early returns to comply with rules of hooks
  const { componentResponse } = useComponent({
    componentId: component?.componentId || '',
    serviceApi: packagingAPI,
    projectId: projectId || ''
  });

  const {
    componentVersions,
    loadComponentVersions,
    updateComponentVersion,
    viewComponentVersion,
    releaseComponentVersion,
    componentVersionsLoading,
    setSelectedComponentVersion,
    selectedComponentVersion,
    setIsReleaseComponentVersionModalOpen,
    isReleaseComponentVersionModalOpen,
    isReleaseInProgress,
    setIsRetireComponentVersionModalOpen,
    isRetireComponentVersionModalOpen,
    retireComponentVersion,
    isRetireInProgress,
  } = useComponentVersions({
    serviceApi: packagingAPI,
    componentId: component?.componentId || '',
  });

  if (!projectId) {
    return null;
  }
  if (!component) {
    return null;
  }

  const columnDefinitions: TableProps.ColumnDefinition<ComponentVersion>[] = [
    {
      id: 'componentVersionName',
      header: i18n.tableHeaderComponentVersionName,
      cell: e => e.componentVersionName,
      sortingField: 'componentVersionName',
      sortingComparator: (a, b) => compare(a.componentVersionName, b.componentVersionName),
    },
    {
      id: 'componentVersionDescription',
      header: i18n.tableHeaderComponentVersionDescription,
      cell: e => e.componentVersionDescription,
    },
    {
      id: 'status',
      header: i18n.tableHeaderStatus,
      cell: e => <ComponentVersionStatus status={e.status} />,
      sortingField: 'status',
    },
    {
      id: 'lastUpdateDate',
      header: i18n.tableHeaderComponentVersionUpdateDate,
      cell: e => <UserDate date={e.lastUpdateDate} />,
      sortingField: 'lastUpdateDate'
    },
    {
      id: 'lastUpdatedBy',
      header: i18n.tableHeaderComponentVersionLastContributor,
      cell: e => e.lastUpdatedBy,
      sortingField: 'lastUpdatedBy'
    }
  ];

  const { items, actions, filterProps, collectionProps, paginationProps } =
    useCollection(componentVersions || [], {
      filtering: {
        empty:
          <EmptyGridNotification
            title={i18n.tableEmptyTitle}
            subTitle={i18n.tableEmptySubtitle}
            actionButtonText={i18n.createButtonText}
            actionButtonOnClick={() => {
              navigateTo(RouteNames.CreateComponentVersion, {
                ':componentId': component.componentId,
              }, {
                componentName: component?.componentName,
                componentPlatform: component?.componentPlatform,
              });
            }}
            actionButtonDisabled={componentResponse?.component.status === 'ARCHIVED'}
          />
        ,
        noMatch:
          <NoMatchTableNotification
            title={i18n.tableFilterNoResultTitle}
            buttonAction={() => actions.setFiltering('')}
            buttonText={i18n.tableFilterNoResultActionText}
            subtitle={i18n.tableFilterNoResultSubtitle}
          />
        ,
      },
      selection: {},
      sorting: {
        defaultState: {
          sortingColumn: columnDefinitions[0],
        },
      },
      pagination: { defaultPage: PAGE_INDEX, pageSize: PAGE_SIZE },
    });

  useEffect(() => {
    setSelectedComponentVersion?.(collectionProps.selectedItems && collectionProps.selectedItems[0]);
  }, [collectionProps, setSelectedComponentVersion]);

  function isItemSelected(predicate?: (comp: ComponentVersion) => boolean) {
    return collectionProps.selectedItems !== undefined &&
      collectionProps.selectedItems?.length >= ZERO_INDEX &&
      collectionProps.selectedItems[0] !== undefined &&
      (!predicate || predicate(collectionProps.selectedItems[0]));
  }

  function preventAnyAction() {
    return !isItemSelected() || isItemSelected(comp => comp.status === 'CREATING');
  }

  function handleDropdownClick({ detail }: CustomEvent<ButtonDropdownProps.ItemClickDetails>) {
    if (detail.id === 'update') {
      updateComponentVersion();
    } else if (detail.id === 'release') {
      setIsReleaseComponentVersionModalOpen(true);
    } else if (detail.id === 'retire') {
      setIsRetireComponentVersionModalOpen(true);
    }
  }

  function preventUpdate() {
    const acceptedStatuses = COMPONENT_VERSION_STATES_FOR_UPDATE;
    return !isItemSelected() ||
      isItemSelected(comp => !acceptedStatuses.has(comp.status as ComponentVersionState));
  }

  function preventRelease() {
    let acceptedStatuses = COMPONENT_VERSION_STATES_FOR_RELEASE;
    if (isFeatureAccessible(RoleBasedFeature.ProductPackagingForceReleaseComponent)) {
      acceptedStatuses = COMPONENT_VERSION_STATES_FOR_FORCE_RELEASE;
    }
    return !isItemSelected() ||
      isItemSelected(comp => !acceptedStatuses.has(comp.status as ComponentVersionState));
  }

  function preventRetire() {
    const acceptedStatuses = COMPONENT_VERSION_STATES_FOR_RETIRE;
    return !isItemSelected() ||
      isItemSelected(comp => !acceptedStatuses.has(comp.status as ComponentVersionState));
  }

  return <>
    <Table
      {...collectionProps}
      header={
        <Header
          variant='h2'
          counter={`(${componentVersions?.length})`}
          actions={
            <SpaceBetween direction='horizontal' size='s'>
              <Button
                data-test='button-refresh-table'
                iconName='refresh'
                onClick={loadComponentVersions}
                loading={componentVersionsLoading}
              />
              <Button
                disabled={
                  componentVersions?.length
                    < MIN_COMPONENT_VERSIONS_COMPARE_LENGTH
                }
                onClick={() => navigateTo(
                  RouteNames.CompareComponentVersions,
                  {
                    ':componentId': component?.componentId,
                  },
                  {
                    versionIdA: selectedComponentVersion
                      ?.componentVersionId,
                  },
                )}
                data-test="compare-versions-btn"
              >
                {i18n.compareVersionsButtonText}
              </Button>
              <Button
                disabled={preventAnyAction()}
                onClick={viewComponentVersion}
                data-test="view-component-version"
              >
                {i18n.buttonViewComponentVersion}
              </Button>
              <ButtonDropdown
                data-test="actions-dropdown"
                onItemClick={handleDropdownClick}
                disabled={preventAnyAction()}
                items={[
                  {
                    text: i18n.componentVersionRelease, id: 'release',
                    disabled: preventRelease()
                  },
                  {
                    text: i18n.componentVersionUpdateDetails, id: 'update',
                    disabled: preventUpdate()
                  },
                  {
                    text: i18n.componentVersionRetire, id: 'retire',
                    disabled: preventRetire()
                  }
                ]}
              >
                {i18n.componentVersionActions}
              </ButtonDropdown>
            </SpaceBetween>
          }
        >
          {i18n.tableHeader}
        </Header>
      }
      loading={componentVersionsLoading}
      items={items}
      selectionType="single"
      filter={
        <TextFilter
          {...filterProps}
          filteringPlaceholder={i18n.findVersionsPlaceholder}
          filteringAriaLabel={i18n.findVersionsPlaceholder}
        />
      }
      pagination={<Pagination
        {...paginationProps}
      />}
      columnDefinitions={columnDefinitions}
      data-test="versions"
    />
    <ReleaseVersionModal
      versionName={selectedComponentVersion?.componentVersionName || ''}
      onClose={() => setIsReleaseComponentVersionModalOpen(false)}
      isOpen={isReleaseComponentVersionModalOpen}
      onConfirm={() => releaseComponentVersion()}
      isLoading={componentVersionsLoading || isReleaseInProgress}
    />
    <RetireVersionModal
      versionName={selectedComponentVersion?.componentVersionName || ''}
      onClose={() => setIsRetireComponentVersionModalOpen(false)}
      isOpen={isRetireComponentVersionModalOpen}
      onConfirm={retireComponentVersion}
      isLoading={componentVersionsLoading || isRetireInProgress}
    />
  </>;
};