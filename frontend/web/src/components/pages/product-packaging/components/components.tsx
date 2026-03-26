/* eslint-disable */
import {
  Box,
  Button,
  ButtonDropdown,
  ButtonDropdownProps,
  Header,
  HelpPanel,
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
import { useComponents } from "./components.logic";
import { i18n } from "./components.translations";
import { useNavigationPaths } from "../../../layout/navigation/navigation-paths.logic";
import { RouteNames } from "../../../layout/navigation/navigation.static";
import {
  Component,
  GetComponentResponse,
} from "../../../../services/API/proserve-wb-packaging-api";
import { extractErrorResponseMessage } from "../../../../utils/api-helpers";
import { ComponentShareModal } from "./component-share-modal/page";
import { useRecoilValue } from "recoil";
import { selectedProjectState } from "../../../../state";
import { ArchiveComponentModal } from "../shared/archive-version-modal";
import { ComponentStatus } from "./components-status";
import { useCloudscapeTablePersisentState } from "../../../../hooks";

const PAGE_SIZE = 20;
const PAGE_INDEX = 1;
const ZERO_INDEX = 0;

interface ServiceAPI {
  archiveComponent: (
    projectId: string,
    componentId: string,
  ) => Promise<Object>;
  getComponent: (
    projectId: string,
    componentId: string,
  ) => Promise<GetComponentResponse>;
  shareComponent: (
    projectId: string,
    componentId: string,
    projectIds: string[],
  ) => Promise<Object>;
}

interface ComponentsProps {
  serviceApi: ServiceAPI;
  projectId?: string;
}

const Components: FC<ComponentsProps> = ({ serviceApi }) => {
  const selectedProject = useRecoilValue(selectedProjectState);
  const [archivingIsLoading, setArchivingIsLoading] = useState(false);
  const [archivePromptVisible, setArchivePromptVisible] = useState(false);
  const [sharingIsLoading, setSharingIsLoading] = useState(false);
  const [sharePromptVisible, setSharePromptVisible] = useState(false);
  const [associatedProjectIds, setAssociatedProjectIds] = useState<string[]>([]);
  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const [selectedComponentId, setSelectedComponentId] = useState<string>();
  const [selectedComponentName, setSelectedComponentName] = useState<string>();
  const {
    components,
    loadComponents,
    isLoading,
    setStatus,
    status,
    statusFirstOption,
    statusOptions,
  } = useComponents();
  const { navigateTo } = useNavigationPaths();
  const columnDefinitions: TableProps.ColumnDefinition<Component>[] = [
    {
      id: "componentName",
      header: i18n.tableHeaderComponentName,
      cell: (e) => e.componentName,
      sortingField: "componentName",
    },
    {
      id: "componentDescription",
      header: i18n.tableHeaderComponentDescription,
      cell: (e) => e.componentDescription,
    },
    {
      id: "componentPlatform",
      header: i18n.tableHeaderComponentPlatform,
      cell: (e) => e.componentPlatform,
      sortingField: "componentPlatform",
    },
    {
      id: "status",
      header: i18n.tableHeaderStatus,
      cell: (e) => <ComponentStatus status={e.status} />,
      sortingField: "status",
    },
    {
      id: "lastUpdateDate",
      header: i18n.tableHeaderComponentLastUpdate,
      cell: (e) => <UserDate date={e.lastUpdateDate} />,
      sortingField: "lastUpdateDate",
    },
  ];

  useEffect(() => {
    if (selectedComponentId && selectedProject.projectId) {
      setSharingIsLoading(true);
      serviceApi
        .getComponent(selectedProject.projectId, selectedComponentId)
        .then((apiRes) => {
          const ids =
            apiRes.metadata?.associatedProjects.map((ap) => ap.projectId) || [];
          setAssociatedProjectIds(ids);
        }).finally(() => {
          setSharingIsLoading(false)
        });
    }
  }, [selectedComponentId]);

  const { items, actions, filterProps, collectionProps, paginationProps } =
    useCollection(components, {
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

  const { onSortingChange } = useCloudscapeTablePersisentState<Component>({
    key: 'prod-man-component', 
    columnDefinitions,
    setSorting: actions.setSorting,
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
      <ArchiveComponentModal
        componentName={selectedComponentName || ""}
        onClose={() => setArchivePromptVisible(false)}
        isOpen={archivePromptVisible}
        onConfirm={archiveConfirmHandler}
        isLoading={archivingIsLoading}
      />
      <ComponentShareModal
        somethingIsPending={sharingIsLoading}
        sharePromptVisible={sharePromptVisible}
        setSharePromptVisible={setSharePromptVisible}
        associatedProjectIds={associatedProjectIds}
        shareConfirmHandler={shareConfirmHandler}
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
                navigateTo(RouteNames.CreateComponent);
              }}
              variant="primary"
              data-test="create-component-btn"
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
      setSelectedComponentName(e.detail.selectedItems[0].componentName);
      setSelectedComponentId(e.detail.selectedItems[0].componentId);
    }
  }

  function renderContent() {
    return (
      <>
        <Table
          onSelectionChange={() => selectionChanged}
          data-test="table-components"
          {...collectionProps}
          onSortingChange={onSortingChange}
          header={
            <Header
              variant="h2"
              counter={`(${components.length})`}
              actions={
                <SpaceBetween direction="horizontal" size="m">
                  <Button
                    data-test="button-refresh-table"
                    iconName="refresh"
                    onClick={loadComponents}
                    loading={isLoading}
                  />
                  <Button
                    data-test="button-view-component"
                    disabled={!isItemSelected()}
                    onClick={viewSelectedItem}
                  >
                    {i18n.buttonViewComponent}
                  </Button>
                  <ButtonDropdown
                    data-test="actions-dropdown"
                    onItemClick={handleDropdownClick}
                    disabled={preventAnyAction()}
                    loading={archivingIsLoading && sharingIsLoading}
                    items={[
                      {
                        text: i18n.componentArchive,
                        id: "archive",
                      },
                      {
                        text: i18n.componentShare,
                        id: "share",
                      },
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
          loading={isLoading}
          items={items}
          selectionType="single"
          trackBy="componentId"
          empty={
            <EmptyGridNotification
              title={i18n.emptyComponents}
              subTitle={i18n.emptyComponentsSubTitle}
              actionButtonText={i18n.emptyComponentsResolve}
              actionButtonOnClick={emptyComponentsResolveAction}
            />
          }
          filter={
            <SpaceBetween size="m" direction="horizontal">
              <TextFilter
                {...filterProps}
                filteringPlaceholder={i18n.findComponentsPlaceholder}
                filteringAriaLabel={i18n.findComponentsPlaceholder}
              />
              <Select
                options={statusOptions}
                selectedOption={status!}
                onChange={event => {
                  setStatus(event.detail.selectedOption);
                }}
                data-test="component-status-select"
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

  function emptyComponentsResolveAction() {
    navigateTo(RouteNames.CreateComponent);
  }

  function isItemSelected(predicate?: (vs: Component) => boolean) {
    return (
      collectionProps.selectedItems !== undefined &&
      collectionProps.selectedItems?.length >= ZERO_INDEX &&
      collectionProps.selectedItems[0] !== undefined &&
      (!predicate || predicate(collectionProps.selectedItems[0]))
    );
  }

  function getSelectedItem(): Component | undefined {
    if (
      collectionProps.selectedItems !== undefined &&
      collectionProps.selectedItems?.length >= ZERO_INDEX &&
      collectionProps.selectedItems[0] !== undefined
    ) {
      return collectionProps.selectedItems[0];
    }
    return undefined;
  }

  function viewSelectedItem() {
    const selectedItem = getSelectedItem();
    if (!!selectedItem) {
      navigateTo(RouteNames.ViewComponent, {
        ":componentId": selectedItem.componentId,
      });
    }
  }

  function preventAnyAction() {
    // add status to component entity! also for table column
    return !isItemSelected() || isItemSelected(vs => vs.status === "ARCHIVED");
    // || isItemSelected(vs => vs.status === "PROCESSING")
  }

  function archiveConfirmHandler() {
    if (selectedComponentId && selectedProject.projectId) {
      setArchivingIsLoading(true);
      serviceApi
        .archiveComponent(selectedProject.projectId, selectedComponentId)
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

  function shareConfirmHandler(values: string[]) {
    if (selectedComponentId && selectedProject.projectId) {
      setSharingIsLoading(true);
      serviceApi
        .shareComponent(selectedProject.projectId, selectedComponentId, values)
        .then(() => {
          showSuccessNotification({
            header: i18n.createSuccessMessageHeader,
            content: i18n.createShareSuccessMessageContent(values),
          });
        })
        .catch(async (e) => {
          showErrorNotification({
            header: i18n.createFailMessageHeader,
            content: await extractErrorResponseMessage(e),
          });
        })
        .finally(() => {
          setSharingIsLoading(false);
          setSharePromptVisible(false);
        });
    }
  }

  function handleDropdownClick({
    detail,
  }: CustomEvent<ButtonDropdownProps.ItemClickDetails>) {
    if (detail.id === "archive") {
      setArchivePromptVisible(true);
    }
    if (detail.id === "share") {
      setSharePromptVisible(true);
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

export { Components };
