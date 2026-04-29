/* eslint-disable @typescript-eslint/no-magic-numbers */
import { useState, useEffect } from 'react';
import { i18n } from './component-version-entries-input.translations';
import useSwr from 'swr';
import { SelectProps } from '@cloudscape-design/components';
import { useNotifications } from '../../../../layout';
import {
  GetComponentsVersionsResponse,
  ComponentVersionEntry,
  ComponentVersionSummary,
} from '../../../../../services/API/proserve-wb-packaging-api';
import { compare } from '../../../../../utils/semantic-versioning';

const MOVE_UP = 'UP';
const MOVE_DOWN = 'DOWN';
const INSERT_ABOVE = 'ABOVE';
const INSERT_BELOW = 'BELOW';
const MOVE_TO_TOP = 'TOP';
const MOVE_TO_BOTTOM = 'BOTTOM';
const DEFAULT_ORDER = 0;

const orderOf = (entry: ComponentVersionEntry): number =>
  entry.order ?? DEFAULT_ORDER;

interface ServiceAPI {
  getComponentsVersions: (
    projectId: string,
    status: string[],
    platform: string,
    os: string,
    arch: string,
  ) => Promise<GetComponentsVersionsResponse>,
}

const FETCH_KEY = (
  projectId: string,
  status: string[],
  platform: string,
  osVersion: string,
  architecture: string
) => {
  if (!projectId) {
    return null;
  }
  return [
    `projects/${projectId}/${status.join('+')}/${platform}/${osVersion}/${architecture}`,
    projectId,
    status,
    platform,
    osVersion,
    architecture
  ];
};

export const useComponentVersionsEntriesInput = ({
  projectId,
  platform,
  osVersion,
  architecture,
  serviceAPI,
  componentVersionEntries,
  setComponentVersionEntries,
  isComponentVersionsEntriesValid,
  minComponentVersionEntries,
  excludedComponents,
  excludedComponentVersions,
  componentVersionStatuses,
  componentVersionView,
}: {
  projectId: string,
  platform: string,
  osVersion: string,
  architecture: string,
  serviceAPI: ServiceAPI,
  componentVersionEntries: ComponentVersionEntry[],
  setComponentVersionEntries: (componentVersionEntries: ComponentVersionEntry[]) => void,
  isComponentVersionsEntriesValid: boolean,
  minComponentVersionEntries: number,
  excludedComponents: string[],
  excludedComponentVersions: string[],
  componentVersionStatuses: string[],
  componentVersionView: ComponentVersionEntry[],
}) => {

  const { showErrorNotification } = useNotifications();
  const [componentsVersions, setComponentVersions] = useState<ComponentVersionSummary[]>();
  const [isComponentsVersionsValid, setIsComponentsVersionsValid] = useState(true);

  const fetcher = ([
    ,
    projectId,
    status,
    platform,
    osVersion,
    architecture
  ]: [
      url: string,
      projectId: string,
      status: string[],
      platform: string,
      osVersion: string,
      architecture: string,
  ]) => {
    return serviceAPI.getComponentsVersions(
      projectId,
      status,
      platform,
      osVersion,
      architecture
    );
  };

  const { data, isLoading } = useSwr(
    FETCH_KEY(
      projectId,
      componentVersionStatuses,
      platform,
      osVersion,
      architecture,
    ),
    fetcher, {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.fetchComponentsVersionsError,
          content: err.message
        });
      }
    }
  );

  useEffect(() => {
    setComponentVersions(data?.componentsVersionsSummary);
    setIsComponentsVersionsValid(
      !!data?.componentsVersionsSummary && data?.componentsVersionsSummary.length > 0
    );
    if (componentVersionEntries.length < minComponentVersionEntries) {
      addComponentVersionEntry(minComponentVersionEntries - componentVersionEntries.length);
    }
  }, [data]);

  function getComponentsSelectOptions(currentComponentId?: string) {
    const selectedComponentIds = new Set([
      ...componentVersionView.map(view => view.componentId),
      ...componentVersionEntries
        .map(entry => entry.componentId)
        .filter(id => id && id !== currentComponentId),
    ]);
    const components = [...new Set(componentsVersions
      ?.filter(item => !excludedComponents.includes(item.componentId))
      .map(item => item.componentId))];
    return components
      .filter(componentId => !selectedComponentIds.has(componentId))
      .map((item) => {
        const component = componentsVersions?.find(x => x.componentId === item);
        return {
          label: component?.componentName || '',
          value: item,
        };
      })
      .sort((a, b) => a.label.localeCompare(b.label));
  }

  function getComponentVersionsSelectOptions(
    selectedComponent: string,
  ) {
    return componentsVersions
      ?.filter(
        (item) =>
          item.componentId === selectedComponent &&
          !excludedComponentVersions.includes(item.componentVersionId)
      )
      ?.map((item) => ({
        label: item.componentVersionName,
        value: item.componentVersionId,
      })).sort((a, b) => compare(a.label, b.label));
  }

  function setDefaultComponentVersion(
    selectedComponent: string,
    componentVersionEntry: ComponentVersionEntry
  ) {
    if (selectedComponent) {
      const componentVersions = getComponentVersionsSelectOptions(selectedComponent);
      componentVersionEntry.componentVersionId = componentVersions?.[0].value || '';
      componentVersionEntry.componentVersionName = componentVersions?.[0].label || '';
    }
  }

  function onComponentChange(
    componentVersionEntry: ComponentVersionEntry,
    selectedComponent: SelectProps.Option) {
    const updatedComponentVersion = componentVersionEntries
      .find((x) => x.order === componentVersionEntry.order) || {} as ComponentVersionEntry;
    updatedComponentVersion.componentId = selectedComponent.value || '';
    updatedComponentVersion.componentName = selectedComponent.label || '';
    setDefaultComponentVersion(updatedComponentVersion.componentId, updatedComponentVersion);
    setComponentVersionEntries([
      ...componentVersionEntries.filter((x) => x.order !== componentVersionEntry.order),
      updatedComponentVersion
    ]);
  }

  function onComponentVersionChange(
    componentVersionEntry: ComponentVersionEntry,
    selectedComponentVersion: SelectProps.Option) {
    const updatedComponentVersion = componentVersionEntries
      .find((x) => x.order === componentVersionEntry.order) || {} as ComponentVersionEntry;
    updatedComponentVersion.componentVersionId = selectedComponentVersion.value || '';
    updatedComponentVersion.componentVersionName = selectedComponentVersion.label || '';
    setComponentVersionEntries([
      ...componentVersionEntries.filter((x) => x.order !== componentVersionEntry.order),
      updatedComponentVersion
    ]);
  }

  function onComponentVersionTypeChange(
    componentVersionEntry: ComponentVersionEntry,
    selectedComponentVersionType: SelectProps.Option) {
    const updatedComponentVersion = componentVersionEntries
      .find((x) => x.order === componentVersionEntry.order) || {} as ComponentVersionEntry;
    updatedComponentVersion.componentVersionType = selectedComponentVersionType.value || '';
    setComponentVersionEntries([
      ...componentVersionEntries.filter((x) => x.order !== componentVersionEntry.order),
      updatedComponentVersion
    ]);
  }

  function getNewComponentVersionEntry(order: number) {
    return {
      componentId: '',
      componentName: '',
      componentVersionId: '',
      componentVersionName: '',
      componentVersionType: 'HELPER',
      order: order,
    };
  }

  function addComponentVersionEntry(n = 1) {
    const maxOrderFromEntries = componentVersionEntries.length > 0
      ? Math.max(...componentVersionEntries.map(e => e.order || 0))
      : 0;
    const maxOrderFromView = componentVersionView.length > 0
      ? Math.max(...componentVersionView.map(e => e.order || 0))
      : 0;
    const maxOrder = Math.max(maxOrderFromEntries, maxOrderFromView);

    setComponentVersionEntries([
      ...componentVersionEntries,
      ...Array(n).fill(0).map((_, i) => getNewComponentVersionEntry(maxOrder + i + 1))
    ]);
  }

  function removeComponentVersionEntry(order: number) {
    setComponentVersionEntries(
      componentVersionEntries
        .filter((x) => x.order !== order)
        .sort((a, b) => orderOf(a) - orderOf(b))
        .map((x, i) => ({ ...x, order: i + 1 } as ComponentVersionEntry))
    );
  }

  function preventRemoveComponentVersionEntry() {
    return componentVersionEntries.length === minComponentVersionEntries;
  }

  function moveComponentVersionEntry(order: number, direction: string) {
    const componentVersionEntry = componentVersionEntries.find((x) =>
      x.order === order
    ) || {} as ComponentVersionEntry;
    const componentVersionToSwap = componentVersionEntries.find((x) =>
      x.order === (direction === MOVE_UP ? order - 1 : order + 1)
    ) || {} as ComponentVersionEntry;
    const updatedComponentVersionEntry = {
      ...componentVersionEntry,
      order: componentVersionToSwap.order
    };
    const updatedComponentVersionEntryToSwap = {
      ...componentVersionToSwap,
      order: componentVersionEntry.order
    };
    setComponentVersionEntries([
      ...componentVersionEntries.filter((x) =>
        x.order !== componentVersionEntry.order && x.order !== componentVersionToSwap.order
      ),
      updatedComponentVersionEntry,
      updatedComponentVersionEntryToSwap
    ]);
  }

  function preventMoveComponentVersionEntry(order: number, direction: string) {
    return direction === MOVE_UP ? order === 1 : order === componentVersionEntries.length;
  }

  function insertComponentVersionEntry(order: number, direction: string) {
    const currentComponentVersionEntry = componentVersionEntries.find((x) => x.order === order);

    if (currentComponentVersionEntry) {
      const updatedComponentVersionEntry = {
        ...currentComponentVersionEntry,
        order: direction === INSERT_ABOVE
          ? orderOf(currentComponentVersionEntry) + 1
          : orderOf(currentComponentVersionEntry)
      };

      const componentVersionEntriesAbove: ComponentVersionEntry[] = componentVersionEntries
        .filter((x) => orderOf(x) < orderOf(currentComponentVersionEntry))
        .map((x) => x);


      const componentVersionEntriesBelow: ComponentVersionEntry[] = componentVersionEntries
        .filter((x) => orderOf(x) > orderOf(currentComponentVersionEntry))
        .map((x) => ({ ...x, order: orderOf(x) + 1 }));

      const newComponentVersionEntry = getNewComponentVersionEntry(
        direction === INSERT_ABOVE
          ? orderOf(currentComponentVersionEntry)
          : orderOf(currentComponentVersionEntry) + 1
      );

      setComponentVersionEntries([
        ...componentVersionEntriesAbove,
        updatedComponentVersionEntry,
        newComponentVersionEntry,
        ...componentVersionEntriesBelow
      ]);
    }
  }

  function moveComponentVersionEntryToEnd(order: number, direction: string) {
    const currentComponentVersionEntry = componentVersionEntries.find((x) => x.order === order);

    if (currentComponentVersionEntry) {
      const updatedComponentVersionEntry = {
        ...currentComponentVersionEntry,
        order: direction === MOVE_TO_TOP
          ? 1
          : componentVersionEntries.length
      };

      const componentVersionEntriesAbove: ComponentVersionEntry[] = componentVersionEntries
        .filter((x) => orderOf(x) < orderOf(currentComponentVersionEntry))
        .map((x) => ({ ...x, order: direction === MOVE_TO_TOP ? orderOf(x) + 1 : x.order }));

      const componentVersionEntriesBelow: ComponentVersionEntry[] = componentVersionEntries
        .filter((x) => orderOf(x) > orderOf(currentComponentVersionEntry))
        .map((x) => ({ ...x, order: direction === MOVE_TO_TOP ? x.order : orderOf(x) - 1 }));

      setComponentVersionEntries([
        ...componentVersionEntriesAbove,
        updatedComponentVersionEntry,
        ...componentVersionEntriesBelow
      ]);
    }
  }

  // eslint-disable-next-line complexity
  function handleAdditionalActions(action: string, order: number) {
    switch (action) {
      case 'insert-above':
        insertComponentVersionEntry(order, INSERT_ABOVE);
        break;
      case 'insert-below':
        insertComponentVersionEntry(order, INSERT_BELOW);
        break;
      case 'move-to-top':
        moveComponentVersionEntryToEnd(order, MOVE_TO_TOP);
        break;
      case 'move-to-bottom':
        moveComponentVersionEntryToEnd(order, MOVE_TO_BOTTOM);
        break;
      default:
        break;
    }
  }

  function getComponentError(componentVersionEntry: ComponentVersionEntry) {
    return !isComponentVersionsEntriesValid && componentVersionEntry.componentId === ''
      ? i18n.inputComponentError : '';
  }

  function getComponentVersionError(componentVersionEntry: ComponentVersionEntry) {
    return !isComponentVersionsEntriesValid && componentVersionEntry.componentVersionId === ''
      ? i18n.inputVersionError : '';
  }

  function getComponentVersionTypeError(componentVersionEntry: ComponentVersionEntry) {
    return !isComponentVersionsEntriesValid && componentVersionEntry.componentVersionType === ''
      ? i18n.inputTypeError : '';
  }

  return {
    getComponentsSelectOptions,
    getComponentVersionsSelectOptions,
    onComponentChange,
    onComponentVersionChange,
    onComponentVersionTypeChange,
    addComponentVersionEntry,
    removeComponentVersionEntry,
    preventRemoveComponentVersionEntry,
    moveComponentVersionEntry,
    preventMoveComponentVersionEntry,
    handleAdditionalActions,
    getComponentError,
    getComponentVersionError,
    getComponentVersionTypeError,
    componentsVersions,
    componentVersionEntries,
    isComponentsVersionsLoading: isLoading,
    isComponentsVersionsValid,
    MOVE_DOWN,
    MOVE_UP,
    INSERT_ABOVE,
    INSERT_BELOW,
    MOVE_TO_TOP,
    MOVE_TO_BOTTOM
  };
};