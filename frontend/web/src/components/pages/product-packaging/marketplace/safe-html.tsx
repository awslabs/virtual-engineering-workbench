// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// SafeHtml — renders AWS Marketplace-provided HTML strings safely.
//
// AWS Marketplace catalog fields (LongDescription, Highlights, etc.) may
// contain a limited HTML tag set (headings, paragraphs, lists, basic
// inline formatting, links). Rendering them as plain text produces the
// literal "<h3>...</h3>" text for the user. Rendering them
// unsanitized is a stored-XSS risk if a compromised seller injects
// scripts.
//
// This component sanitizes with DOMPurify against an allowlist and
// injects the result with `dangerouslySetInnerHTML`. The allowlist is
// intentionally narrow — headings, paragraphs, lists, basic emphasis,
// line breaks, and external links (with `rel="noopener noreferrer"`
// forced).
//
// If the input is falsy or (after sanitization) empty, the component
// renders nothing.

import { FC, useMemo } from 'react';
import DOMPurify from 'dompurify';

interface SafeHtmlProps {
  html: string | null | undefined,
  /**
   * Optional inline style overrides for the wrapper. Prefer keeping
   * defaults; Cloudscape's typography inherits into the injected DOM.
   */
  style?: React.CSSProperties,
  /**
   * Testing hook.
   */
  // eslint-disable-next-line @typescript-eslint/naming-convention -- DOM attribute name
  'data-test'?: string,
}

const ALLOWED_TAGS = [
  // Headings
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  // Block-level text
  'p', 'div', 'br',
  // Lists
  'ul', 'ol', 'li',
  // Inline formatting
  'strong', 'b', 'em', 'i', 'u', 'code', 'span',
  // Links
  'a',
];

const ALLOWED_ATTR = ['href', 'target', 'rel', 'title'];

// Force all links to open in a new tab with a safe rel attr — even if
// the seller supplied their own target/rel, we override for consistency.
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer');
  }
});

export const SafeHtml: FC<SafeHtmlProps> = ({ html, style, 'data-test': dataTest }) => {
  const clean = useMemo(() => {
    if (!html) { return ''; }
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS,
      ALLOWED_ATTR,
      // Reject anything outside the allowlist rather than escaping it.
      KEEP_CONTENT: true,
    });
  }, [html]);

  if (!clean) { return null; }

  return (
    <div
      data-test={dataTest}
      style={style}
      // Sanitized above — safe to inject.
      // eslint-disable-next-line @typescript-eslint/naming-convention -- React's `__html` key
      dangerouslySetInnerHTML={{ __html: clean }}
    />
  );
};
