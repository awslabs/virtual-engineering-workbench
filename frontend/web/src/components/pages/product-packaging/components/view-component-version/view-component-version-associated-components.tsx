import {
  Header, Link, Pagination, Table, TextFilter,
} from '@cloudscape-design/components';
import {
  ComponentVersionEntry,
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
  componentId: string,
  componentName: string,
  componentVersionId: string,
  componentVersionName: string,
  isGroup: boolean,
  childCount: number,
}

function buildRows(entries: ComponentVersionEntry[]): Row[] {
  const groups = new Map<string, ComponentVersionEntry[]>();
  for (const e of entries) {
    const list = groups.get(e.componentId) ?? [];
    list.push(e);
    groups.set(e.componentId, list);
  }

  const rows: Row[] = [];
  for (const [compId, versions] of groups) {
    rows.push({
      id: `group:${compId}`,
      parentId: null,
      componentId: compId,
      componentName: versions[0].componentName,
      componentVersionId: '',
      componentVersionName: '',
      isGroup: true,
      childCount: versions.length,
    });
    for (const v of versions) {
      rows.push({
        id: `${compId}/${v.componentVersionId}`,
        parentId: `group:${compId}`,
        componentId: v.componentId,
        componentName: v.componentName,
        componentVersionId: v.componentVersionId,
        componentVersionName: v.componentVersionName,
        isGroup: false,
        childCount: ZERO,
      });
    }
  }
  return rows;
}

export function ViewComponentVersionAssociatedComponents({
  associatedComponentsVersions,
  isLoading,
}: {
  associatedComponentsVersions?: ComponentVersionEntry[],
  isLoading?: boolean,
}) {
  const { getPathFor } = useNavigationPaths();
  const allEntries = associatedComponentsVersions ?? [];
  const allItems = buildRows(allEntries);

  const {
    items, actions, filterProps, collectionProps, paginationProps,
  } = useCollection(allItems, {
    filtering: {
      empty: <EmptyGridNotification
        title={i18n.associatedComponentsEmptyTitle}
        subTitle={i18n.noAssociatedComponents}
      />,
      noMatch: <NoMatchTableNotification
        title={i18n.associatedComponentsFilterNoResultTitle}
        buttonAction={() => actions.setFiltering('')}
        buttonText={i18n.filterNoResultActionText}
        subtitle={
          i18n.associatedComponentsFilterNoResultSubtitle
        }
      />,
    },
    pagination: {
      defaultPage: PAGE_INDEX, pageSize: PAGE_SIZE,
    },
    sorting: {
      defaultState: {
        sortingColumn: {
          sortingField: 'componentVersionName',
          sortingComparator: (a, b) =>
            compare(a.componentVersionName, b.componentVersionName),
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
          {i18n.associatedComponentsHeader}
        </Header>
      }
      loading={isLoading}
      expandableRows={collectionProps.expandableRows}
      columnDefinitions={[
        {
          id: 'name',
          header: i18n.columnComponentName,
          sortingField: 'componentName',
          cell: (e) => e.isGroup
            ? <Link
              href={getPathFor(RouteNames.ViewComponent, {
                ':componentId': e.componentId,
              })}
              external
            >
              {e.componentName}
            </Link>
            : null,
          isRowHeader: true,
        },
        {
          id: 'id',
          header: i18n.columnId,
          cell: (e) => e.isGroup
            ? <CopyText
              copyText={e.componentId}
              successText={i18n.componentIdCopySuccess}
              errorText={i18n.componentIdCopyError}
              copyButtonLabel=""
            />
            : <CopyText
              copyText={e.componentVersionId}
              successText={i18n.versionIdCopySuccess}
              errorText={i18n.versionIdCopyError}
              copyButtonLabel=""
            />,
        },
        {
          id: 'version',
          header: i18n.columnVersion,
          sortingField: 'componentVersionName',
          sortingComparator: (a, b) =>
            compare(a.componentVersionName, b.componentVersionName),
          cell: (e) => {
            if (e.isGroup) {
              const n = e.childCount;
              return n === ONE
                ? `${n} version`
                : `${n} versions`;
            }
            return <Link
              href={getPathFor(RouteNames.ViewComponentVersion, {
                ':componentId': e.componentId,
                ':versionId': e.componentVersionId,
              })}
              external
            >
              {e.componentVersionName}
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
            i18n.findAssociatedComponentsPlaceholder
          }
          filteringAriaLabel={
            i18n.findAssociatedComponentsPlaceholder
          }
        />
      }
      pagination={<Pagination {...paginationProps} />}
    />
  );
}
