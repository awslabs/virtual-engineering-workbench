/* eslint-disable */
import {
  Box,
  Button,
  ButtonDropdown,
  ButtonDropdownProps,
  Header,
  HelpPanel,
  Link,
  Pagination,
  Select,
  SpaceBetween,
  Table,
  TableProps,
  TextFilter,
} from "@cloudscape-design/components";
import { useCollection } from "@cloudscape-design/collection-hooks";
import { FC, useEffect, useState } from "react";
import { BreadcrumbItem, useNotifications } from "../../../layout";
import { WorkbenchAppLayout } from "../../../layout/workbench-app-layout/workbench-app-layout";
import {
  UserDate,
  EmptyGridNotification,
  NoMatchTableNotification,
} from "../../shared";
import { useRecipes } from './recipes.logic';
import { i18n } from './recipes.translations';
import { useNavigationPaths } from "../../../layout/navigation/navigation-paths.logic";
import { RouteNames } from "../../../layout/navigation/navigation.static";
import {
    Recipe,
    GetRecipeResponse
} from "../../../../services/API/proserve-wb-packaging-api";
import { extractErrorResponseMessage } from "../../../../utils/api-helpers";
import { useRecoilValue } from "recoil";
import { selectedProjectState } from "../../../../state";
import { ArchiveRecipeModal } from '../shared/archive-version-modal';
import { RecipeStatus } from './recipes-status';

const PAGE_SIZE = 20;
const PAGE_INDEX = 1;
const ZERO_INDEX = 0;

interface ServiceAPI {
  archiveRecipe: (
    projectId: string,
    recipeId: string,
  ) => Promise<Object>;
  getRecipe: (
    projectId: string,
    recipeId: string,
  ) => Promise<GetRecipeResponse>;
}


interface RecipesProps {
  serviceApi: ServiceAPI;
  projectId?: string;
}

const Recipes: FC<RecipesProps> = ({ serviceApi }) => {
  const selectedProject = useRecoilValue(selectedProjectState);
  const [archivingIsLoading, setArchivingIsLoading] = useState(false);
  const [archivePromptVisible, setArchivePromptVisible] = useState(false);
  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const [selectedRecipeId, setSelectedRecipeId] = useState<string>();
  const [selectedRecipeName, setSelectedRecipeName] = useState<string>();
  const [selectedRecipeStatus, setSelectedRecipeStatus] = useState<string>();
  const {
    recipes,
    loadRecipes,
    isLoading,
    setStatus,
    status,
    statusFirstOption,
    statusOptions
  } = useRecipes();
  const { navigateTo } = useNavigationPaths();

  const columnDefinitions: TableProps.ColumnDefinition<Recipe>[] = [
    {
      id: 'recipeName',
      header: i18n.tableHeaderRecipeName,
      cell: (e) => {
        return <div>
          <Link onFollow={() => {
            navigateTo(RouteNames.ViewRecipe, { 
              ':recipeId': e.recipeId,
            })
          }}>{e.recipeName}</Link>
        </div>;
      }
    },
    {
      id: 'recipeDescription',
      header: i18n.tableHeaderRecipeDescription,
      cell: e => e.recipeDescription,
    },
    {
      id: 'recipePlatform',
      header: i18n.tableHeaderRecipePlatform,
      cell: e => e.recipePlatform,
    },
    {
      id: "status",
      header: i18n.tableHeaderStatus,
      cell: (e) => <RecipeStatus status={e.status} />,
    },
    {
      id: 'lastUpdateDate',
      header: i18n.tableHeaderRecipeLastUpdate,
      cell: e => <UserDate date={e.lastUpdateDate} />,
      sortingField: 'lastUpdateDate'
    },
  ];

  useEffect(() => {
    if (selectedRecipeId && selectedProject.projectId) {
      serviceApi.getRecipe(selectedProject.projectId, selectedRecipeId)
    }
  }, [selectedRecipeId, selectedRecipeStatus])

  const { items, actions, filterProps, collectionProps, paginationProps } =
    useCollection(recipes, {
      filtering: {
        empty: (
          <NoMatchTableNotification
            title={i18n.tableFilterNoResultTitle}
            buttonAction={() => clearFilters()}
            buttonText={i18n.tableFilterNoResultActionText}
            subtitle={i18n.tableFilterNoResultSubtitle}
          />
        ),
        noMatch: (
          <NoMatchTableNotification
            title={i18n.tableFilterNoResultTitle}
            buttonAction={() => clearFilters()}
            buttonText={i18n.tableFilterNoResultActionText}
            subtitle={i18n.tableFilterNoResultSubtitle}
          />
        ),
      },
      selection: {},
      sorting: {
        defaultState: {
          sortingColumn: columnDefinitions[3],
          isDescending: true,
        },
      },
      pagination: { defaultPage: PAGE_INDEX, pageSize: PAGE_SIZE },
    });
  const defaultFunc = collectionProps.onSelectionChange;
  collectionProps.onSelectionChange = selectionChanged;

  return (
    <>
      <WorkbenchAppLayout
        breadcrumbItems={getBreadcrumbItems()}
        content={renderContent()}
        contentType="default"
        tools={renderTools()}
        customHeader={renderHeader()}
      />
      <ArchiveRecipeModal
          recipeName={selectedRecipeName || ""}
          onClose={() => setArchivePromptVisible(false)}
          isOpen={archivePromptVisible}
          onConfirm={archiveConfirmHandler}
          isLoading={archivingIsLoading}
      />
    </>
  );

  function getBreadcrumbItems(): BreadcrumbItem[] {
    return [{ path: i18n.breadcrumbLevel1, href: "#" }];
  }

  function renderHeader() {
    return (
      <>
        <Header
          variant="h1"
          description={i18n.navHeaderDescription}
          actions={
            <Button
              onClick={() => {
                navigateTo(RouteNames.CreateRecipe);
              }}
              variant="primary"
              data-test="create-recipe-btn"
            >
              {i18n.createButtonText}
            </Button>
          }
        >
          {i18n.navHeader}
        </Header>
      </>
    );
  }

  function selectionChanged(e: any) {
    if (defaultFunc) {
      defaultFunc(e);
    }
    if (e.detail.selectedItems) {
      setSelectedRecipeName(e.detail.selectedItems[0].recipeName);
      setSelectedRecipeId(e.detail.selectedItems[0].recipeId);
      setSelectedRecipeStatus(e.detail.selectedItems[0].status);
    }
  }


  function renderContent() {
    return (
      <>
        <Table
          onSelectionChange={() => selectionChanged}
          data-test="table-recipes"
          {...collectionProps}
          header={
            <Header
              variant="h2"
              counter={`(${recipes.length})`}
              actions={
                <SpaceBetween direction="horizontal" size="m">
                  <Button
                    data-test="button-refresh-table"
                    iconName="refresh"
                    onClick={loadRecipes}
                    loading={isLoading}
                  />
                  <Button
                    data-test="button-view-recipe"
                    disabled={!isItemSelected()}
                    onClick={viewSelectedItem}
                  >
                    {i18n.buttonViewRecipe}
                  </Button>
                  <ButtonDropdown
                    data-test="actions-dropdown"
                    onItemClick={handleDropdownClick}
                    disabled={preventAnyAction()}
                    loading={archivingIsLoading}
                    items={[
                      {
                        text: i18n.recipeArchive,
                        id: "archive",
                      }
                    ]}
                  >
                    {i18n.buttonActions}
                  </ButtonDropdown>
                </SpaceBetween>
              }
            >
              {i18n.tableHeader}
            </Header>
          }
          columnDisplay={
            [
              { id: "recipeName", visible: true },
              { id: "recipeDescription", visible: true },
              { id: "recipePlatform", visible: true },
              { id: "status", visible: true },
              { id: "lastUpdateDate", visible: true },
            ]
          }
          loading={isLoading}
          items={items}
          selectionType="single"
          trackBy="recipeId"
          empty={
            <EmptyGridNotification
              title={i18n.emptyRecipes}
              subTitle={i18n.emptyRecipesSubTitle}
              actionButtonText={i18n.emptyRecipesResolve}
              actionButtonOnClick={emptyRecipesResolveAction}
            />
          }
          filter={
            <SpaceBetween size="m" direction="horizontal">
              <TextFilter
                {...filterProps}
                filteringPlaceholder={i18n.findRecipesPlaceholder}
                filteringAriaLabel={i18n.findRecipesPlaceholder}
              />
              <Select
                options={statusOptions}
                selectedOption={status!}
                onChange={event => {
                  setStatus(event.detail.selectedOption);
                }}
                data-test="recipe-status-select"
              />
            </SpaceBetween>
          }
          pagination={<Pagination {...paginationProps} />}
          columnDefinitions={columnDefinitions}
        />
      </>
    );
  }

  function clearFilters() {
    actions.setFiltering("");
    setStatus(statusFirstOption);
  }

  function emptyRecipesResolveAction() {
    navigateTo(RouteNames.CreateRecipe);
  }

  function isItemSelected(predicate?: (vs: Recipe) => boolean) {
    return (
      collectionProps.selectedItems !== undefined &&
      collectionProps.selectedItems?.length >= ZERO_INDEX &&
      collectionProps.selectedItems[0] !== undefined &&
      (!predicate || predicate(collectionProps.selectedItems[0]))
    );
  }

  function getSelectedItem(): Recipe | undefined {
    if (collectionProps.selectedItems !== undefined &&
      collectionProps.selectedItems?.length >= ZERO_INDEX &&
      collectionProps.selectedItems[0] !== undefined) {
      return collectionProps.selectedItems[0]
    }
    return undefined;
  }

  function viewSelectedItem() {
    const selectedItem = getSelectedItem();
    if (!!selectedItem) {
      navigateTo(RouteNames.ViewRecipe, { 
        ':recipeId': selectedItem.recipeId,
      })
    }
  }

  function preventAnyAction() {
    // add status to recipe entity! also for table column
    return !isItemSelected() || isItemSelected(vs => vs.status === "ARCHIVED");
    // || isItemSelected(vs => vs.status === "PROCESSING")
  }

  function archiveConfirmHandler() {
    if (selectedRecipeId && selectedProject.projectId) {
      setArchivingIsLoading(true);
      serviceApi
        .archiveRecipe(selectedProject.projectId, selectedRecipeId)
        .then(() => {
          showSuccessNotification({
            header: i18n.createSuccessMessageHeader,
            content: i18n.createArchiveSuccessMessageContent,
          });
        })
        .catch(async (e) => {
          showErrorNotification({
            header: i18n.createFailMessageHeader,
            content: await extractErrorResponseMessage(e),
          });
        })
        .finally(() => {
          setArchivingIsLoading(false);
          setArchivePromptVisible(false);
        });
    }
  }

  function handleDropdownClick({
    detail,
  }: CustomEvent<ButtonDropdownProps.ItemClickDetails>) {
    if (detail.id === "archive") {
      setArchivePromptVisible(true);
    }
  }

  function renderTools() {
    return (
      <HelpPanel header={<h2>{i18n.infoPanelHeader}</h2>}>
        <SpaceBetween size={"s"}>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel1}</Box>
          <Box variant="p">{i18n.infoPanelMessage1}</Box>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel2}</Box>
          <Box variant="p">{i18n.infoPanelMessage2}</Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }
};

export { Recipes };
