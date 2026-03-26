import { FC } from 'react';
import { ComponentVersionEntry } from '../../../../../services/API/proserve-wb-packaging-api';
import { Header, Link, Table, TableProps } from '@cloudscape-design/components';
import { i18n } from './component-version-entries-view.translations';
import { COMPONENT_VERSION_ENTRY_TYPE_TRANSLATIONS } from '../component-version-entry.static';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../../layout/navigation/navigation.static';

interface ComponentVersionEntriesViewProps {
  componentVersionEntries: ComponentVersionEntry[],
  typeColumnEnabled?: boolean,
  tableVariant?: TableProps.Variant,
}

const DEFAULT_ORDER = 0;
const ORDER_OFFSET = 1;
const PREPEND_PRIORITY = 1;
const USER_PRIORITY = 2;
const APPEND_PRIORITY = 3;

const getPositionPriority = (position?: string): number => {
  if (position === 'PREPEND') { return PREPEND_PRIORITY; }
  if (position === 'APPEND') { return APPEND_PRIORITY; }
  return USER_PRIORITY;
};

const compareComponentPositions = (a: ComponentVersionEntry, b: ComponentVersionEntry): number => {
  const priorityDiff = getPositionPriority(a.position) - getPositionPriority(b.position);
  if (priorityDiff !== DEFAULT_ORDER) { return priorityDiff; }
  return (a.order || DEFAULT_ORDER) - (b.order || DEFAULT_ORDER);
};

const sortComponentsByPosition = (components: ComponentVersionEntry[]): ComponentVersionEntry[] => {
  return [...components].sort(compareComponentPositions);
};

export const ComponentVersionEntriesView: FC<ComponentVersionEntriesViewProps> = ({
  componentVersionEntries = [],
  typeColumnEnabled,
  tableVariant,
}) => {
  const { getPathFor } = useNavigationPaths();
  const sortedComponents = sortComponentsByPosition(componentVersionEntries);

  const componentsWithDisplayOrder = sortedComponents.map((component, index) => ({
    ...component,
    displayOrder: index + ORDER_OFFSET
  }));

  return <Table
    variant={tableVariant}
    data-test="component-version-entries-table"
    items={componentsWithDisplayOrder}
    columnDefinitions={[
      {
        id: 'order',
        header: i18n.tableColumnOrder,
        cell: (e) => e.displayOrder,
      },
      {
        id: 'component',
        header: i18n.tableColumnComponent,
        cell: (e) =>
          <Link
            href={getPathFor(RouteNames.ViewComponent, { ':componentId': e.componentId })}
            external
          >
            {e.componentName}
          </Link>
        ,
      },
      {
        id: 'componentVersion',
        header: i18n.tableColumnComponentVersion,
        cell: (e) =>
          <Link
            href={getPathFor(RouteNames.ViewComponentVersion, {
              ':componentId': e.componentId,
              ':versionId': e.componentVersionId,
            })}
            external
          >
            {e.componentVersionName}
          </Link>
        ,
      },
      ...typeColumnEnabled ? [{
        id: 'type',
        header: i18n.tableColumnComponentVersionType,
        cell: (item: ComponentVersionEntry) =>
          COMPONENT_VERSION_ENTRY_TYPE_TRANSLATIONS[
            item.componentVersionType || ''
          ],
      }] : []
    ]}
    header={<Header variant="h2">
      {i18n.tableHeader}
    </Header>}
  />;
};