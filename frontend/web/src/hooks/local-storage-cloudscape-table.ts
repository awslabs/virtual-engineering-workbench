import { TableProps } from '@cloudscape-design/components';
import { useEffect, useState } from 'react';
import { useLocalStorage, useLocalStorageNumber } from './local-storage';

const KEY_PREFIX = 'table';
const FALLBACK_NUM = 0;
export interface SortingStateWithColumnDisplay<T>
  extends TableProps.SortingState<T> {
  sortingColumn: TableProps.SortingColumn<T> & { id?: string },
}

interface Props<T> {
  key: string,
  columnDefinitions: TableProps.ColumnDefinition<T>[],
  setSorting(state: {
    isDescending?: boolean,
    sortingColumn: TableProps.ColumnDefinition<T>,
  }): void,
}

export function useCloudscapeTablePersisentState<T>(props: Props<T>) {
  const [lastSortingField, setLastSortingField] = useLocalStorage(
    `${KEY_PREFIX}-${props.key}_lastSortingField`
  );
  const [sortIndex, setSortIndex] = useLocalStorageNumber(
    `${KEY_PREFIX}-${props.key}_sortIndex`,
    FALLBACK_NUM
  );
  const [isDescending, setIsDescending] = useLocalStorageNumber(
    `${KEY_PREFIX}-${props.key}_isDescending`,
    FALLBACK_NUM
  );
  const [sortingColumn, setSortingColumn] =
    useState<TableProps.ColumnDefinition<T>>();

  function onSortingChange<T>(arg: {
    detail: SortingStateWithColumnDisplay<T>,
  }) {
    const idx = props.columnDefinitions.findIndex(
      (cd) => cd.id === arg.detail.sortingColumn.id
    );
    const soretColumn = props.columnDefinitions[idx];
    if (lastSortingField === soretColumn.sortingField) {
      // eslint-disable-next-line @typescript-eslint/no-magic-numbers
      setIsDescending(isDescending ? 0 : 1);
    } else {
      setSortIndex(idx);
      setLastSortingField(soretColumn.sortingField || null);
    }
  }

  useEffect(() => {
    const state = {
      isDescending: !!isDescending,
      sortingColumn: props.columnDefinitions[sortIndex || FALLBACK_NUM],
    };
    props.setSorting(state);
  }, [sortIndex, isDescending]);


  return {
    onSortingChange,
    sortingColumn,
    setSortingColumn,
    isDescending,
  };
}
