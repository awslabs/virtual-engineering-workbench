// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { FC, useEffect, useState } from 'react';
import { ButtonDropdownProps, TopNavigation, TopNavigationProps } from '@cloudscape-design/components';
import { loggedInUserState } from '../../session-management/logged-user';
import { useRecoilState } from 'recoil';
import { useLocation } from 'react-router-dom';

// global window

type Props = {
  onSignInClick: () => void,
  onSignOutClick: () => void,
};

const i18n = {
  appName: 'Virtual Engineering Workbench',
  menuDropDownPreferences: 'Preferences',
  menuDropDownHelp: 'Help',
  menuDropDownAdministration: 'Administration',
  menuDropDownSignOut: 'Sign out',
  projectDropDownNoProjectSelected: 'No project selected',
  projectDropDownFetching: 'Fetching projects...',
  projectDropDownPrograms: 'Programs',
  login: 'Login',
};

const BUTTON_TYPES = {
  SignOut: 'signout',
  Administration: 'administration',
  PreferencesSection: 'preferences-section',
  Preferences: 'preferences',
  Help: 'help',
};

/* eslint complexity: "off", @typescript-eslint/no-magic-numbers: "off" */
const pageHeader: FC<Props> = ({
  onSignInClick,
  onSignOutClick,
}) => {
  const [user] = useRecoilState(loggedInUserState);
  const location = useLocation();

  function handleProfileItemClick({ detail }: CustomEvent<ButtonDropdownProps.ItemClickDetails>) {
    if (detail.id === BUTTON_TYPES.SignOut) {
      onSignOutClick();
    }

  }

  const [menuItems, setMenuItems] = useState<TopNavigationProps.Utility[]>([]);

  useEffect(() => {
    const menuItemsList: TopNavigationProps.Utility[] = [];

    if (user?.user) {

      menuItemsList.push({
        type: 'menu-dropdown',
        text: user.user.firstName + ' ' + user.user.lastName,
        iconName: 'user-profile',
        onItemClick: handleProfileItemClick,
        description: user.user.userId,
        items: [
          { id: BUTTON_TYPES.Help, text: i18n.menuDropDownHelp },
          { id: BUTTON_TYPES.SignOut, text: i18n.menuDropDownSignOut },
        ]
      });

    } else {
      menuItemsList.push(
        {
          type: 'button',
          text: i18n.login,
          onClick: onSignInClick
        },
      );
    }

    setMenuItems(menuItemsList);
  }, [user, location.pathname]);

  return (
    <header id="h" style={{ position: 'sticky', top: 0, zIndex: 1002 }}>
      <TopNavigation
        identity={{
          href: '#',
          title: i18n.appName,
          logo: {
            src:
              'stell-logo-white.svg',
            alt: 'WorkbenchService'
          }
        }}
        utilities={menuItems}
        i18nStrings={{
          searchIconAriaLabel: 'Search',
          searchDismissIconAriaLabel: 'Close search',
          overflowMenuTriggerText: 'More',
          overflowMenuTitleText: 'All',
          overflowMenuBackIconAriaLabel: 'Back',
          overflowMenuDismissIconAriaLabel: 'Close menu'
        }}
      />
    </header>
  );
};

export { pageHeader as PageHeaderDisabled };
