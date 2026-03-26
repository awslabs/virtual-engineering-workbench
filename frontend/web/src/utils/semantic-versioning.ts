const bigger = 1;
const smaller = -1;
const equal = 0;

function extractVersionElements(version: string, pattern: RegExp): number[] {
  const defaultVersion = 0;
  const matches = version.match(pattern);
  if (matches) {
    return matches.map((ele: string) => { return Number(ele); });
  }
  return [defaultVersion];
}

function extractVersion(v: string): number[] {
  const regexAll = /\d+/gu;
  return extractVersionElements(v, regexAll);
}

function compareVersionAToVersionB(v1: number[], v2: number[]): number {
  const startIndex = 0;

  const minLength = Math.min(v1.length, v2.length);

  for (let i = startIndex; i < minLength; i++) {
    if (v1[i] === v2[i]) {
      continue;
    }
    return v2[i] > v1[i] ? bigger : smaller;
  }
  return equal;
}

function releaseCandidateHandling(a?: string, b?: string): number {
  if (a?.includes('rc')) {
    return bigger;
  }
  if (b?.includes('rc')) {
    return smaller;
  }
  return equal;
}

export function compare(a?: string, b?: string) {
  const semVerElements1 = extractVersion(a || '');
  const semVerElements2 = extractVersion(b || '');

  const comparison = compareVersionAToVersionB(semVerElements1, semVerElements2);
  if (comparison === equal) {
    return releaseCandidateHandling(a, b);
  }
  return comparison;
}
