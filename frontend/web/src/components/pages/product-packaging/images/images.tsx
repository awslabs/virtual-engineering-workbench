/* eslint-disable */
import {
  Box,
  Button,
  Header,
  HelpPanel,
  Link,
  Pagination,
  SpaceBetween,
  Table,
  TableProps,
  TextFilter,
} from '@cloudscape-design/components';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { FC, useEffect } from 'react';
import { BreadcrumbItem } from '../../../layout';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout';
import { UserDate, EmptyGridNotification, NoMatchTableNotification, CopyText } from '../../shared';
import { useImages } from './images.logic';
import { i18n, } from './images.translations';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { Image } from '../../../../services/API/proserve-wb-packaging-api';
import { ImageStatus } from './image-status';
import { packagingAPI } from '../../../../services';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { useCloudscapeTablePersisentState } from '../../../../hooks';

const PAGE_SIZE = 20;
const PAGE_INDEX = 1;
const ZERO_INDEX = 0;

interface ImagesProps {
}

const Images: FC<ImagesProps> = () => {

  const {
    images,
    loadImages,
    isLoading,
    setSelectedImage,
  } = useImages({serviceApi: packagingAPI});

  const { getPathFor, navigateTo } = useNavigationPaths();

  const columnDefinitions: TableProps.ColumnDefinition<Image>[] = [
    {
      id: "amiId",
      header: i18n.tableHeaderAmiId,
      cell: (e) => e.imageUpstreamId && <CopyText
      copyText={e.imageUpstreamId}
      copyButtonLabel={i18n.copyAmiId}
      successText={i18n.copyAmiIdSuccess}
      errorText={i18n.copyAmiIdError} />,
      width: "256px",
      sortingField: "imageUpstreamId",
    },
    {
      id: "pipeline",
      header: i18n.tableHeaderPipeline,
      cell: (e) => e.pipelineName,
      sortingField: "pipelineName",
    },
    {
      id: "buildVersion",
      header: i18n.tableHeaderBuildVersion,
      cell: (e) => e.imageBuildVersion,
      width: "158px",
      sortingField: "imageBuildVersion",
    },
    {
      id: "recipe",
      header: i18n.tableHeaderRecipe,
      cell: (e) => (
        <Link
          href={getPathFor(RouteNames.ViewRecipe, { ":recipeId": e.recipeId })}
          external
        >
          {e.recipeName}
        </Link>
      ),
      sortingField: "recipeName",
    },
    {
      id: "recipeVersion",
      header: i18n.tableHeaderRecipeVersion,
      cell: (e) => (
        <Link
          href={getPathFor(RouteNames.ViewRecipeVersion, {
            ":recipeId": e.recipeId,
            ":versionId": e.recipeVersionId,
          })}
          external
        >
          {e.recipeVersionName}
        </Link>
      ),
      width: "158px",
      sortingField: "recipeVersionName",
    },
    {
      id: "status",
      header: i18n.tableHeaderStatus,
      cell: (e) => <ImageStatus status={e.status} />,
      width: "128px",
      sortingField: "status",
    },
    {
      id: "lastUpdateDate",
      header: i18n.tableHeaderImageLastUpdate,
      cell: (e) => <UserDate date={e.lastUpdateDate} />,
      width: "196px",
      sortingField: "lastUpdateDate",
    },
  ];

  const { items, actions, filterProps, collectionProps, paginationProps } = useCollection(
    images,
    {
      filtering: {
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
      sorting: { defaultState: { sortingColumn: columnDefinitions.find(x => x.id==='lastUpdateDate') || {}, isDescending: true } },
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
          <Button onClick={() => {
            navigateTo(RouteNames.Pipelines);
          }}
            variant='primary'
            data-test='create-image-btn'
          >
            {i18n.createButtonText}
          </Button>
        }
      >
        {i18n.navHeader}
      </Header>
    </>;
  }

  function getSelectedItem(): Image | undefined {
    if (collectionProps.selectedItems !== undefined &&
      collectionProps.selectedItems?.length >= ZERO_INDEX &&
      collectionProps.selectedItems[0] !== undefined) {
      return collectionProps.selectedItems[0]
    }
    return undefined;
  }

  function isItemSelected(predicate?: (vs: Image) => boolean) {
    return collectionProps.selectedItems !== undefined &&
      collectionProps.selectedItems?.length >= ZERO_INDEX &&
      collectionProps.selectedItems[0] !== undefined &&
      (!predicate || predicate(collectionProps.selectedItems[0]));
  }

  function renderContent() {
    return (
      <>
        <Table
          data-test="table-images"
          {...collectionProps}
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
            <TextFilter
              {...filterProps}
              filteringPlaceholder={i18n.findImagesPlaceholder}
              filteringAriaLabel={i18n.findImagesPlaceholder}
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
          <Box>
            <p>{i18n.infoPanelMessage2}</p>
            <ul>
              <li><b>{i18n.infoPanelPoint1}</b><br />{i18n.infoPanelPoint1Message}</li>
              <li><b>{i18n.infoPanelPoint2}</b><br />{i18n.infoPanelPoint2Message}</li>
            </ul>
          </Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }
};

export { Images };
