import { describe, expect, it } from 'vitest';
import { preselectedVersion } from './provisioning.helpers';

const v = (versionName: string, isRecommendedVersion = false) => ({ versionName, isRecommendedVersion });

// The launch pre-selected the oldest version (1.0.0 next to 1.0.3).
describe('preselectedVersion', () => {
  it('takes the newest release', () => {
    expect(preselectedVersion([v('1.0.0'), v('1.0.3')])?.versionName).toBe('1.0.3');
    expect(preselectedVersion([v('1.0.2'), v('1.0.1')])?.versionName).toBe('1.0.2');
    expect(preselectedVersion([v('1.0.9'), v('1.0.10'), v('1.0.2')])?.versionName).toBe('1.0.10');
  });

  it('prefers a release over a newer release candidate, and a release over its candidate', () => {
    expect(preselectedVersion([v('1.0.3'), v('1.0.4-rc.1')])?.versionName).toBe('1.0.3');
    expect(preselectedVersion([v('1.0.4-rc.1'), v('1.0.4')])?.versionName).toBe('1.0.4');
    expect(preselectedVersion([v('1.0.4-rc.1'), v('1.0.4-rc.2')])?.versionName).toBe('1.0.4-rc.2');
  });

  it('takes the recommended version first', () => {
    expect(preselectedVersion([v('1.0.0', true), v('1.0.3')])?.versionName).toBe('1.0.0');
  });

  it('selects nothing without versions', () => {
    expect(preselectedVersion([])).toBeUndefined();
  });
});
