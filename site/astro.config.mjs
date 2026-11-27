import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { execSync } from 'node:child_process';

// Shown on the start page, so a reader can tell which commit the site describes.
let mainDate = 'unknown';
try { mainDate = execSync('git log -1 --format=%cs', { encoding: 'utf8' }).trim(); } catch {}
process.env.VEW_MAIN_DATE = mainDate;

const repo = 'https://github.com/awslabs/virtual-engineering-workbench';

export default defineConfig({
  vite: { define: { 'import.meta.env.VEW_MAIN_DATE': JSON.stringify(mainDate) } },
  site: 'https://awslabs.github.io',
  // SITE_BASE lets the same source build for GitHub Pages (default) or a preview host served at /.
  base: process.env.SITE_BASE || '/virtual-engineering-workbench',
  integrations: [
    starlight({
      title: 'Virtual Engineering Workbench',
      description: 'Self-service engineering workbenches and virtual targets on AWS.',
      logo: { src: './src/assets/logo.svg', alt: '' },
      favicon: '/favicon.svg',
      social: [{ icon: 'github', label: 'GitHub', href: repo }],
      editLink: { baseUrl: `${repo}/edit/main/site/` },
      customCss: ['./src/styles/custom.css'],
      components: { SiteTitle: './src/components/SiteTitle.astro' },
      // Groups follow the order of the work, so Previous and Next walk a
      // reader from deploying to publishing to using. Features and Roadmap are
      // in the sidebar too; the header alone was the only way to reach them.
      sidebar: [
        {
          label: 'Start here',
          items: [{ slug: 'what-is-vew' }, { slug: 'getting-started' }, { slug: 'features' }],
        },
        {
          label: 'Concepts',
          items: [{ slug: 'concepts/how-it-works' }, { slug: 'concepts/architecture' }, { slug: 'concepts/accounts-and-access' }, { slug: 'concepts/authorization-model' }],
        },
        { label: 'For operators', items: [{ autogenerate: { directory: 'operators' } }] },
        {
          label: 'For platform engineers',
          items: [{ autogenerate: { directory: 'platform' } }, { autogenerate: { directory: 'examples' } }],
        },
        { label: 'For developers', items: [{ autogenerate: { directory: 'developers' } }] },
        { label: 'Tools and automation', items: [{ autogenerate: { directory: 'tools' } }] },
        {
          label: 'Project',
          items: [{ autogenerate: { directory: 'project' } }, { slug: 'roadmap' }],
        },
      ],
      lastUpdated: false,
    }),
  ],
});
