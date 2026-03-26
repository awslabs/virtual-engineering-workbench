import { ProductParameter } from '../../services/API/proserve-wb-provisioning-api/index.ts';
import { compare } from '../../utils/semantic-versioning.ts';
import { REGULAR_EXPRESSIONS, MINUTES_PER_DAY, LOWER_BOUND } from '.';

export type ProductParameterState = {
  [key: string]: string | undefined,
};

interface AvailableSemanticVersion {
  versionName: string,
}

export function compareSemanticVersions(): (
  a: AvailableSemanticVersion,
  b: AvailableSemanticVersion
) => number {
  return (a, b) => compare(a.versionName, b.versionName);
}


function convertBrowserTimeToUTC0(time: number, timeZoneOffset: number): number {
  let timeInUTC0 = time - timeZoneOffset;

  if (timeInUTC0 < LOWER_BOUND) {
    timeInUTC0 += MINUTES_PER_DAY;
  } else if (timeInUTC0 > MINUTES_PER_DAY) {
    timeInUTC0 -= MINUTES_PER_DAY;
  }

  return timeInUTC0;
}


type TimeInterval = {
  label: string,
  value: string,
};


export function getMaintenanceWindowOptions(timeZoneOffset: number): TimeInterval[] {

  const INTERVAL_1_START = 240;
  const INTERVAL_1_END = 480;
  const INTERVAL_2_START = 480;
  const INTERVAL_2_END = 720;
  const INTERVAL_3_START = 720;
  const INTERVAL_3_END = 960;
  const INTERVAL_4_START = 960;
  const INTERVAL_4_END = 1200;
  const INTERVAL_5_START = 1200;
  const INTERVAL_5_END = 1440;
  const INTERVAL_6_START = 0;
  const INTERVAL_6_END = 240;

  return [
    {
      label: '04:00-08:00',
      value: `${
        convertBrowserTimeToUTC0(INTERVAL_1_START, timeZoneOffset)}-${
        convertBrowserTimeToUTC0(INTERVAL_1_END, timeZoneOffset)
      }`
    },
    {
      label: '08:00-12:00',
      value: `${
        convertBrowserTimeToUTC0(INTERVAL_2_START, timeZoneOffset)}-${
        convertBrowserTimeToUTC0(INTERVAL_2_END, timeZoneOffset)
      }`
    },
    {
      label: '12:00-16:00',
      value: `${
        convertBrowserTimeToUTC0(INTERVAL_3_START, timeZoneOffset)}-${
        convertBrowserTimeToUTC0(INTERVAL_3_END, timeZoneOffset)
      }`
    },
    {
      label: '16:00-20:00',
      value: `${
        convertBrowserTimeToUTC0(INTERVAL_4_START, timeZoneOffset)}-${
        convertBrowserTimeToUTC0(INTERVAL_4_END, timeZoneOffset)}`
    },
    {
      label: '20:00-00:00',
      value: `${
        convertBrowserTimeToUTC0(INTERVAL_5_START, timeZoneOffset)}-${
        convertBrowserTimeToUTC0(INTERVAL_5_END, timeZoneOffset)}`
    },
    {
      label: '00:00-04:00',
      value: `${
        convertBrowserTimeToUTC0(INTERVAL_6_START, timeZoneOffset)}-${
        convertBrowserTimeToUTC0(INTERVAL_6_END, timeZoneOffset)
      }`
    },
  ];
}

export function visibleParameters(parameter: ProductParameter): boolean {
  return !hiddenParameters(parameter);
}

// eslint-disable-next-line complexity
export function hiddenParameters(parameter: ProductParameter): boolean {
  return parameter.parameterKey === 'Experimental' ||
    new RegExp(REGULAR_EXPRESSIONS.securityGroupId, 'giu').test(parameter.parameterType || '') ||
    new RegExp(REGULAR_EXPRESSIONS.ssmParameter, 'giu').test(parameter.parameterType || '');
}