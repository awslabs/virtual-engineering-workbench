// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { FC, ReactNode } from 'react';
import {
  AppLayout,
  AppLayoutProps,
  Box,
  Header,
  SplitPanel,
  ContentLayout,
  NonCancelableCustomEvent
} from '@cloudscape-design/components';
import { Navigation } from '../navigation/navigation.tsx';
import { loggedUser } from '../../session-management/logged-user';
import { useRecoilValue } from 'recoil';
import { Breadcrumb, BreadcrumbItem } from '../breadcrumb/breadcrumb';
import { Notifications } from '../notifications';
import { useSplitPanel } from '../../../hooks';

const SPLIT_PANEL_I18N_STRINGS = {
  preferencesTitle: 'Split panel preferences',
  preferencesPositionLabel: 'Split panel position',
  preferencesPositionDescription: 'Choose the default split panel position for the service.',
  preferencesPositionSide: 'Side',
  preferencesPositionBottom: 'Bottom',
  preferencesConfirm: 'Confirm',
  preferencesCancel: 'Cancel',
  closeButtonAriaLabel: 'Close panel',
  openButtonAriaLabel: 'Open panel',
  resizeHandleAriaLabel: 'Resize split panel'
};

const TOOL_WIDTH = 290;

type WorkbenchLayoutProps<T> = {
  breadcrumbItems: BreadcrumbItem[],
  contentType?: AppLayoutProps.ContentType,
  tools?: ReactNode,
  content?: ReactNode,
  customHeader?: ReactNode,
  headerText?: string,
  headerSubText?: string,
  splitPanel?: ReactNode,
  splitPanelHeader?: string,
  splitPanelItemsForOpen?: T[],
  splitPanelClosed?: () => void,
  toolsHide?: boolean,
  navigationHide?: boolean,
  toolsOpen?: boolean,
  onToolsChange?: (event: NonCancelableCustomEvent<AppLayoutProps.ChangeDetail>) => void,
  toolsWidth?: number,
};

export const WorkbenchAppLayout: FC<WorkbenchLayoutProps<unknown>> = ({
  breadcrumbItems,
  contentType,
  tools,
  content,
  headerText,
  customHeader,
  headerSubText,
  splitPanel,
  splitPanelHeader,
  splitPanelItemsForOpen,
  splitPanelClosed,
  toolsHide,
  navigationHide,
  toolsOpen,
  onToolsChange,
  toolsWidth = TOOL_WIDTH,
}) => {
  const loggedInUser = useRecoilValue(loggedUser);
  const { splitPanelOpen, onSplitPanelToggle, splitPanelSize, onSplitPanelResize } = useSplitPanel(
    splitPanelItemsForOpen || [],
    splitPanelClosed,
  );

  return <>
    {renderAppLayout()}
  </>;

  function renderAppLayout() {
    return <AppLayout
      navigation={ <Navigation user={ loggedInUser } /> }
      breadcrumbs={renderBreadcrumb()}
      content={renderContent()}
      contentType={contentType}
      tools={tools}
      notifications={<Notifications />}
      headerSelector='#h'
      footerSelector='#f'
      splitPanel={splitPanelOpen &&
        <SplitPanel header={splitPanelHeader || ''} i18nStrings={SPLIT_PANEL_I18N_STRINGS}>
          {splitPanel}
        </SplitPanel>
      }
      splitPanelOpen={splitPanelOpen}
      onSplitPanelToggle={onSplitPanelToggle}
      splitPanelSize={splitPanelSize}
      onSplitPanelResize={onSplitPanelResize}
      stickyNotifications={true}
      toolsHide={toolsHide}
      navigationHide={navigationHide}
      toolsOpen={toolsOpen}
      onToolsChange={onToolsChange}
      maxContentWidth={Number.MAX_VALUE}
      toolsWidth={toolsWidth}
    />;
  }

  function renderBreadcrumb() {
    return <Breadcrumb items={breadcrumbItems} />;
  }

  function hasAnyHeaderElement() {
    return hasCustomHeader() || hasHeaderText();
  }

  function hasCustomHeader() {
    return !!customHeader;
  }

  function hasHeaderText() {
    return !!headerText || !!headerSubText;
  }

  function renderHeader() {
    if (hasCustomHeader()) {
      return customHeader;
    }
    return <>
      {!!headerText && <Header
        variant='awsui-h1-sticky'
      >
        {headerText}
      </Header>}
      {!!headerSubText &&
        <Box variant="p" color="text-label" margin={{ bottom: 'l' }}>
          {headerSubText}
        </Box>
      }
    </>;
  }

  function renderContent() {
    if (hasAnyHeaderElement()) {
      return <ContentLayout header={renderHeader()}>
        {content}
      </ContentLayout>;
    }
    return content;
  }
};
