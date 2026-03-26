import {
  Button,
  ButtonDropdown,
  ButtonDropdownProps,
  Header,
  Link,
  Pagination,
  SpaceBetween,
  Table,
  TableProps,
  TextFilter
} from '@cloudscape-design/components';
import { RecipeVersion } from '../../../../../services/API/proserve-wb-packaging-api';
import { i18n } from './view-recipe.translations';
import { EmptyGridNotification, NoMatchTableNotification, UserDate } from '../../../shared';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { compare } from '../../../../../utils/semantic-versioning';
import { useEffect } from 'react';
import { packagingAPI } from '../../../../../services';
import { useRecipeVersions } from './view-recipe-versions.logic';
import { RecipeVersionStatus } from '../shared';
import {
  RECIPE_VERSION_STATES_FOR_FORCE_RELEASE,
  RECIPE_VERSION_STATES_FOR_RELEASE,
  RECIPE_VERSION_STATES_FOR_RETIRE,
  RECIPE_VERSION_STATES_FOR_UPDATE,
  RecipeVersionState
} from '../shared/recipe-version.static';
import { RoleBasedFeature, selectedProjectState } from '../../../../../state';
import { useRoleAccessToggle } from '../../../../../hooks/role-access-toggle';
import { ReleaseVersionModal, RetireVersionModal } from '../../shared';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { useRecipe } from './view-recipe.logic';
import { useRecoilValue } from 'recoil';

const PAGE_SIZE = 20;
const PAGE_INDEX = 1;
const ZERO_INDEX = 0;

// eslint-disable-next-line complexity
export const ViewRecipeVersions = ({
  recipeId
}: {
  recipeId: string,
}) => {
  const isFeatureAccessible = useRoleAccessToggle();
  const { navigateTo } = useNavigationPaths();
  const selectedProject = useRecoilValue(selectedProjectState);
  // Ensure projectId is defined
  const projectId = selectedProject?.projectId;

  // Handle case where projectId is undefined
  if (!projectId) {
    return null; // or display an error message to the user
  }

  // Fetch recipe data
  const { recipeResponse } = useRecipe({
    recipeId,
    serviceApi: packagingAPI,
    projectId
  }
  );

  const {
    recipeVersions,
    loadRecipeVersions,
    recipeVersionsLoading,
    setSelectedRecipeVersion,
    selectedRecipeVersion,
    isReleaseRecipeVersionModalOpen,
    setIsReleaseRecipeVersionModalOpen,
    isReleaseInProgress,
    updateRecipeVersion,
    releaseRecipeVersion,
    viewRecipeVersion,
    isRetireRecipeVersionModalOpen,
    setIsRetireRecipeVersionModalOpen,
    retireRecipeVersion,
    isRetireInProgress,
  } = useRecipeVersions({
    serviceApi: packagingAPI,
    recipeId,
  });

  const columnDefinitions: TableProps.ColumnDefinition<RecipeVersion>[] = [
    {
      id: 'recipeVersionName',
      header: i18n.tableHeaderRecipeVersionName,
      cell: (e) => {
        return <div>
          <Link onFollow={() => {
            navigateTo(RouteNames.ViewRecipeVersion, {
              ':recipeId': e.recipeId,
              ':versionId': e.recipeVersionId,
            });
          }}>{e.recipeVersionName}</Link>
        </div>;
      },
      sortingField: 'recipeVersionName',
      sortingComparator: (a, b) => compare(a.recipeVersionName, b.recipeVersionName),
    },
    {
      id: 'recipeVersionDescription',
      header: i18n.tableHeaderRecipeVersionDescription,
      cell: e => e.recipeVersionDescription,
    },
    {
      id: 'status',
      header: i18n.tableHeaderStatus,
      cell: e => <RecipeVersionStatus status={e.status}/>,
      sortingField: 'status',
    },
    {
      id: 'lastUpdateDate',
      header: i18n.tableHeaderRecipeVersionUpdateDate,
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

  const { items, actions, filterProps, collectionProps, paginationProps } = useCollection(
    recipeVersions || [],
    {
      filtering: {
        empty: <EmptyGridNotification
          title={i18n.tableEmptyTitle}
          subTitle={i18n.tableEmptySubtitle}
          actionButtonText={i18n.createButtonText}
          actionButtonOnClick={() => {
            navigateTo(RouteNames.CreateRecipeVersion, {
              ':recipeId': recipeId,
            });
          }}
          actionButtonDisabled={
            recipeResponse?.recipe.status === 'ARCHIVED'
          }
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

  useEffect(() => {
    setSelectedRecipeVersion?.(collectionProps.selectedItems && collectionProps.selectedItems[0]);
  }, [collectionProps, setSelectedRecipeVersion]);

  // eslint-disable-next-line complexity
  function isItemSelected(predicate?: (reci: RecipeVersion) => boolean) {
    return collectionProps.selectedItems !== undefined &&
      collectionProps.selectedItems?.length >= ZERO_INDEX &&
      collectionProps.selectedItems[0] !== undefined &&
      (!predicate || predicate(collectionProps.selectedItems[0]));
  }

  function preventAnyAction() {
    return !isItemSelected() || isItemSelected(reci => reci.status === 'CREATING');
  }

  function handleDropdownClick({ detail }: CustomEvent<ButtonDropdownProps.ItemClickDetails>) {
    if (detail.id === 'update') {
      updateRecipeVersion();
    } else if (detail.id === 'release') {
      setIsReleaseRecipeVersionModalOpen(true);
    } else if (detail.id === 'retire') {
      setIsRetireRecipeVersionModalOpen(true);
    }
  }

  function preventUpdate() {
    const acceptedStatuses = RECIPE_VERSION_STATES_FOR_UPDATE;
    return !isItemSelected() ||
      isItemSelected(reci => !acceptedStatuses.has(reci.status as RecipeVersionState));
  }

  function preventRetire() {
    const acceptedStatuses = RECIPE_VERSION_STATES_FOR_RETIRE;
    return !isItemSelected() ||
      isItemSelected(reci => !acceptedStatuses.has(reci.status as RecipeVersionState));
  }

  function preventRelease() {
    let acceptedStatuses = RECIPE_VERSION_STATES_FOR_RELEASE;
    if (isFeatureAccessible(RoleBasedFeature.ProductPackagingForceReleaseRecipe)) {
      acceptedStatuses = RECIPE_VERSION_STATES_FOR_FORCE_RELEASE;
    }
    return !isItemSelected() ||
      isItemSelected(reci => !acceptedStatuses.has(reci.status as RecipeVersionState));
  }

  return <>
    <Table
      {...collectionProps}
      header={
        <Header
          variant='h2'
          counter={`(${recipeVersions?.length})`}
          actions={
            <SpaceBetween direction='horizontal' size='s'>
              <Button
                data-test='button-refresh-table'
                iconName='refresh'
                onClick={loadRecipeVersions}
                loading={recipeVersionsLoading}
              />
              <Button
                disabled={preventAnyAction()}
                onClick={viewRecipeVersion}
                data-test="view-recipe-version"
              >
                {i18n.buttonViewRecipeVersion}
              </Button>
              <ButtonDropdown
                data-test="actions-dropdown"
                onItemClick={handleDropdownClick}
                disabled={preventAnyAction()}
                items={[
                  {
                    text: i18n.recipeVersionRelease, id: 'release',
                    disabled: preventRelease()
                  },
                  {
                    text: i18n.recipeVersionUpdate, id: 'update',
                    disabled: preventUpdate()
                  },
                  {
                    text: i18n.recipeVersionRetire, id: 'retire',
                    disabled: preventRetire()
                  }
                ]}
              >
                {i18n.recipeVersionActions}
              </ButtonDropdown>
            </SpaceBetween>
          }
        >
          {i18n.tableHeader}
        </Header>
      }
      loading={recipeVersionsLoading}
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
      isLoading={recipeVersionsLoading || isReleaseInProgress}
      isOpen={isReleaseRecipeVersionModalOpen}
      onClose={() => setIsReleaseRecipeVersionModalOpen(false)}
      onConfirm={releaseRecipeVersion}
      versionName={selectedRecipeVersion?.recipeVersionName || ''}
    />
    <RetireVersionModal
      isLoading={recipeVersionsLoading || isRetireInProgress}
      isOpen={isRetireRecipeVersionModalOpen}
      onClose={() => setIsRetireRecipeVersionModalOpen(false)}
      onConfirm={retireRecipeVersion}
      versionName={selectedRecipeVersion?.recipeVersionName || ''}
    />
  </>;
};