/* eslint-disable @typescript-eslint/no-magic-numbers */
/* eslint-disable complexity */
import {
  Alert,
  Box,
  Button,
  ButtonDropdown,
  ColumnLayout,
  FormField,
  Select,
  SpaceBetween,
  Spinner,
  StatusIndicator,
  Input,
} from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n } from './component-version-entries-input.translations';
import { useComponentVersionsEntriesInput } from './component-version-entries-input.logic';
import { packagingAPI } from '../../../../../services';
import { ComponentVersionEntry } from '../../../../../services/API/proserve-wb-packaging-api';
import {
  COMPONENT_VERSION_ENTRY_TYPES,
} from '../component-version-entry.static';

const DEFAULT_COMPONENT_VERSION_STATUS = 'RELEASED';
const MIN_OPTIONS_FOR_FILTERING = 5;
const DEFAULT_ORDER = 0;
const PREPEND_PRIORITY = 1;
const USER_PRIORITY = 2;
const APPEND_PRIORITY = 3;

const orderOf = (entry: ComponentVersionEntry): number =>
  entry.order ?? DEFAULT_ORDER;

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

export interface ComponentVersionEntriesInputProps {
  projectId: string,
  platform: string,
  osVersion: string,
  architecture: string,
  componentVersionEntries: ComponentVersionEntry[],
  setComponentVersionEntries: (componentsVersionEntries: ComponentVersionEntry[]) => void,
  isComponentVersionsEntriesValid: boolean,
  typeSelectionEnabled?: boolean,
  minComponentVersionEntries?: number,
  excludedComponents?: string[],
  excludedComponentVersions?: string[],
  componentVersionStatuses?: string[],
  componentVersionView?: ComponentVersionEntry[],
}

export const ComponentVersionEntriesInput: FC<ComponentVersionEntriesInputProps> = ({
  projectId,
  platform,
  osVersion,
  architecture,
  componentVersionEntries,
  setComponentVersionEntries,
  isComponentVersionsEntriesValid,
  typeSelectionEnabled,
  minComponentVersionEntries = 1,
  excludedComponents = [],
  excludedComponentVersions = [],
  componentVersionStatuses = [DEFAULT_COMPONENT_VERSION_STATUS],
  componentVersionView
}) => {
  const {
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
    isComponentsVersionsLoading,
    isComponentsVersionsValid,
    MOVE_DOWN,
    MOVE_UP
  } = useComponentVersionsEntriesInput({
    projectId,
    platform,
    osVersion,
    architecture,
    serviceAPI: packagingAPI,
    componentVersionEntries,
    setComponentVersionEntries,
    isComponentVersionsEntriesValid,
    minComponentVersionEntries,
    excludedComponents,
    excludedComponentVersions,
    componentVersionStatuses,
    componentVersionView: typeSelectionEnabled ? componentVersionView ?? [] : [],
  });

  if (isComponentsVersionsLoading) {
    return <Spinner size="large" />;
  }

  if (!isComponentsVersionsLoading && !isComponentsVersionsValid) {
    return <Alert
      statusIconAriaLabel='Info'
      type='info'
      header={i18n.componentsVersionsErrorHeader}
    >
      {i18n.componentsVersionsErrorContent}
    </Alert>;
  }

  function renderComponentVersionEntry(componentVersionEntry: ComponentVersionEntry) {
    return <ColumnLayout columns={typeSelectionEnabled ? 4 : 3} key={componentVersionEntry.order}>
      <FormField errorText={getComponentError(componentVersionEntry)}>
        {(() => {
          const componentOptions = getComponentsSelectOptions(componentVersionEntry.componentId);
          const selectedComponentOption =
            componentOptions.find(x => x.value === componentVersionEntry.componentId) || null;
          const filteringType =
            componentOptions.length > MIN_OPTIONS_FOR_FILTERING ? 'auto' : 'none';
          return (
            <Select
              data-test="components-select"
              options={componentOptions}
              selectedOption={selectedComponentOption}
              onChange={({ detail }) => {
                onComponentChange(componentVersionEntry, detail.selectedOption);
              }}
              filteringType={filteringType}
              placeholder={i18n.inputComponentDescription}
            />
          );
        })()}
      </FormField>
      <FormField errorText={getComponentVersionError(componentVersionEntry)}>
        <Select
          data-test="component-versions-select"
          options={getComponentVersionsSelectOptions(
            componentVersionEntry.componentId
          )}
          selectedOption={
            getComponentVersionsSelectOptions(
              componentVersionEntry.componentId
            )?.find(
              (x) => x.value === componentVersionEntry.componentVersionId
            ) || null
          }
          onChange={({ detail }) => {
            onComponentVersionChange(
              componentVersionEntry,
              detail.selectedOption
            );
          }}
          filteringType={
            (getComponentVersionsSelectOptions(
              componentVersionEntry.componentId
            ) || []).length > MIN_OPTIONS_FOR_FILTERING
              ? 'auto'
              : 'none'
          }
          placeholder={i18n.inputVersionDescription}
        />
      </FormField>
      {typeSelectionEnabled && <FormField errorText={getComponentVersionTypeError(componentVersionEntry)}>
        <Select
          data-test="component-version-type-select"
          options={COMPONENT_VERSION_ENTRY_TYPES}
          selectedOption={
            COMPONENT_VERSION_ENTRY_TYPES
              ?.find((x) => x.value === componentVersionEntry.componentVersionType) || null
          }
          onChange={({ detail }) => {
            onComponentVersionTypeChange(componentVersionEntry, detail.selectedOption);
          }}
          placeholder={i18n.inputTypeDescription}
        />
      </FormField>}
      <SpaceBetween size='xs' direction='horizontal'>
        <Button
          iconName='remove'
          ariaLabel={i18n.buttonRemove}
          onClick={() => removeComponentVersionEntry(orderOf(componentVersionEntry))}
          disabled={preventRemoveComponentVersionEntry()}
        />
        <Button
          iconName='caret-up-filled'
          ariaLabel={i18n.buttonMoveUp}
          onClick={() => moveComponentVersionEntry(orderOf(componentVersionEntry), MOVE_UP)}
          disabled={preventMoveComponentVersionEntry(orderOf(componentVersionEntry), MOVE_UP)}
        />
        <Button
          iconName='caret-down-filled'
          ariaLabel={i18n.buttonMoveDown}
          onClick={() => moveComponentVersionEntry(orderOf(componentVersionEntry), MOVE_DOWN)}
          disabled={preventMoveComponentVersionEntry(orderOf(componentVersionEntry), MOVE_DOWN)}
        />
        <ButtonDropdown
          variant='icon'
          onItemClick={({ detail }) => handleAdditionalActions(detail.id, orderOf(componentVersionEntry))}
          ariaLabel={i18n.buttonMore}
          items={[
            {
              id: 'move-to-top',
              text: i18n.buttonMoveToTop,
              disabled: preventMoveComponentVersionEntry(orderOf(componentVersionEntry), MOVE_UP),
            },
            {
              id: 'move-to-bottom',
              text: i18n.buttonMoveToBottom,
              disabled: preventMoveComponentVersionEntry(orderOf(componentVersionEntry), MOVE_DOWN),
            },
            {
              id: 'insert-above',
              text: i18n.buttonInsertAbove,
            },
            {
              id: 'insert-below',
              text: i18n.buttonInsertBelow,
            }
          ]}
        />
      </SpaceBetween>
    </ColumnLayout>;
  }
  function renderComponentVersionView(componentVersionView: ComponentVersionEntry) {
    return (
      <ColumnLayout columns={typeSelectionEnabled ? 4 : 3} key={componentVersionView.order}>
        <FormField errorText={getComponentError(componentVersionView)}>
          <Input
            value={componentVersionView.componentName}
            disabled = {true}
          />
        </FormField>
        <FormField errorText={getComponentVersionError(componentVersionView)}>
          <Input
            value={componentVersionView.componentVersionName}
            disabled = {true}
          />
        </FormField>
        {typeSelectionEnabled &&
              <FormField errorText={getComponentVersionTypeError(componentVersionView)}>
                <Input
                  value={componentVersionView.componentVersionType || ''}
                  disabled = {true}
                />
              </FormField>
        }
        <SpaceBetween size='xs' direction='horizontal'>
          <Button
            iconName='remove'
            ariaLabel={i18n.buttonRemove}
            onClick={() => removeComponentVersionEntry(orderOf(componentVersionView))}
            disabled={true}
          />
          <Button
            iconName='caret-up-filled'
            ariaLabel={i18n.buttonMoveUp}
            onClick={() => moveComponentVersionEntry(orderOf(componentVersionView), MOVE_UP)}
            disabled={true}
          />
          <Button
            iconName='caret-down-filled'
            ariaLabel={i18n.buttonMoveDown}
            onClick={() => moveComponentVersionEntry(orderOf(componentVersionView), MOVE_DOWN)}
            disabled={true}
          />
          <ButtonDropdown
            variant='icon'
            onItemClick={({ detail }) => handleAdditionalActions(detail.id, orderOf(componentVersionView))}
            ariaLabel={i18n.buttonMore}
            items={[
              {
                id: 'move-to-top',
                text: i18n.buttonMoveToTop,
                disabled: true,
              },
              {
                id: 'move-to-bottom',
                text: i18n.buttonMoveToBottom,
                disabled: true,
              },
              {
                id: 'insert-above',
                text: i18n.buttonInsertAbove,
              },
              {
                id: 'insert-below',
                text: i18n.buttonInsertBelow,
              }
            ]}
          />
          {typeSelectionEnabled &&
          <StatusIndicator type="info">
            {
              (componentVersionView as any).isIntegrationComponent ?
                'Integration' :
                i18n.mandatoryComponentLabel
            }
          </StatusIndicator>}
        </SpaceBetween>
      </ColumnLayout>
    );
  }

  const allComponents = typeSelectionEnabled
    ? sortComponentsByPosition([
      ...componentVersionView ?? [],
      ...componentVersionEntries
    ])
    : componentVersionEntries.sort((a, b) => orderOf(a) - orderOf(b));

  const prependedComponents = allComponents.filter(c => c.position === 'PREPEND');
  const userComponents = allComponents.filter(c => !c.position);
  const appendedComponents = allComponents.filter(c => c.position === 'APPEND');

  return (
    <SpaceBetween direction="vertical" size="xs">
      <Box></Box>
      {componentVersionEntries.length > 0 &&
      <ColumnLayout columns={typeSelectionEnabled ? 4 : 3}>
        <Box variant="awsui-key-label">{i18n.labelComponent}</Box>
        <Box variant="awsui-key-label">{i18n.labelVersion}</Box>
        {typeSelectionEnabled &&
          <Box variant="awsui-key-label">{i18n.labelType}</Box>
        }
      </ColumnLayout>}
      <SpaceBetween size="xs" direction="vertical">
        {typeSelectionEnabled && prependedComponents.map(renderComponentVersionView)}
        {userComponents.map(renderComponentVersionEntry)}
        {typeSelectionEnabled && appendedComponents.map(renderComponentVersionView)}
      </SpaceBetween>
      <Box>
        {minComponentVersionEntries > 0
        && i18n.minComponentVersionEntriesMessage(minComponentVersionEntries)}
      </Box>
      <Button onClick={() => addComponentVersionEntry(1)}>
        {i18n.buttonAddComponent}
      </Button>
    </SpaceBetween>
  );
};