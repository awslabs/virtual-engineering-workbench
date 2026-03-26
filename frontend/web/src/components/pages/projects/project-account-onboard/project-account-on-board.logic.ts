import { useEffect, useState } from 'react';
import { useUserProfile } from '../../../user-preferences/user-profile.hook';
import { projectsAPI } from '../../../../services';
import { extractErrorResponseMessage, getApis } from '../../../../utils/api-helpers';
import { useNotifications } from '../../../layout';
import { useLocation, useNavigate } from 'react-router-dom';
import { useTechnologies } from '../../technologies/technologies.logic';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';

type ProjectAccountOnboardingProps = {
  projectId: string,
};


const useProjectAccountOnboarding = ({ projectId }: ProjectAccountOnboardingProps) => {
  const { userProfile, userProfileLoading } = useUserProfile({ serviceAPIs: getApis() });
  const { state } = useLocation();
  const DEFAULT_PAGE_SIZE = 50;

  const [accountName, setAccountName] = useState<string>('');
  const [accountType, setAccountType] = useState<string>('USER');
  const [awsAccountId, setAWSAccountId] = useState<string>('');
  const [accountDescription, setAccountDescription] = useState<string>('');
  const [accountOnboardingInProgress, setAccountOnboardingInProgress] = useState(false);
  const [onboardSuccess, setOnboardSuccess] = useState(false);
  const [stage, setStage] = useState('');
  const [technologyId, setTechnologyId] = useState('');
  const [region, setRegion] = useState<string>();
  const navigate = useNavigate();
  const { getPathFor } = useNavigationPaths();

  const { showErrorNotification, showSuccessNotification } = useNotifications();

  useEffect(() => {
    setRegion(userProfile.preferredRegion);
  }, [userProfile]);

  useEffect(() => {
    if (state && state.technologyId) {
      setTechnologyId(state.technologyId);
    }
  }, [state]);

  const {
    technologies,
    isLoadingTechnologies,
  } = useTechnologies({ projectId: projectId, pageSize: DEFAULT_PAGE_SIZE.toString() });

  return {
    accountName,
    setAccountName,
    accountType,
    setAccountType,
    awsAccountId,
    setAWSAccountId,
    accountDescription,
    setAccountDescription,
    isFormValid,
    accountOnboardingInProgress,
    onboardSuccess,
    onboardAccount,
    stage,
    setStage,
    technologyId,
    setTechnologyId,
    region,
    setRegion,
    enabledRegions: userProfile.enabledRegions,
    enabledRegionsLoading: userProfileLoading,
    technologies,
    isLoadingTechnologies,
  };


  function isFormValid() {
    return hasMandatoryFreeTextFields() && hasMandatoryChoiceFields();
  }

  function hasMandatoryFreeTextFields() {
    return !!accountName && !!accountDescription && !!awsAccountId;
  }

  function hasMandatoryChoiceFields() {
    return !!accountType && !!stage && !!region && !!technologyId;
  }

  function onboardAccount() {
    if (!isFormValid() || !region) {
      return;
    }

    setAccountOnboardingInProgress(true);

    projectsAPI.onboardProjectAccount(projectId, {
      awsAccountId,
      accountType,
      accountName,
      accountDescription,
      stage,
      technologyId,
      region
    }).then(() => {
      showSuccessNotification({
        header: 'Success!',
        content: 'Account onboarding started successfully.'
      });
      setOnboardSuccess(true);
      navigate(`${getPathFor(RouteNames.Technologies)}/${technologyId}`, {
        state: {
          technologyId: technologyId
        }
      });
    }).catch(async e => {
      showErrorNotification({
        header: 'Unable to start account onboarding',
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setAccountOnboardingInProgress(false);
    });
  }
};

export { useProjectAccountOnboarding };