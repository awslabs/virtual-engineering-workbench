/* eslint-disable */
export function sanitizePath(input: string) {
  const invalidChars = /[<>:"/\\|?*\x00-\x1F]/g;
  return input.replace(invalidChars, '_');
}
