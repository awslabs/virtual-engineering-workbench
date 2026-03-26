// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { FC, useEffect, useState } from 'react';
import {
  ButtonDropdownProps,
} from '@cloudscape-design/components';
import { RoleBasedFeature } from '../../../state/';
import { loggedUser, UserType } from '../../session-management/logged-user';
import { useRecoilValue } from 'recoil';
import { useLocalStorage, useProjectsSwitch } from '../../../hooks';
import { useRoleAccessToggle } from '../../../hooks/role-access-toggle';
import { useLocation } from 'react-router-dom';
import { UserPreferences } from '../../user-preferences';
import { useNavigationPaths } from '../navigation/navigation-paths.logic';
import {
  RouteNames,
  ROUTE_REGULAR_EXPRESSIONS,
} from '../navigation/navigation.static';
import './page-header.scss';
import { AppConfig } from '../../../utils/app-config';
import { getHomePage } from '../../../routes';
import { applyMode, Mode } from '@cloudscape-design/global-styles';
import CustomTopNavigation, {
  CustomUtility,
} from './cutom-top-navigation/custom-top-navigation';
import { THEME } from '../../../constants';

type Props = {
  onSignInClick: () => void,
  onSignOutClick: () => void,
};

const i18n = {
  appName: 'Virtual Engineering Workbench',
  menuDropDownPreferences: 'Preferences',
  menuDropDownSignOut: 'Sign out',
  projectDropDownNoProjectSelected: 'No program selected',
  projectDropDownFetching: 'Fetching programs...',
  projectDropDownPrograms: 'Programs',
  login: 'Login',
  notifications: 'Notifications',
};

const BUTTON_TYPES = {
  SignOut: 'signout',
  PreferencesSection: 'preferences-section',
  Preferences: 'preferences',
};

/* eslint complexity: "off", @typescript-eslint/no-magic-numbers: "off" */
/* eslint @typescript-eslint/no-unused-vars: "off" */
export const PageHeader: FC<Props> = ({ onSignInClick, onSignOutClick }) => {
  const user = useRecoilValue(loggedUser);
  const { navigateTo } = useNavigationPaths();
  const location = useLocation();
  const { userProjects, selectedProject, switchToProject, loadingProjects } =
    useProjectsSwitch({ skipFetch: true });
  const [preferencesVisible, setPreferencesVisible] = useState(false);
  const isFeatureAccessible = useRoleAccessToggle();
  const [menuItems, setMenuItems] = useState<CustomUtility[]>([]);
  const themeName = useLocalStorage(THEME)[0];
  const activePrograms = userProjects.filter(program => {
    return program.isActive === true;
  });
  const [envrionmenName, setEnvrionmenName] = useState('prod');

  function handleTopRightInfo(user: UserType) {
    if (user.firstName && user.lastName) {
      return user.firstName + ' ' + user.lastName;
    }
    return user.userName;
  }

  useEffect(() => {
    applyMode(themeName as Mode);
  }, []);

  useEffect(() => {
    function inProgramsScreen() {
      return (
        new RegExp(ROUTE_REGULAR_EXPRESSIONS.programs, 'giu').test(
          location.pathname
        ) ||
        new RegExp(ROUTE_REGULAR_EXPRESSIONS.createProgram, 'giu').test(
          location.pathname
        )
      );
    }

    function handleProfileItemClick({
      detail,
    }: CustomEvent<ButtonDropdownProps.ItemClickDetails>) {
      if (detail.id === BUTTON_TYPES.SignOut) {
        onSignOutClick();
      }
      if (detail.id === BUTTON_TYPES.Preferences) {
        setPreferencesVisible(true);
      }
    }

    const programsToDisplay = () => {
      if (isFeatureAccessible(RoleBasedFeature.ShowInactivePrograms)) {
        return userProjects;
      }
      return activePrograms;
    };

    function handleProjectChangeClick({
      detail,
    }: CustomEvent<ButtonDropdownProps.ItemClickDetails>) {
      if (detail.id.startsWith('project-')) {
        navigateTo(getHomePage());
        switchToProject(detail.id.substring(8));
      }

      if (detail.id === 'programs') {
        navigateTo(RouteNames.Programs);
      }
    }

    const menuCustomItemsList: CustomUtility[] = [];
    setEnvrionmenName(AppConfig.Environment);

    if (user) {
      let dropdownText = i18n.projectDropDownNoProjectSelected;

      if (loadingProjects) {
        dropdownText = i18n.projectDropDownFetching;
      } else if (selectedProject.projectName) {
        dropdownText = selectedProject.projectName;
      }

      if (inProgramsScreen()) {
        dropdownText = i18n.projectDropDownPrograms;
      }

      menuCustomItemsList.push({
        type: 'menu-dropdown',
        text: dropdownText,
        onItemClick: handleProjectChangeClick,
        dataTest: 'custom-drop-down-program',
        items: [
          {
            id: 'programs-menu',
            items: [{ id: 'programs', text: i18n.projectDropDownPrograms }],
          },
          ...programsToDisplay().map((p) => ({
            id: `project-${p.id}`,
            text: p.name,
            disabled: p.id === selectedProject.projectId && !inProgramsScreen(),
          })),
        ],
      });

      const displayDescription = (): string => {
        if (selectedProject.roles) {
          return user.userId + ' (' + selectedProject.roles[0] + ')';
        }
        return user.userId;
      };

      menuCustomItemsList.push({
        type: 'menu-dropdown',
        text: handleTopRightInfo(user),
        iconName: 'user-profile',
        onItemClick: handleProfileItemClick,
        description: displayDescription(),
        dataTest: 'custom-drop-down-user-profile',
        items: [
          ...isFeatureAccessible(RoleBasedFeature.GetUserProfile)
            ? [
              {
                id: BUTTON_TYPES.Preferences,
                text: i18n.menuDropDownPreferences,
              },
            ]
            : [],
          { id: BUTTON_TYPES.SignOut, text: i18n.menuDropDownSignOut },
        ],
      });
    } else {
      menuCustomItemsList.push({
        type: 'button',
        text: i18n.login,
        dataTest: 'custom-drop-down-signin',
        onClick: onSignInClick,
      });
    }
    setMenuItems(menuCustomItemsList);
  }, [
    user,
    userProjects,
    selectedProject,
    loadingProjects,
    location.pathname,
  ]);

  return (
    <header id="h" style={{ position: 'sticky', top: 0, zIndex: 1002 }}>
      <CustomTopNavigation
        utilities={menuItems}
        envrionmenName={envrionmenName}
        identity={{
          hrefRoute: getHomePage(),
          logo: {
            src:
            '/AWS_logo_RGB_WHT.png',
            alt: 'WorkbenchService'
          },
        }}
      ></CustomTopNavigation>
      <UserPreferences
        visible={preferencesVisible}
        onDismiss={() => setPreferencesVisible(false)}
        onConfirmSuccess={() => setPreferencesVisible(false)}
      />
    </header>
  );
};
