import Table, { TableProps } from '@cloudscape-design/components/table';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { EmptyGridNotification } from '../empty-grid-notification.tsx';
import { Pagination, PropertyFilter } from '@cloudscape-design/components';
import { propertyFilterI18nStrings } from './generic-table.translation.ts';

const DEFAULT_PAGE_SIZE = 20;
const PAGE_INDEX = 1;

export interface KeyValuePair {
  [k: string]: string | KeyValuePair[],
}

export interface GenericTableProps
  extends Omit<TableProps, 'columnDefinitions' | 'items'> {
  data: readonly KeyValuePair[],
}

function genericTable(props: GenericTableProps) {
  const header = Array.from(
    new Set(props.data.map((item) => Object.keys(item)).flatMap((x) => x))
  );
  const columnDefinitions: ReadonlyArray<TableProps.ColumnDefinition<any>> =
    header.map((h) => {
      return {
        id: `id-${h}`,
        header: `${h}`,
        cell: (value) => {
          if (!(h in value)) {
            return <>-</>;
          }
          if (typeof value[h] === 'string') {
            return <>{value[h]}</>;
          }
          return <>{JSON.stringify(value[h])}</>;
        },
        sortingField: `${h}`,
      };
    });

  const filteringProperties: readonly any[] = header.map((h) => {
    return {
      key: `${h}`,
      operators: ['=', ':', '!='],
      propertyLabel: `${h}`,
      groupValuesLabel: `${h}`,
    };
  });
  const { items, collectionProps, propertyFilterProps, paginationProps } =
    useCollection(props.data, {
      propertyFiltering: {
        empty:
          <EmptyGridNotification
            title={'EmptyHeader'}
            subTitle={'Empty Subtitle'}
          />
        ,
        noMatch: <EmptyGridNotification title={''} subTitle={''} />,
        filteringProperties: filteringProperties,
      },
      pagination: { defaultPage: PAGE_INDEX, pageSize: DEFAULT_PAGE_SIZE },
      sorting: {},
      selection: {},
    });

  return (
    <Table
      {...collectionProps}
      {...props}
      pagination={<Pagination {...paginationProps} />}
      columnDefinitions={columnDefinitions}
      items={items}
      filter={
        <PropertyFilter
          {...propertyFilterProps}
          i18nStrings={propertyFilterI18nStrings}
          expandToViewport
          hideOperations
        />
      }
    />
  );
}

export { genericTable as GenericTable };
