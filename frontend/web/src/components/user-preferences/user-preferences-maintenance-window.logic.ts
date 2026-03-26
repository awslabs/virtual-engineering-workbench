import { i18n } from './user-preferences.translations';
import { MaintenanceWindow } from '../../services/API/proserve-wb-provisioning-api';
import {
  DEFAULT_MAINTENANCE_WINDOWS,
  MAINTENANCE_WINDOW_DAYS,
  MAINTENANCE_WINDOW_TIME_OPTIONS,
  MIN_MAINTENANCE_WINDOW_DAYS,
  getMaintenanceWindowEndTime
} from '../../utils/maintenance-windows';
import { SelectProps } from '@cloudscape-design/components';

type Props = {
  preferredMaintenanceWindows: MaintenanceWindow[],
  setPreferredMaintenanceWindows: (value: MaintenanceWindow[]) => void,
};

export function useUserPreferencesMaintenanceWindow({
  preferredMaintenanceWindows,
  setPreferredMaintenanceWindows
}:Props) {
  function getSelectedStartOption(day: string) {
    const selectedStartTime = preferredMaintenanceWindows
      ?.find((mw:MaintenanceWindow) => mw.day === day)?.startTime;
    return MAINTENANCE_WINDOW_TIME_OPTIONS
      .find(option => option.value === selectedStartTime) as SelectProps.Option;
  }

  function modifyMaintenanceWindowDay(day: string) {
    if (preferredMaintenanceWindows.some(d => d.day === day)) {
      if (preferredMaintenanceWindows.length > MIN_MAINTENANCE_WINDOW_DAYS) {
        setPreferredMaintenanceWindows(preferredMaintenanceWindows.filter(d => d.day !== day));
      }
    } else {
      setPreferredMaintenanceWindows([
        ...preferredMaintenanceWindows.filter(d => d.day !== day),
        {
          day: day,
          startTime: DEFAULT_MAINTENANCE_WINDOWS[0].startTime,
          endTime: DEFAULT_MAINTENANCE_WINDOWS[0].endTime,
        }
      ]);
    }
  }

  function modifyMaintenanceWindowStart(day: string, startTimeOption: SelectProps.Option) {
    if (startTimeOption.label && startTimeOption.value) {
      setPreferredMaintenanceWindows([
        ...preferredMaintenanceWindows.filter(d => d.day !== day),
        {
          day: day,
          startTime: startTimeOption.value,
          endTime: getMaintenanceWindowEndTime(startTimeOption.label).value,
        } as MaintenanceWindow
      ]);
    }
  }

  function getEndTimeLabel(startTimeOption: SelectProps.Option) {
    if (startTimeOption && startTimeOption.label) {
      return i18n.labelEndingAt(getMaintenanceWindowEndTime(startTimeOption.label).label);
    }
    return '';
  }

  return {
    getSelectedStartOption,
    modifyMaintenanceWindowDay,
    modifyMaintenanceWindowStart,
    getEndTimeLabel,
    startTimeOptions: MAINTENANCE_WINDOW_TIME_OPTIONS,
    days: MAINTENANCE_WINDOW_DAYS
  };
}