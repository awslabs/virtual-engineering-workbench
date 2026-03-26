import { useCollection } from '@cloudscape-design/collection-hooks';
import {
  ProvisionedProductInstalledToolsListProps
} from './interface';
import { Feature } from '../../../feature-toggles/feature-toggle.state';
import { useFeatureToggles } from '../../../feature-toggles/feature-toggle.hook';
import { useState } from 'react';
import {
  Header,
  Link,
  Pagination,
  Select,
  SelectProps,
  SpaceBetween,
  Table,
  TableProps,
  TextFilter,
} from '@cloudscape-design/components';
import { EmptyGridNotification, NoMatchTableNotification } from '../../shared';
import {
  ComponentVersionDetail,
} from '../../../../services/API/proserve-wb-provisioning-api';

const PAGE_INDEX = 1;
const PAGE_SIZE = 20;

export function ProvisionedProductInstalledToolsList({
  componentVersionDetails,
  translations,
}: ProvisionedProductInstalledToolsListProps) {
  const { isFeatureEnabled } = useFeatureToggles();

  const componentVersionTypeFirstOption = {
    label: translations.selectComponentVersionTypePlaceholder,
    value: translations.componentVersionTypeAnyOption,
  };
  const [componentVersionType, setComponentVersionType] =
    useState<SelectProps.Option>(componentVersionTypeFirstOption);
  const softwareVendorFirstOption = {
    label: translations.selectSoftwareVendorPlaceholder,
    value: translations.softwareVendorAnyOption,
  };
  const [softwareVendor, setSoftwareVendor] = useState<SelectProps.Option>(
    softwareVendorFirstOption
  );

  const columnDefinitions: TableProps.ColumnDefinition<ComponentVersionDetail>[] =
    [
      {
        id: 'componentName',
        header: translations.tableHeaderComponentName,
        cell: (e) => e.componentName,
      },
      {
        id: 'softwareVersion',
        header: translations.tableHeaderSoftwareVersion,
        cell: (e) => e.softwareVersion,
      },
      {
        id: 'componentVersionType',
        header: translations.tableHeaderComponentVersionType,
        cell: (e) => e.componentVersionType,
      },
      {
        id: 'softwareVendor',
        header: translations.tableHeaderSoftwareVendor,
        cell: (e) => e.softwareVendor,
      },
      {
        id: 'notes',
        header: translations.tableHeaderNotes,
        cell: (e) => e.notes,
      },
      {
        id: 'licenseDashboard',
        header: translations.tableHeaderLicenseDashboard,
        cell: (e) =>
          <Link external href={e.licenseDashboard}>
            {' '}
            {e.licenseDashboard}{' '}
          </Link>
        ,
      },
    ];

  const { items, actions, filterProps, collectionProps, paginationProps } =
    useCollection(
      componentVersionDetails?.filter(
        (componentVersion) =>
          (componentVersion.componentVersionType ===
            componentVersionType?.value ||
            componentVersionType?.value ===
              translations.componentVersionTypeAnyOption) &&
          (componentVersion.softwareVendor === softwareVendor?.value ||
            softwareVendor?.value === translations.softwareVendorAnyOption)
      ) || [],
      {
        filtering: {
          empty:
            <NoMatchTableNotification
              title={translations.tableFilterNoResultTitle}
              buttonAction={() => actions.setFiltering('')}
              buttonText={translations.tableFilterNoResultActionText}
              subtitle={translations.tableFilterNoResultSubtitle}
            />
          ,
          noMatch:
            <NoMatchTableNotification
              title={translations.tableFilterNoResultTitle}
              buttonAction={() => actions.setFiltering('')}
              buttonText={translations.tableFilterNoResultActionText}
              subtitle={translations.tableFilterNoResultSubtitle}
            />
          ,
        },
        selection: {},
        sorting: {
          defaultState: {
            sortingColumn: columnDefinitions[0],
            isDescending: true,
          },
        },
        pagination: { defaultPage: PAGE_INDEX, pageSize: PAGE_SIZE },
      }
    );

  const getComponentVersionTypeOptions = () => {
    const componentVersionTypesOptions = [
      ...new Set(componentVersionDetails),
    ].map((componentVersion) => {
      return {
        label: componentVersion.componentVersionType,
        value: componentVersion.componentVersionType,
      } as SelectProps.Option;
    });

    componentVersionTypesOptions.unshift(componentVersionTypeFirstOption);

    return componentVersionTypesOptions;
  };

  const getSoftwareVendorOptions = () => {
    const softwareVendorsOptions = [
      ...new Set(componentVersionDetails),
    ].map((componentVersion) => {
      return {
        label: componentVersion.softwareVendor,
        value: componentVersion.softwareVendor,
      } as SelectProps.Option;
    });

    softwareVendorsOptions.unshift(softwareVendorFirstOption);

    return softwareVendorsOptions;
  };

  function renderComponentVersionDetails() {
    if (!componentVersionDetails) {
      return <></>;
    }

    return (
      <>
        <Table
          data-test="table-component-version-details"
          {...collectionProps}
          header={
            <Header
              variant="h3"
              counter={`(${componentVersionDetails.length})`}
            >
              {translations.tableHeader}
            </Header>
          }
          columnDisplay={[
            { id: 'componentName', visible: true },
            { id: 'softwareVersion', visible: true },
            { id: 'componentVersionType', visible: true },
            { id: 'softwareVendor', visible: true },
            { id: 'notes', visible: true },
            { id: 'licenseDashboard', visible: true },
          ]}
          items={items}
          empty={
            <EmptyGridNotification
              title={translations.emptyInstalledTools}
              subTitle={translations.emptyInstalledToolsSubTitle}
            />
          }
          filter={
            <SpaceBetween size="m" direction="horizontal">
              <TextFilter
                {...filterProps}
                filteringPlaceholder={
                  translations.findInstalledToolsPlaceholder
                }
                filteringAriaLabel={translations.findInstalledToolsPlaceholder}
              />
              <Select
                options={getComponentVersionTypeOptions()}
                // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
                selectedOption={componentVersionType!}
                onChange={(event) => {
                  setComponentVersionType(event.detail.selectedOption);
                }}
                placeholder={translations.selectComponentVersionTypePlaceholder}
                data-test="select-component-version-type"
              />
              <Select
                options={getSoftwareVendorOptions()}
                // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
                selectedOption={softwareVendor!}
                onChange={(event) => {
                  setSoftwareVendor(event.detail.selectedOption);
                }}
                placeholder={translations.selectSoftwareVendorPlaceholder}
                data-test="select-software-vendor"
              />
            </SpaceBetween>
          }
          pagination={<Pagination {...paginationProps} />}
          columnDefinitions={columnDefinitions}
        />
      </>
    );
  }

  return (
    <>
      {isFeatureEnabled(Feature.ProductMetadata) && componentVersionDetails &&
        renderComponentVersionDetails()}
    </>
  );
}
