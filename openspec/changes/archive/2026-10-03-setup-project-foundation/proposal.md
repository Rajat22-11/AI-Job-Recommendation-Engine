## Why

`ai-job-recommendation-ui` is a brand-new web UI. The repository has no application code yet, only OpenSpec and Claude configuration. Before any pages or visual design are built, the project needs an agreed, minimal technical foundation: framework, tooling, directory layout, content pattern, and a deployment path that works on Render's free tier.

## What Changes

- Initialize a **Next.js 16 (App Router) + React 19 + TypeScript** application in the existing repository, keeping `.claude/` and `openspec/`.
- Make **pnpm** the only package manager (`packageManager` field, `pnpm-lock.yaml`), with Node 24 pinned.
- Add the quality baseline: **Tailwind CSS v4**, **ESLint 9** (Next.js presets), **Prettier** (with Tailwind class sorting), strict TypeScript, and `lint` / `typecheck` / `format` / `check` scripts.
- Configure the app as a **fully static export** (`output: "export"`) so it deploys as a **Render Static Site**, which is free and has no cold starts.
- Add a `render.yaml` blueprint for the static site named `ai-job-recommendation-ui`. Nothing is deployed in this change.
- Establish a minimal directory structure, a **route registry** that feeds the sitemap, and a **typed static content layer** behind async accessors so content can move to Markdown, MDX or a CMS later without touching pages.
- Add a styling foundation: Tailwind entry stylesheet with **neutral placeholder design tokens** and a system font stack. No visual design is decided here.
- Add SEO plumbing: site-wide metadata, trailing-slash canonical URLs, `sitemap.xml`, and `robots.txt` with **indexing off by default** until launch.
- Add only placeholder `/` and not-found pages, which the static build needs. **No page UI, components, or redesign work.**
- Fill in `openspec/config.yaml` `context` so future changes are grounded in these decisions.

## Capabilities

### New Capabilities
- `project-tooling`: Developer-facing contract for installing, checking, formatting, and building the project (package manager, runtime pin, quality commands, cross-platform formatting).
- `static-site-delivery`: How the built site behaves when hosted: static output, canonical URL form, not-found handling, sitemap, and opt-in search indexing.
- `content-source`: Page content is defined separately from presentation and read through a single access layer, so the content source can be swapped later.

### Modified Capabilities
<!-- None: no existing specs. -->

## Impact

- **New files:** `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, `next.config.ts`, `tsconfig.json`, `eslint.config.mjs`, `postcss.config.mjs`, Prettier config and ignore files, `.gitignore`, `.gitattributes`, `.node-version`, `.env.example`, `render.yaml`, `src/**` (root layout, placeholder home, not-found, sitemap, robots, globals.css, `lib/`, `content/`).
- **Modified:** `openspec/config.yaml` (project context only).
- **Repository:** `git init` before scaffolding.
- **Dependencies:** next, react, react-dom; dev dependencies for TypeScript, Tailwind, ESLint, and Prettier only (see design.md).
- **Hosting constraint:** static export rules out server-only features (API routes at request time, Next.js redirects and rewrites, on-demand image optimization, `proxy.ts`) until the hosting model changes.
