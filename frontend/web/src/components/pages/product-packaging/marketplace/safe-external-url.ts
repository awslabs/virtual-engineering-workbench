// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// safe-external-url — gate seller-supplied URLs before they reach an `href`.
//
// AWS Marketplace listing resources (`resources[].value`) and legal-term
// documents (`documents[].url`) are authored by the seller. They arrive as
// opaque strings. Passed straight into a Cloudscape `<Link href=...>`, a
// seller who supplies `javascript:...` gets script
// execution in the context of the VEW origin when a user clicks the link;
// `data:text/html,...` gets an attacker-controlled document on a
// same-origin-adjacent surface.
//
// `SafeHtml` already handles this for Marketplace *HTML* fields, because
// DOMPurify drops unsafe URI schemes inside sanitised markup. These two sites
// never went through DOMPurify -- the value was interpolated directly into a
// React prop -- so they need the equivalent gate.
//
// Allowlist, not denylist: only `https:` and `mailto:` pass. A denylist of
// known-bad schemes (`javascript:`, `data:`, `vbscript:`) fails open on
// anything novel, and browsers accept more schemes than any list enumerates.
//
// Plain `http:` is rejected deliberately. These links sit next to a purchase
// decision and are documents a buyer may rely on contractually (EULA, privacy
// policy, refund policy); silently downgrading those to cleartext is not
// something to do on a seller's behalf.

const ALLOWED_PROTOCOLS = ['https:', 'mailto:'];

/**
 * Return the URL if it is safe to use as an `href`, otherwise `null`.
 *
 * Parsing is delegated to the `URL` constructor rather than a regex: it
 * normalises away the tricks that defeat string matching (leading/trailing
 * whitespace, embedded newlines and tabs, `JaVaScRiPt:` casing, percent- and
 * HTML-entity-encoded colons).
 *
 * Relative URLs are rejected. Every caller here renders a seller-supplied
 * *external* link, so a relative value is either a seller mistake or an
 * attempt to make a VEW-internal path look like the seller's own site.
 */
export const safeExternalUrl = (value: string | null | undefined): string | null => {
  if (!value || typeof value !== 'string') { return null; }

  const trimmed = value.trim();
  if (!trimmed) { return null; }

  let parsed: URL;
  try {
    // No base: a relative URL therefore throws and is rejected.
    parsed = new URL(trimmed);
  } catch {
    return null;
  }

  if (!ALLOWED_PROTOCOLS.includes(parsed.protocol)) { return null; }

  // Return the original (trimmed) string rather than `parsed.href`, which
  // normalises in ways a user comparing the link to the seller's site would
  // not expect (appending a trailing slash, re-encoding the path).
  return trimmed;
};

/**
 * True when the value is safe to render as a link.
 */
export const isSafeExternalUrl = (value: string | null | undefined): boolean =>
  safeExternalUrl(value) !== null;
