export function isNullOrEmpty(str: string) {
  return !str || str.trim() === '';
}

export function isUrl(str: string) {
  try {
    const url = new URL(str.trim());
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
}

// A function to check if a string has max length of given value
export function hasMaxLength(str: string, maxLength: number) {
  return str.length <= maxLength;
}
