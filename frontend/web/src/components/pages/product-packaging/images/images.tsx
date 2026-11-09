import {
  Badge,
  Box,
  Button,
  Header,
  HelpPanel,
  Link,
  Pagination,
  SpaceBetween,
  Table,
  TableProps,
  PropertyFilter,
} from '@cloudscape-design/components';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { FC, useEffect } from 'react';
import { BreadcrumbItem } from '../../../layout';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout';
import { UserDate, EmptyGridNotification, NoMatchTableNotification, CopyText } from '../../shared';
import { useImages } from './images.logic';
import { i18n } from './images.translations';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { Image, GetImagesResponse } from '../../../../services/API/proserve-wb-packaging-api';
import { ImageStatus } from './image-status';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { useCloudscapeTablePersisentState } from '../../../../hooks';

const PAGE_SIZE = 20;
const PAGE_INDEX = 1;

interface ServiceAPI {
  getImages: (projectId: string) => Promise<GetImagesResponse>,
}

interface ImagesProps {
  serviceApi: ServiceAPI,
}

const Images: FC<ImagesProps> = ({ serviceApi }) => {

  const {
    images,
    loadImages,
    isLoading,
    setSelectedImage,
  } = useImages({ serviceApi });

  const { getPathFor, navigateTo } = useNavigationPaths();

  const columnDefinitions: TableProps.ColumnDefinition<Image>[] = [
    {
      id: 'amiId',
      header: i18n.tableHeaderAmiId,
      cell: (e) => e.imageUpstreamId && <CopyText
        copyText={e.imageUpstreamId}
        copyButtonLabel={i18n.copyAmiId}
        successText={i18n.copyAmiIdSuccess}
        errorText={i18n.copyAmiIdError} />,
      width: '256px',
      sortingField: 'imageUpstreamId',
    },
    {
      id: 'imageSource',
      header: i18n.tableHeaderImageSource,
      cell: (e) => {
        const source = e.imageSource || 'PIPELINE';
        const colorMap: Record<string, 'blue' | 'green' | 'grey'> = {
          PIPELINE: 'blue', EXISTING_AMI: 'green', MARKETPLACE_PRODUCT: 'grey',
        };
        const labelMap: Record<string, string> = {
          PIPELINE: i18n.imageSourcePipeline,
          EXISTING_AMI: i18n.imageSourceImported,
          MARKETPLACE_PRODUCT: i18n.imageSourceMarketplace,
        };
        return <Badge color={colorMap[source] || 'blue'}>{labelMap[source] || source}</Badge>;
      },
      width: '140px',
      sortingField: 'imageSource',
    },
    {
      id: 'status',
      header: i18n.tableHeaderStatus,
      cell: (e) => <ImageStatus status={e.status} />,
      width: '128px',
      sortingField: 'status',
    },
    {
      id: 'pipeline',
      header: i18n.tableHeaderPipeline,
      cell: (e) => e.pipelineName ?? '—',
      sortingField: 'pipelineName',
    },
    {
      id: 'buildVersion',
      header: i18n.tableHeaderBuildVersion,
      cell: (e) => e.imageBuildVersion,
      width: '158px',
      sortingField: 'imageBuildVersion',
    },
    {
      id: 'recipe',
      header: i18n.tableHeaderRecipe,
      cell: (e) =>
        e.recipeId && e.recipeName ?
          <Link
            href={getPathFor(RouteNames.ViewRecipe, { ':recipeId': e.recipeId })}
            external
          >
            {e.recipeName}
          </Link>
          : '—'
      ,
      sortingField: 'recipeName',
    },
    {
      id: 'recipeVersion',
      header: i18n.tableHeaderRecipeVersion,
      cell: (e) =>
        e.recipeId && e.recipeVersionId && e.recipeVersionName ?
          <Link
            href={getPathFor(RouteNames.ViewRecipeVersion, {
              ':recipeId': e.recipeId,
              ':versionId': e.recipeVersionId,
            })}
            external
          >
            {e.recipeVersionName}
          </Link>
          : '—'
      ,
      width: '158px',
      sortingField: 'recipeVersionName',
    },
    {
      id: 'lastUpdateDate',
      header: i18n.tableHeaderImageLastUpdate,
      cell: (e) => <UserDate date={e.lastUpdateDate} />,
      width: '196px',
      sortingField: 'lastUpdateDate',
    },
  ];

  const normalizedImages = images.map((img) => ({
    ...img,
    imageSource: img.imageSource || 'PIPELINE',
  }));

  const { items, actions, propertyFilterProps, collectionProps, paginationProps } = useCollection(
    normalizedImages,
    {
      propertyFiltering: {
        filteringProperties: [
          {
            key: 'imageSource',
            operators: ['=', '!='],
            propertyLabel: 'Source',
            groupValuesLabel: 'Source values',
          },
          {
            key: 'status',
            operators: ['=', '!='],
            propertyLabel: 'Status',
            groupValuesLabel: 'Status values',
          },
          {
            key: 'pipelineName',
            operators: ['=', ':'],
            propertyLabel: 'Pipeline',
            groupValuesLabel: 'Pipeline values',
          },
          {
            key: 'recipeName',
            operators: ['=', ':'],
            propertyLabel: 'Recipe',
            groupValuesLabel: 'Recipe values',
          },
        ],
        empty: <NoMatchTableNotification
          title={i18n.tableFilterNoResultTitle}
          buttonAction={() => actions.setFiltering('')}
          buttonText={i18n.tableFilterNoResultActionText}
          subtitle={i18n.tableFilterNoResultSubtitle}
        />,
        noMatch: <NoMatchTableNotification
          title={i18n.tableFilterNoResultTitle}
          buttonAction={() => actions.setFiltering('')}
          buttonText={i18n.tableFilterNoResultActionText}
          subtitle={i18n.tableFilterNoResultSubtitle} />,
      },
      selection: {},
      sorting: {
        defaultState: {
          sortingColumn: columnDefinitions.find(
            x => x.id === 'lastUpdateDate',
          ) || {},
          isDescending: true,
        },
      },
      pagination: { defaultPage: PAGE_INDEX, pageSize: PAGE_SIZE }
    }
  );

  const { onSortingChange } = useCloudscapeTablePersisentState<Image>({
    key: 'prod-man-images',
    columnDefinitions,
    setSorting: actions.setSorting,
  });

  useEffect(() => {
    setSelectedImage?.(collectionProps.selectedItems && collectionProps.selectedItems[0]);
  }, [collectionProps, setSelectedImage]);

  return (
    <WorkbenchAppLayout
      breadcrumbItems={getBreadcrumbItems()}
      content={renderContent()}
      contentType="default"
      tools={renderTools()}
      customHeader={renderHeader()}
    />
  );

  function getBreadcrumbItems(): BreadcrumbItem[] {
    return [
      { path: i18n.breadcrumbLevel1, href: '#' },
    ];
  }

  function renderHeader() {
    return <>
      <Header
        variant='h1'
        description={i18n.navHeaderDescription}
        actions={
          <SpaceBetween direction="horizontal" size="xs">
            <Button onClick={() => navigateTo(RouteNames.ImportImage)}>{i18n.importAmiButton}</Button>
            <Button onClick={() => {
              navigateTo(RouteNames.Pipelines);
            }}
            variant='primary'
            data-test='create-image-btn'
            >
              {i18n.createButtonText}
            </Button>
          </SpaceBetween>
        }
      >
        {i18n.navHeader}
      </Header>
    </>;
  }

  function renderContent() {
    return (
      <>
        <Table
          data-test="table-images"
          {...collectionProps}
          trackBy="imageId"
          onSortingChange={onSortingChange}
          header={
            <Header
              variant="h2"
              counter={`(${images.length})`}
              actions={
                <SpaceBetween direction="horizontal" size="m">
                  <Button
                    data-test="button-refresh-table"
                    iconName="refresh"
                    onClick={loadImages}
                    loading={isLoading}
                  />
                </SpaceBetween>
              }
            >
              {i18n.tableHeader}
            </Header>
          }
          loading={isLoading}
          items={items}
          selectionType="single"
          empty={
            <EmptyGridNotification
              title={i18n.emptyImages}
              subTitle={i18n.emptyImagesSubTitle}
              actionButtonText={i18n.emptyImagesResolve}
              actionButtonOnClick={emptyImagesResolveAction}
            />
          }
          filter={
            <PropertyFilter
              {...propertyFilterProps}
              i18nStrings={{
                dismissAriaLabel: 'Dismiss',
                groupValuesText: 'Values',
                groupPropertiesText: 'Properties',
                operatorsText: 'Operators',
                operationAndText: 'and',
                operationOrText: 'or',
                operatorEqualsText: 'Equals',
                operatorDoesNotEqualText: 'Does not equal',
                operatorContainsText: 'Contains',
                operatorDoesNotContainText: 'Does not contain',
                editTokenHeader: 'Edit filter',
                propertyText: 'Property',
                operatorText: 'Operator',
                valueText: 'Value',
                cancelActionText: 'Cancel',
                applyActionText: 'Apply',
                allPropertiesLabel: 'All properties',
                clearFiltersText: 'Clear filters',
                tokenLimitShowMore: 'Show more',
                tokenLimitShowFewer: 'Show fewer',
                removeTokenButtonAriaLabel: (token) =>
                  `Remove token ${token.propertyKey} ${token.operator} ${token.value}`,
                enteredTextLabel: (text) => `Use: "${text}"`,
              }}
              expandToViewport
              hideOperations
              tokenLimit={2}
            />
          }
          pagination={<Pagination {...paginationProps} />}
          columnDefinitions={columnDefinitions}
          contentDensity="compact"
          wrapLines
        />
      </>
    );
  }


  function emptyImagesResolveAction() {
    navigateTo(RouteNames.Pipelines);
  }

  function renderTools() {
    return (
      <HelpPanel header={<h2>{i18n.infoPanelHeader}</h2>}>
        <SpaceBetween size={'s'}>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel1}</Box>
          <Box variant="p">{i18n.infoPanelMessage1}</Box>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel2}</Box>
          <Box variant="p">{i18n.infoPanelMessage2}</Box>
          <SpaceBetween size="xs">
            <Box>
              <Box variant="awsui-key-label">{i18n.infoPanelPoint1}</Box>
              <Box variant="p">{i18n.infoPanelPoint1Message}</Box>
            </Box>
            <Box>
              <Box variant="awsui-key-label">{i18n.infoPanelPoint2}</Box>
              <Box variant="p">{i18n.infoPanelPoint2Message}</Box>
            </Box>
          </SpaceBetween>
        </SpaceBetween>
      </HelpPanel>
    );
  }
};

export { Images };
