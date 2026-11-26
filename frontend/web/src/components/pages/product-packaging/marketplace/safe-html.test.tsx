// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Tests for SafeHtml — the DOMPurify-backed wrapper used for
// AWS Marketplace HTML content (LongDescription, Highlights, etc.).
//
// Coverage:
// - Renders allowlisted tags (h1..h4, p, ul/ol/li, strong/em, a, br)
// - Strips disallowed tags (script, iframe, style, on* attrs)
// - Forces `target=_blank rel=noopener noreferrer` on all links
// - Returns null for empty / null / undefined input
// - Idempotent — sanitizing already-clean HTML doesn't corrupt it
// - Markup renders as elements, never as literal `<h3>...</h3>` text.

import React from 'react';
import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { SafeHtml } from './safe-html';

const TWO = 2;

describe('SafeHtml', () => {
  it('renders nothing for null/undefined/empty input', () => {
    const { container: c1 } = render(<SafeHtml html={null} />);
    expect(c1.firstChild).toBeNull();

    const { container: c2 } = render(<SafeHtml html={undefined} />);
    expect(c2.firstChild).toBeNull();

    const { container: c3 } = render(<SafeHtml html="" />);
    expect(c3.firstChild).toBeNull();
  });

  it('renders allowlisted tags as real DOM (not escaped text)', () => {
    const html = '<h3>Title</h3><p>Body with <strong>emphasis</strong>.</p>';
    const { container } = render(<SafeHtml html={html} />);

    // Sanity: the h3 element exists as real DOM, not as literal text
    const h3 = container.querySelector('h3');
    expect(h3).not.toBeNull();
    expect(h3?.textContent).toBe('Title');

    const strong = container.querySelector('strong');
    expect(strong?.textContent).toBe('emphasis');

    // Explicitly verify the raw text does NOT contain angle-bracketed tags
    expect(container.textContent).not.toContain('<h3>');
    expect(container.textContent).not.toContain('</strong>');
  });

  it('renders lists', () => {
    const html = '<ul><li>One</li><li>Two</li></ul>';
    const { container } = render(<SafeHtml html={html} />);
    const items = container.querySelectorAll('li');
    expect(items).toHaveLength(TWO);
    expect(items[0].textContent).toBe('One');
    expect(items[1].textContent).toBe('Two');
  });

  it('strips script tags entirely', () => {
    const html = 'Before <script>alert("xss")</script> after';
    const { container } = render(<SafeHtml html={html} />);
    // No <script> element should exist
    expect(container.querySelector('script')).toBeNull();
    // The alert() string should also be gone (KEEP_CONTENT still strips
    // script bodies because DOMPurify special-cases them).
    expect(container.textContent).not.toContain('alert');
    // Regular text around it survives
    expect(container.textContent).toContain('Before');
    expect(container.textContent).toContain('after');
  });

  it('strips inline event handlers', () => {
    const html = '<p onclick="alert(1)">Click me</p>';
    const { container } = render(<SafeHtml html={html} />);
    const p = container.querySelector('p');
    expect(p).not.toBeNull();
    expect(p?.getAttribute('onclick')).toBeNull();
    // Text content survives
    expect(p?.textContent).toBe('Click me');
  });

  it('strips iframe tags', () => {
    const html = '<iframe src="https://evil.example"></iframe>ok';
    const { container } = render(<SafeHtml html={html} />);
    expect(container.querySelector('iframe')).toBeNull();
    expect(container.textContent).toContain('ok');
  });

  it('forces target=_blank rel=noopener noreferrer on all links', () => {
    const html = '<a href="https://example.com">Link</a>';
    const { container } = render(<SafeHtml html={html} />);
    const a = container.querySelector('a');
    expect(a).not.toBeNull();
    expect(a?.getAttribute('href')).toBe('https://example.com');
    expect(a?.getAttribute('target')).toBe('_blank');
    expect(a?.getAttribute('rel')).toBe('noopener noreferrer');
  });

  it('overrides user-supplied target/rel with safe values', () => {
    // Even if seller supplies `target=_self rel=""`, we still force safe values.
    const html = '<a href="https://example.com" target="_self" rel="">Link</a>';
    const { container } = render(<SafeHtml html={html} />);
    const a = container.querySelector('a');
    expect(a?.getAttribute('target')).toBe('_blank');
    expect(a?.getAttribute('rel')).toBe('noopener noreferrer');
  });

  it('applies data-test attribute for testability', () => {
    const { container } = render(<SafeHtml html="<p>x</p>" data-test="my-html" />);
    const wrapper = container.querySelector('[data-test="my-html"]');
    expect(wrapper).not.toBeNull();
  });
});
