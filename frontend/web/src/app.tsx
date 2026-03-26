// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import './app.css';
import '@cloudscape-design/global-styles/index.css';
import { PageHeader } from './components/layout';
import { useProjectsSwitch } from './hooks/';
import { useAuthenticator } from './components/session-management/authenticator';
import { useUserProfile } from './components/user-preferences/user-profile.hook';
import { RouterAuth, RouterNoAuth } from './routes';
import { PageFooter } from './components/layout/page-footer/page-footer';
import { useBetaUserNotification } from './hooks';
import { useFeatureToggles } from './components/feature-toggles/feature-toggle.hook';
import { RouterDisabled } from './routes/router-disabled';
import { RouterLoading } from './routes/router-loading';
import { getApis } from './utils/api-helpers';

export const App = () => {
  const { user, initiateSignOut, initiateAuth } = useAuthenticator();
  const { featuresInitialised } = useFeatureToggles();
  const { loadingProjects, projectsInitialised } = useProjectsSwitch({});
  const { userProfileLoading, userProfileLoaded } = useUserProfile({ serviceAPIs: getApis() });

  useBetaUserNotification();

  return (
    <>
      {renderHeader()}
      {Boolean(user?.user) && authenticatedApp()}
      {!user?.user && unauthenticatedApp()}
      <PageFooter />
    </>
  );

  function renderHeader() {
    return <PageHeader
      onSignInClick={initiateAuth}
      onSignOutClick={initiateSignOut}
    />;
  }

  function unauthenticatedApp() {
    return <RouterNoAuth />;
  }

  function authenticatedApp() {
    if (appIsLoading()) {
      return <RouterLoading />;
    } else if (appIsReady()) {
      return <>
        <RouterAuth />
      </>;
    }
    return <RouterDisabled />;
  }

  function appIsLoading() {
    return appIsLoadingProjects() || appIsLoadingUserProfile() || appIsProcessingFeatureToggles();
  }

  function appIsLoadingProjects() {
    return loadingProjects && !projectsInitialised;
  }

  function appIsLoadingUserProfile() {
    return userProfileLoading && !userProfileLoaded;
  }

  function appIsProcessingFeatureToggles() {
    return !featuresInitialised;
  }

  function appIsReady() {
    return projectsInitialised && userProfileLoaded && featuresInitialised;
  }
};
