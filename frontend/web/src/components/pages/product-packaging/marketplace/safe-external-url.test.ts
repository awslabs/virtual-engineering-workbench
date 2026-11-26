// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
/* eslint-disable no-script-url -- these tests assert that `javascript:`
   URLs are REJECTED. The literal hostile scheme is the input under test;
   removing it would delete the security assertion. Scoped to this file. */
import { describe, it, expect } from 'vitest';
import { safeExternalUrl, isSafeExternalUrl } from './safe-external-url';

describe('safeExternalUrl', () => {
  it('accepts https URLs', () => {
    expect(safeExternalUrl('https://example.com/eula.pdf')).toBe('https://example.com/eula.pdf');
  });

  it('accepts mailto URLs', () => {
    expect(safeExternalUrl('mailto:support@example.com')).toBe('mailto:support@example.com');
  });

  it('rejects javascript: URLs', () => {
    // `r.value` and `doc.url` are seller-controlled. Passed straight into an
    // href, this value means script execution on the VEW origin as soon as a
    // user clicks the seller's "resource" link.
    expect(safeExternalUrl('javascript:alert(document.cookie)')).toBeNull();
  });

  it('rejects javascript: URLs regardless of casing', () => {
    expect(safeExternalUrl('JaVaScRiPt:alert(1)')).toBeNull();
    expect(safeExternalUrl('JAVASCRIPT:alert(1)')).toBeNull();
  });

  it('rejects javascript: URLs padded with whitespace and control characters', () => {
    // A string-prefix check is defeated by any of these; the URL constructor
    // strips them before resolving the scheme, which is why parsing beats
    // matching here.
    expect(safeExternalUrl('  javascript:alert(1)')).toBeNull();
    expect(safeExternalUrl('\njavascript:alert(1)')).toBeNull();
    expect(safeExternalUrl('\tjava\nscript:alert(1)')).toBeNull();
  });

  it('rejects data: URLs', () => {
    expect(safeExternalUrl('data:text/html,<script>alert(1)</script>')).toBeNull();
    expect(safeExternalUrl('data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==')).toBeNull();
  });

  it('rejects vbscript: and file: URLs', () => {
    expect(safeExternalUrl('vbscript:msgbox(1)')).toBeNull();
    expect(safeExternalUrl('file:///etc/passwd')).toBeNull();
  });

  it('rejects plain http, because these links sit next to a purchase decision', () => {
    // Deliberate: a EULA or privacy policy a buyer may rely on contractually
    // should not be silently fetched over cleartext on the seller's behalf.
    expect(safeExternalUrl('http://example.com/eula.pdf')).toBeNull();
  });

  it('rejects relative URLs', () => {
    // Every caller renders an external seller link, so a relative value is
    // either a seller mistake or an attempt to pass a VEW-internal path off
    // as the seller's own site.
    expect(safeExternalUrl('/projects/proj-1/images')).toBeNull();
    expect(safeExternalUrl('../../admin')).toBeNull();
  });

  it('rejects empty, blank and non-string values', () => {
    expect(safeExternalUrl('')).toBeNull();
    expect(safeExternalUrl('   ')).toBeNull();
    expect(safeExternalUrl(null)).toBeNull();
    expect(safeExternalUrl(undefined)).toBeNull();
  });

  it('does not normalise an accepted URL', () => {
    // `parsed.href` would append a trailing slash and re-encode the path. A
    // user comparing the rendered link against the seller's real site should
    // see exactly what the seller supplied.
    expect(safeExternalUrl('https://example.com')).toBe('https://example.com');
    expect(safeExternalUrl('https://example.com/a path')).toBe('https://example.com/a path');
  });

  it('trims surrounding whitespace from an accepted URL', () => {
    expect(safeExternalUrl('  https://example.com/x  ')).toBe('https://example.com/x');
  });
});

describe('isSafeExternalUrl', () => {
  it('mirrors safeExternalUrl as a boolean', () => {
    expect(isSafeExternalUrl('https://example.com')).toBe(true);
    expect(isSafeExternalUrl('javascript:alert(1)')).toBe(false);
  });
});
