// Pulls Markdown that lives elsewhere in the repository into the site at build
// time, so the repo stays the single source of truth. Each entry maps a repo
// file to a page; relative links are rewritten to the page they point at, or
// to GitHub when the target is not part of the site.
import { readFileSync, writeFileSync, mkdirSync, rmSync, cpSync, existsSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, posix } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(here, '..', '..');
const docsRoot = join(here, '..', 'src', 'content', 'docs');
// Must match astro.config.mjs, which honours the same override. Trailing slash
// stripped so SITE_BASE=/ yields /page/ rather than a protocol-relative //page/.
const BASE = (process.env.SITE_BASE || '/virtual-engineering-workbench').replace(/\/+$/, '');
const REPO = 'https://github.com/awslabs/virtual-engineering-workbench';

const PAGES = [
  { src: 'docs/authorization-model.md', page: 'concepts/authorization-model', order: 4 },
  { src: 'docs/launch-a-product.md', page: 'developers/launch-a-product', order: 1 },
  { src: 'docs/connect-to-a-product.md', page: 'developers/connect-to-a-product', order: 2 },
  { src: 'docs/onboard-an-account.md', page: 'platform/onboard-an-account', order: 1 },
  { src: 'docs/marketplace-integration.md', page: 'platform/marketplace-integration', order: 2 },
  { src: 'docs/packaging-s2s-api.md', page: 'platform/packaging-s2s-api', order: 3 },
  { src: 'docs/provisioning-s2s-api.md', page: 'platform/provisioning-s2s-api', order: 4 },
  { src: 'examples/freertos/README.md', page: 'examples/freertos', order: 1, label: 'FreeRTOS virtual target' },
  { src: 'examples/android-cuttlefish/README.md', page: 'examples/android-cuttlefish', order: 2, label: 'Android Cuttlefish' },
  { src: 'examples/qemu-kvm/README.md', page: 'examples/qemu-kvm', order: 3, label: 'QEMU/KVM nested virtualization' },
  { src: 'cli/README.md', page: 'tools/cli', order: 1, label: 'VEW CLI' },
  { src: 'CONTRIBUTING.md', page: 'project/contributing', order: 1, label: 'Contributing' },
  { src: 'SECURITY.md', page: 'project/security', order: 2, label: 'Security' },
];

const bySrc = new Map(PAGES.map((p) => [p.src, p]));
const dirAlias = (p) => (bySrc.has(p) ? p : bySrc.has(`${p}/README.md`) ? `${p}/README.md` : null);

// Same-document anchors in a source file stay same-document on its page -- but
// only if the heading came along. Where a page is assembled from part of a
// source file, the rest of that file's headings are not on it, so an anchor
// into them is dead. Each such anchor is mapped to where it actually lives.
const ANCHOR_TARGETS = {
  'README.md': {
    'private-deployment': `${BASE}/operators/private-deployment/`,
    // No site page covers the spoke bootstrap template, so this one points at
    // the README section it came from.
    'spoke-account-onboarding': `${REPO}#spoke-account-onboarding`,
  },
};

function rewriteLink(url, fromRepoPath) {
  if (/^(https?:|mailto:)/.test(url)) return url;
  if (url.startsWith('#')) {
    return ANCHOR_TARGETS[fromRepoPath]?.[url.slice(1)] ?? url;
  }
  const [rawPath, hash = ''] = url.split('#');
  const h = hash ? `#${hash}` : '';
  const target = posix.normalize(posix.join(posix.dirname(fromRepoPath), rawPath)).replace(/\/$/, '');
  const hit = dirAlias(target);
  if (hit) return `${BASE}/${bySrc.get(hit).page}/${h}`;
  // Anything else lives only in the repository. Ask the checkout whether the
  // target is a file rather than guessing from the extension, which sent
  // extensionless files such as LICENSE to a /tree/ URL.
  let isFile = /\.[a-z0-9]+$/i.test(target);
  try {
    isFile = statSync(join(repoRoot, target)).isFile();
  } catch {
    /* not in the checkout: keep the extension guess */
  }
  return `${REPO}/${isFile ? 'blob' : 'tree'}/main/${target}${h}`;
}

// A fence opens with ``` or ~~~ and closes with the same marker, so a line
// inside a block is never mistaken for a heading.
function demoteHeadings(text) {
  let fence = null;
  return text
    .split('\n')
    .map((line) => {
      const m = line.match(/^\s*(```+|~~~+)/);
      if (m) {
        if (!fence) fence = m[1][0];
        else if (m[1][0] === fence) fence = null;
        return line;
      }
      return fence ? line : line.replace(/^# /, '## ');
    })
    .join('\n');
}

// Remove previously generated files only; hand-written pages in the same
// folders (e.g. project/roadmap.mdx) are left alone.
for (const entry of PAGES) {
  const f = join(docsRoot, `${entry.page}.md`);
  if (existsSync(f)) rmSync(f);
}

let skipped = 0;
for (const entry of PAGES) {
  // A source can legitimately be absent: this repository is mirrored, and the
  // two copies do not carry an identical set of root files. Skip the page with
  // a visible warning rather than failing the whole build, so the site can be
  // built from either copy.
  const srcPath = join(repoRoot, entry.src);
  if (!existsSync(srcPath)) {
    console.warn(`sync-docs: no ${entry.src} in this checkout, skipping ${entry.page}`);
    skipped++;
    continue;
  }
  let text = readFileSync(srcPath, 'utf8');
  const m = text.match(/^# (.+)\n+/);
  const title = m ? m[1].trim() : entry.label ?? entry.page;
  if (m) text = text.slice(m[0].length);
  text = text.replace(/\]\(([^)\s]+)\)/g, (_, u) => `](${rewriteLink(u, entry.src)})`);
  // Headings must not use `#` level 1 inside a Starlight page. Only outside
  // fenced blocks: a shell comment such as `# fetch the values` is not a
  // heading, and demoting it printed `## ...` inside the CLI page's examples.
  text = demoteHeadings(text);
  const fm = [
    '---',
    `title: ${JSON.stringify(title)}`,
    entry.label ? `sidebar:\n  label: ${JSON.stringify(entry.label)}\n  order: ${entry.order}` : `sidebar:\n  order: ${entry.order}`,
    `editUrl: ${REPO}/edit/main/${entry.src}`,
    '---',
    '',
  ].join('\n');
  // The provenance note goes after the body: a reader wants the task first,
  // and the Edit link in the page header already points at the source.
  const note = [
    '',
    `:::note[Source]`,
    `This page is generated from [\`${entry.src}\`](${REPO}/blob/main/${entry.src}) in the repository.`,
    `:::`,
    '',
  ].join('\n');
  const out = join(docsRoot, `${entry.page}.md`);
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, `${fm + text.replace(/\s+$/, '')}\n${note}`);
}

const assetsOut = join(here, '..', 'public', 'assets');
const assetsSrc = join(repoRoot, 'assets');
if (existsSync(assetsSrc)) {
  rmSync(assetsOut, { recursive: true, force: true });
  // Only the diagrams the pages reference, so a new file in assets/ is not
  // published by accident.
  mkdirSync(assetsOut, { recursive: true });
  for (const png of ['architecture-public.png', 'architecture-private.png', 'architecture-backend.png']) {
    const from = join(assetsSrc, png);
    if (existsSync(from)) cpSync(from, join(assetsOut, png));
    else console.warn(`sync-docs: no assets/${png} in this checkout`);
  }
} else {
  console.warn('sync-docs: no assets/ directory in this checkout, keeping the published assets as they are');
}


{
  const readme = readFileSync(join(repoRoot, 'README.md'), 'utf8');
  const start = readme.indexOf('### Configuration reference');
  const end = readme.indexOf('### What gets patched');
  if (start < 0 || end < 0) throw new Error('README configuration section not found');
  let body = readme.slice(start, end).replace('### Configuration reference\n', '');
  body = body.replace(/\]\(([^)\s]+)\)/g, (_, u) => `](${rewriteLink(u, 'README.md')})`);
  body = body.replace(/^### /gm, '## ');
  const out = join(docsRoot, 'operators', 'configuration.md');
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, `---
title: Configuration reference
description: Every deploy.sh parameter and the advanced settings in the source tree.
sidebar:
  order: 5
editUrl: ${REPO}/edit/main/README.md
---

${body.replace(/\s+$/, '')}

:::note[Source]
This page is generated from the [README](${REPO}#configuration-reference) in the repository.
:::
`);
}

console.log(`synced ${PAGES.length + 1 - skipped} pages${skipped ? `, skipped ${skipped}` : ''}`);
