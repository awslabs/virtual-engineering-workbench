/* eslint-disable @typescript-eslint/no-magic-numbers */
import {
  Button,
  FormField,
  Grid,
  Header,
  Select,
  SpaceBetween,
  TextContent,
} from '@cloudscape-design/components';
import { i18n } from './user-preferences.translations';
import { FC } from 'react';
import { MaintenanceWindow } from '../../services/API/proserve-wb-provisioning-api';
import { useUserPreferencesMaintenanceWindow } from './user-preferences-maintenance-window.logic';

type Props = {
  preferredMaintenanceWindows: MaintenanceWindow[],
  setPreferredMaintenanceWindows: (value: MaintenanceWindow[]) => void,
};
const gridDefinition = [{ colspan: 2 }, { colspan: 3 }];


export const UserPreferencesMaintenanceWindow: FC<Props> = ({
  preferredMaintenanceWindows,
  setPreferredMaintenanceWindows
}) => {
  const {
    getSelectedStartOption,
    getEndTimeLabel,
    modifyMaintenanceWindowDay,
    modifyMaintenanceWindowStart,
    startTimeOptions,
    days
  } = useUserPreferencesMaintenanceWindow({
    preferredMaintenanceWindows,
    setPreferredMaintenanceWindows
  });

  function renderMaintenanceWindowForm(day: string) {
    const selectedStartOption = getSelectedStartOption(day);
    return <Grid gridDefinition={gridDefinition} key={day}>
      <p className='capitalize'>{day.toLowerCase()}</p>
      <SpaceBetween direction="horizontal" size='s'>
        <FormField constraintText={getEndTimeLabel(selectedStartOption)}>
          <Select
            options={startTimeOptions}
            selectedOption={selectedStartOption || startTimeOptions[0]}
            disabled={!selectedStartOption}
            onChange={({ detail }) => modifyMaintenanceWindowStart(day, detail.selectedOption)}
          />
        </FormField>
        <div className='maintenance-window-action'>
          {!selectedStartOption
            && <Button
              iconName="add-plus"
              onClick={()=> { modifyMaintenanceWindowDay(day); }}
              variant='primary'/>
          }
          {selectedStartOption
            && <Button
              iconName="remove"
              onClick={() => { modifyMaintenanceWindowDay(day); }}/>
          }
        </div>
      </SpaceBetween>
    </Grid>;
  }

  return (
    < >
      <SpaceBetween direction='vertical' size='l'>
        <Header description={i18n.tabDescriptionMaintenanceWindow} variant='h3'>
          {i18n.tabHeadingMaintenanceWindow}
        </Header>
        <TextContent>
          <small>{i18n.tabDescriptionMaintenanceWindow2}</small>
        </TextContent>
        <Grid gridDefinition={gridDefinition}>
          <div></div>
          <strong className='capitalize'>starting</strong>
        </Grid>
        {days.map(day => renderMaintenanceWindowForm(day))}
      </SpaceBetween>
    </>
  );
};