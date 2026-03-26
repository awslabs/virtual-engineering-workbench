/* eslint-disable @typescript-eslint/no-magic-numbers */
import { format, startOfDay, addMinutes, addHours } from 'date-fns';
import { MaintenanceWindow } from '../services/API/proserve-wb-provisioning-api';


const START_DATE = startOfDay(new Date());
const MAINTENANCE_WINDOW_DURATION_IN_HOURS = 4;

function formatTime(date: Date) {
  return format(date, 'HH:mm');
}

function convertDateToUTC(date: Date) {
  return addMinutes(date, date.getTimezoneOffset());
}


type MaintenanceWindowTimeOption = {
  label: string,
  value: string,
};

function getMaintenanceWindowTimeOptions(): MaintenanceWindowTimeOption[] {
  const maintenanceWindowStartOptions: MaintenanceWindowTimeOption[] = [];

  for (let i = 0; i < 24; i++) {
    const date = addHours(START_DATE, i);
    maintenanceWindowStartOptions.push({
      label: formatTime(date),
      value: formatTime(convertDateToUTC(date)),
    });
  }
  return maintenanceWindowStartOptions;
}

export function getMaintenanceWindowEndTime(startLabel: string): MaintenanceWindowTimeOption {
  const startDate = new Date(`${START_DATE.toDateString()} ${startLabel}`);
  const endDate = addHours(startDate, MAINTENANCE_WINDOW_DURATION_IN_HOURS);
  return {
    label: formatTime(endDate),
    value: formatTime(convertDateToUTC(endDate)),
  };
}

export const MAINTENANCE_WINDOW_TIME_OPTIONS = getMaintenanceWindowTimeOptions();

export const MAINTENANCE_WINDOW_DAYS: string[] = [
  'MONDAY',
  'TUESDAY',
  'WEDNESDAY',
  'THURSDAY',
  'FRIDAY',
  'SATURDAY',
  'SUNDAY'
];

export const DEFAULT_MAINTENANCE_WINDOWS
: MaintenanceWindow[]
  = MAINTENANCE_WINDOW_DAYS.slice(0, 5).map((d) => {
    return {
      day: d,
      startTime: MAINTENANCE_WINDOW_TIME_OPTIONS[0].value,
      endTime: getMaintenanceWindowEndTime(MAINTENANCE_WINDOW_TIME_OPTIONS[0].label).value
    };
  });

export const MIN_MAINTENANCE_WINDOW_DAYS = 2;