import { parseISO, compareAsc } from 'date-fns';

function compareDates(a: string | undefined, b: string | undefined) {

  const DEFAULT_EMPTY_DATE = '2023-01-01';

  return compareAsc(
    parseISO(a || DEFAULT_EMPTY_DATE),
    parseISO(b || DEFAULT_EMPTY_DATE)
  );

}

export { compareDates as CompareDates };