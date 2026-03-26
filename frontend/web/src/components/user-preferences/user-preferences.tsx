import {
  Box,
  Button,
  Modal,
  RadioGroupProps,
  SpaceBetween,
  Spinner,
  Tabs,
  TabsProps
} from '@cloudscape-design/components';
import { FC, useCallback, useEffect, useMemo, useState } from 'react';
import { useUserProfile } from './user-profile.hook';
import {
  EnabledRegion,
  REGION_DESCRIPTIONS,
  REGION_NAMES
} from './user-preferences.static';
import { RoleBasedFeature } from '../../state';
import { RoleAccessToggle } from '../pages/shared/role-access-toggle';
import { i18n } from './user-preferences.translations';
import { UserPreferencesGeneral } from './user-preferences-general';
import { UserPreferencesMaintenanceWindow } from './user-preferences-maintenance-window';
import { getApis } from '../../utils/api-helpers.ts';

type Props = {
  visible: boolean,
  onDismiss?: () => void,
  onConfirmSuccess?: () => void,
};

export const UserPreferences: FC<Props> = ({
  visible,
  onDismiss,
  onConfirmSuccess,
}) => {
  const { userProfile, userProfileLoading, updateUserProfile } = useUserProfile({ serviceAPIs: getApis() });
  const [preferredRegion, setPreferredRegion] = useState(userProfile.preferredRegion);
  const [preferredNetwork, setPreferredNetwork] = useState(userProfile.preferredNetwork);
  const [preferredMaintenanceWindows, setPreferredMaintenanceWindows]
    = useState(userProfile.preferredMaintenanceWindows);


  useEffect(() => {
    setPreferredRegion(userProfile.preferredRegion);
    setPreferredNetwork(userProfile.preferredNetwork);
    setPreferredMaintenanceWindows(userProfile.preferredMaintenanceWindows);
  }, [userProfile]);

  const enabledRegions: RadioGroupProps.RadioButtonDefinition[] = useMemo(() => {
    return userProfile.
      enabledRegions.map(r => ({
        value: r,
        label: REGION_NAMES[r as EnabledRegion] || r,
        description: REGION_DESCRIPTIONS[r as EnabledRegion] || '',
      } as RadioGroupProps.RadioButtonDefinition));
  }, [userProfile]);

  const enabledNetworks: RadioGroupProps.RadioButtonDefinition[] = useMemo(() => {
    return userProfile.
      enabledNetworks.map(r => ({
        value: r,
        label: i18n.preferenceNetworkLabel(r),
        description: i18n.preferenceNetworkDescription(r),
      } as RadioGroupProps.RadioButtonDefinition));
  }, [userProfile]);

  const onConfirm = useCallback(() => {
    updateUserProfile(
      preferredRegion, preferredNetwork, preferredMaintenanceWindows
    ).then(() => {
      onConfirmSuccess?.();
    });
  }, [
    updateUserProfile,
    preferredRegion,
    preferredNetwork,
    preferredMaintenanceWindows,
    onConfirmSuccess
  ]
  );

  const tabDefinitions:TabsProps.Tab[] = [
    {
      label: i18n.tabHeadingGeneral,
      id: 'general',
      content: <>
        <UserPreferencesGeneral
          preferredNetwork={preferredNetwork}
          enabledNetworks={enabledNetworks}
          setPreferredNetwork={setPreferredNetwork}
          preferredRegion={preferredRegion}
          enabledRegions={enabledRegions}
          setPreferredRegion={setPreferredRegion}
        />
      </>
    },
    {
      label: i18n.tabHeadingMaintenanceWindow,
      id: 'second',
      content: <>
        <UserPreferencesMaintenanceWindow
          preferredMaintenanceWindows={preferredMaintenanceWindows}
          setPreferredMaintenanceWindows={setPreferredMaintenanceWindows}
        />
      </>
    },

  ];

  return (
    <Modal
      onDismiss={onDismiss}
      size='large'
      visible={visible}
      closeAriaLabel={i18n.closeModal}
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <RoleAccessToggle feature={RoleBasedFeature.UpdateUserProfile}>
              <Button variant="link" onClick={onDismiss}>{i18n.buttonCancel}</Button>
              <Button
                variant="primary"
                onClick={onConfirm}
                loading={userProfileLoading}
              >
                {i18n.buttonConfirm}
              </Button>
            </RoleAccessToggle>
          </SpaceBetween>
        </Box>
      }
      header={i18n.title}
    >
      {userProfileLoading && <Spinner />}
      {!userProfileLoading && <>
        <Tabs tabs={tabDefinitions}></Tabs>
      </>}
    </Modal>
  );
};
