import {
  Header, Link, Pagination, Table, TextFilter,
} from '@cloudscape-design/components';
import {
  RecipeVersionEntry,
} from '../../../../../services/API/proserve-wb-packaging-api';
import { i18n } from './view-component-version.translations';
import {
  CopyText, EmptyGridNotification, NoMatchTableNotification,
} from '../../../shared';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { compare } from '../../../../../utils/semantic-versioning';

const PAGE_SIZE = 20;
const PAGE_INDEX = 1;
const ONE = 1;
const ZERO = 0;

interface Row {
  id: string,
  parentId: string | null,
  recipeId: string,
  recipeName: string,
  recipeVersionId: string,
  recipeVersionName: string,
  isGroup: boolean,
  childCount: number,
}

function buildRows(entries: RecipeVersionEntry[]): Row[] {
  const groups = new Map<string, RecipeVersionEntry[]>();
  for (const e of entries) {
    const list = groups.get(e.recipeId) ?? [];
    list.push(e);
    groups.set(e.recipeId, list);
  }

  const rows: Row[] = [];
  for (const [recipeId, versions] of groups) {
    rows.push({
      id: `group:${recipeId}`,
      parentId: null,
      recipeId,
      recipeName: versions[0].recipeName,
      recipeVersionId: '',
      recipeVersionName: '',
      isGroup: true,
      childCount: versions.length,
    });
    for (const v of versions) {
      rows.push({
        id: `${recipeId}/${v.recipeVersionId}`,
        parentId: `group:${recipeId}`,
        recipeId: v.recipeId,
        recipeName: v.recipeName,
        recipeVersionId: v.recipeVersionId,
        recipeVersionName: v.recipeVersionName,
        isGroup: false,
        childCount: ZERO,
      });
    }
  }
  return rows;
}

export function ViewComponentVersionAssociatedRecipes({
  associatedRecipesVersions,
  isLoading,
}: {
  associatedRecipesVersions?: RecipeVersionEntry[],
  isLoading?: boolean,
}) {
  const { getPathFor } = useNavigationPaths();
  const allEntries = associatedRecipesVersions ?? [];
  const allItems = buildRows(allEntries);

  const {
    items, actions, filterProps, collectionProps, paginationProps,
  } = useCollection(allItems, {
    filtering: {
      empty: <EmptyGridNotification
        title={i18n.associatedRecipesEmptyTitle}
        subTitle={i18n.noAssociatedRecipes}
      />,
      noMatch: <NoMatchTableNotification
        title={i18n.associatedRecipesFilterNoResultTitle}
        buttonAction={() => actions.setFiltering('')}
        buttonText={i18n.filterNoResultActionText}
        subtitle={
          i18n.associatedRecipesFilterNoResultSubtitle
        }
      />,
    },
    pagination: {
      defaultPage: PAGE_INDEX, pageSize: PAGE_SIZE,
    },
    sorting: {
      defaultState: {
        sortingColumn: {
          sortingField: 'recipeVersionName',
          sortingComparator: (a, b) =>
            compare(a.recipeVersionName, b.recipeVersionName),
        },
        isDescending: true,
      },
    },
    expandableRows: {
      getId: (item) => item.id,
      getParentId: (item) => item.parentId,
    },
  });

  return (
    <Table
      {...collectionProps}
      header={
        <Header variant="h2" counter={`(${allEntries.length})`}>
          {i18n.associatedRecipesHeader}
        </Header>
      }
      loading={isLoading}
      expandableRows={collectionProps.expandableRows}
      columnDefinitions={[
        {
          id: 'name',
          header: i18n.columnRecipeName,
          sortingField: 'recipeName',
          cell: (e) => e.isGroup
            ? <Link
              href={getPathFor(RouteNames.ViewRecipe, {
                ':recipeId': e.recipeId,
              })}
              external
            >
              {e.recipeName}
            </Link>
            : null,
          isRowHeader: true,
        },
        {
          id: 'id',
          header: i18n.columnId,
          cell: (e) => e.isGroup
            ? <CopyText
              copyText={e.recipeId}
              successText={i18n.recipeIdCopySuccess}
              errorText={i18n.recipeIdCopyError}
              copyButtonLabel=""
            />
            : <CopyText
              copyText={e.recipeVersionId}
              successText={i18n.recipeVersionIdCopySuccess}
              errorText={i18n.recipeVersionIdCopyError}
              copyButtonLabel=""
            />,
        },
        {
          id: 'version',
          header: i18n.columnVersion,
          sortingField: 'recipeVersionName',
          sortingComparator: (a, b) =>
            compare(a.recipeVersionName, b.recipeVersionName),
          cell: (e) => {
            if (e.isGroup) {
              const n = e.childCount;
              return n === ONE
                ? `${n} version`
                : `${n} versions`;
            }
            return <Link
              href={getPathFor(RouteNames.ViewRecipeVersion, {
                ':recipeId': e.recipeId,
                ':versionId': e.recipeVersionId,
              })}
              external
            >
              {e.recipeVersionName}
            </Link>;
          },
        },
      ]}
      items={items}
      sortingDisabled={false}
      filter={
        <TextFilter
          {...filterProps}
          filteringPlaceholder={
            i18n.findAssociatedRecipesPlaceholder
          }
          filteringAriaLabel={
            i18n.findAssociatedRecipesPlaceholder
          }
        />
      }
      pagination={<Pagination {...paginationProps} />}
    />
  );
}
