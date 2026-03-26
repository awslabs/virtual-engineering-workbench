import { parse, getUnixTime } from 'date-fns';

export function getTimestamp(dateStr: string, timeStr: string): number | undefined {
  // Check if either input is empty
  if (!dateStr || !timeStr) {
    return undefined;
  }

  // Combine date and time strings
  const dateTimeStr = `${dateStr} ${timeStr}`;

  try {
    const parsedDate = parse(dateTimeStr, 'yyyy-MM-dd HH:mm', new Date());
    return getUnixTime(parsedDate);
  } catch {
    return undefined;
  }
}