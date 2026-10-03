## Context

The repository contains only `.claude/` (OpenSpec commands and skills, which must be preserved) and `openspec/` (an unconfigured `config.yaml`, no specs). It is not a git repository. There is no legacy site, so there are no URLs to preserve. The local toolchain is Node 24.19 with pnpm 12.8.1 available through Corepack. Hosting is fixed to **Render Free Tier**, and the delivery and service name is `ai-job-recommendation-ui`. See proposal.md for motivation, and the three specs for the behavior contract.

Registry checks run while writing this design:
- `typescript-eslint` (pulled in by `eslint-config-next`) supports `typescript >=4.8.4 <6.1.0`, so TypeScript 7 cannot be used yet.
- `eslint-plugin-react`, `eslint-plugin-import` and `eslint-plugin-jsx-a11y` (also pulled in by `eslint-config-next`) cap their ESLint peer at `^9`, so ESLint 10 cannot be used yet.
- Render Static Sites serve `page/index.html` at both `/page` and `/page/`, and trailing-slash behavior can't be configured on Render.

## Goals / Non-Goals

**Goals:**
- A buildable, lint-clean, type-clean Next.js App Router project that exports to static files and is ready to connect to Render.
- Conventions (structure, content, tokens, routes) that later changes can extend without restructuring.

**Non-Goals:**
- Any page UI, components, layout, visual design, fonts, color palette, animation, or copy.
- Actually deploying, connecting the GitHub repo to Render, or buying a domain.
- Test frameworks, CI pipelines, git hooks, analytics, MDX, or a CMS.
- Defining the product's route map. Routes are added by later feature changes through the route registry.

## Decisions

### D1. Next.js 16 App Router, statically exported
`next@16.3.x`, `react@19`, App Router only (no `pages/`), Server Components by default, `output: "export"`.
- **Why static export:** Render's free Web Service spins down when idle, so the first request after inactivity takes tens of seconds. That hurts crawlers and first impressions. A free Render Static Site is served from a CDN with no cold start. The foundation has no server-side needs.
- **Alternative considered:** Web Service running `next start` on the free plan. It keeps redirects, rewrites, image optimization and request-time rendering, but has cold starts. Rejected for now; moving to it later means removing `output: "export"` and changing `render.yaml`, without restructuring the code.
- **Consequences, accepted:** no request-time Route Handlers, no `redirects`/`rewrites`/`headers` in `next.config.ts` (use Render's redirect, rewrite and header rules if needed), no `proxy.ts`, and `images.unoptimized: true`. Future AI and recommendation features will call an external API from the client, or justify a hosting change in their own proposal.

### D2. Trailing-slash URLs
`trailingSlash: true` makes the export emit `route/index.html`. On Render that file is served at both `/route` and `/route/`, so every page carries a self-referencing canonical in trailing-slash form (see the `static-site-delivery` spec).
- **Alternative:** `trailingSlash: false` emits `route.html`, which needs host rewrites for extension-less URLs. Rejected because it's fragile on Render.

### D3. Toolchain versions
| Tool | Version | Reason |
|---|---|---|
| TypeScript | `^5` (5.9.x) | typescript-eslint ceiling; matches create-next-app |
| ESLint | `^9` (flat config) | plugin peer ceiling |
| Tailwind CSS | `^4` via `@tailwindcss/postcss` | CSS-first config, no `tailwind.config.js` |
| Prettier | `^3` + `prettier-plugin-tailwindcss` | class sorting; `tailwindStylesheet` points at `src/app/globals.css` |
| Node | `24.x` (`engines` + `.node-version`) | current LTS; still ships Corepack, which Node 25 drops |
| pnpm | `pnpm@12.8.1` in `packageManager` | resolved through Corepack locally and on Render |

React Compiler: **off** (it adds a Babel plugin and build cost, and nothing needs it yet).

### D4. Dependencies
- **Runtime:** `next`, `react`, `react-dom`.
- **Dev:** `typescript`, `@types/node`, `@types/react`, `@types/react-dom`, `tailwindcss`, `@tailwindcss/postcss`, `eslint`, `eslint-config-next`, `eslint-config-prettier`, `prettier`, `prettier-plugin-tailwindcss`.
- **Later, only when a change needs them:** `@tailwindcss/typography` (long-form prose), `clsx` / `tailwind-merge` (component variants), `@next/mdx` or `next-mdx-remote` + `gray-matter` (Markdown or MDX content), a CMS SDK, `zod` (validating external data), `@playwright/test` (route and E2E checks), `husky` + `lint-staged` (multiple contributors).
- **Explicitly excluded:** UI kits, state managers, data-fetching libraries, CSS-in-JS, `next-seo` and `next-sitemap` (the built-in Metadata API, `sitemap.ts` and `robots.ts` cover them), `dotenv` (Next loads `.env*`), `sharp` (not used with unoptimized images).

### D5. Scaffolding approach
`create-next-app` refuses to run in a folder containing unrecognized entries (`.claude/`, `openspec/`). So: run `pnpm create next-app@16.3.8` into a scratch directory (TypeScript, Tailwind, ESLint, App Router, `src/`, `@/*` alias, pnpm, no React Compiler), copy its config files into the repo, then strip the demo content (default page markup, demo SVGs, Geist font wiring). Any agent-instruction file it generates (e.g. `AGENTS.md`) is reviewed and not copied over existing `.claude/` content. Prettier, `.gitattributes`, `render.yaml` and the `src/lib` / `src/content` structure are added by hand.

### D6. Directory structure
```
src/
  app/
    layout.tsx        root <html>, global metadata (metadataBase, title template, robots), globals.css
    page.tsx          placeholder home that renders content from the access layer
    not-found.tsx     placeholder; exported as out/404.html
    globals.css       @import "tailwindcss"; @theme placeholder tokens; minimal base styles
    sitemap.ts        built from the route registry (export const dynamic = "force-static")
    robots.ts         indexing on or off per SITE_INDEXING (force-static)
  content/
    types.ts          content type definitions (PageContent, …)
    pages.ts          static content entries keyed by slug (home only for now)
  lib/
    site.ts           siteName, validated siteUrl (from NEXT_PUBLIC_SITE_URL), indexing flag
    routes.ts         route registry: list of public routes { path, contentSlug }
    content.ts        async accessors, e.g. getPageContent(slug); throws on unknown slug
public/               favicon only
```
No `components/`, `hooks/`, `utils/`, `styles/` or route groups until a real file needs them. `typedRoutes: true` is enabled so `<Link href>` values are checked against existing routes at compile time.

### D7. Content layer
Content is plain typed data in `src/content/`. Pages call `await getPageContent("home")` from `src/lib/content.ts`, and `generateMetadata` uses the same call. Accessors are async now so a later CMS or MDX implementation keeps the same signature. Content types mirror what a CMS model would hold (slug, `seo.title`, `seo.description`, body fields as strings or arrays of plain objects). Rich text stays as plain strings until a prose-format change decides between Markdown and MDX. An ESLint `no-restricted-imports` rule blocks `@/content/*` imports from outside `src/lib/`, which enforces the `content-source` spec.

### D8. Route registry
`src/lib/routes.ts` exports the list of public routes. It's the single source for `sitemap.ts`, and later for navigation and route tests. It starts with `/` only. Adding a page means adding the `app/` folder and a registry entry together, and the proposal for each future feature change lists its routes there.

### D9. Styling foundation
`globals.css` holds `@import "tailwindcss";` and an `@theme` block of **neutral placeholder tokens**: a grayscale palette plus one placeholder accent, `--font-sans` set to a system font stack, and radius and spacing defaults left at Tailwind's. Conventions: style with utilities; reference colors and fonts only through theme tokens (no raw hex values in markup); keep component-specific CSS out of `globals.css`. The redesign change replaces token values and adds `next/font` without renaming the mechanism. Dark mode is deferred to the design step.

### D10. Lint and format configuration
- `eslint.config.mjs`: `eslint-config-next/core-web-vitals` + `eslint-config-next/typescript` + `eslint-config-prettier` last; global ignores for `.next/`, `out/`, `next-env.d.ts`; plus the D7 import restriction.
- `.prettierrc.json`: defaults plus `endOfLine: "lf"`, the Tailwind plugin, and `tailwindStylesheet`. `.prettierignore` covers `.next/`, `out/`, `pnpm-lock.yaml`, `openspec/`, `.claude/`.
- `.gitattributes`: `* text=auto eol=lf` (Windows development, Linux build).
- `tsconfig.json`: create-next-app defaults with `strict: true` and `noUncheckedIndexedAccess: true`.
- Scripts: `dev`, `build`, `lint` (`eslint .`), `typecheck` (`tsc --noEmit`), `format`, `format:check`, `check` (lint + typecheck + format:check), and `preview` (serves `out/` with a zero-install static server via `pnpm dlx serve out`). There is no `start` script, because `next start` doesn't apply to static export.

### D11. pnpm build-script policy
pnpm 10+ blocks dependency lifecycle scripts by default. After the first install, review the reported ignored builds and allowlist only what the toolchain needs in `pnpm-workspace.yaml`. Expected candidates: `unrs-resolver` (ESLint import resolver), and possibly `@tailwindcss/oxide`. Record the allowlist so frozen installs on Render behave the same as local ones.

### D12. Environment and site config
- `NEXT_PUBLIC_SITE_URL`: required for `next build`. `src/lib/site.ts` validates it and throws a named error when it's missing or malformed. In `next dev` it falls back to `http://localhost:3000`.
- `SITE_INDEXING`: `"true"` enables indexing; anything else (including unset) means `robots.txt` has `Disallow: /` and the root metadata sets `robots: { index: false, follow: false }`.
- `.env.example` documents both. `.env*.local` stays git-ignored.

### D13. Render blueprint
`render.yaml` defines one static site:
- `type: web`, `runtime: static`, `name: ai-job-recommendation-ui` (static sites are free, so no paid plan field is needed)
- `buildCommand: corepack enable && pnpm install --frozen-lockfile && pnpm build`
- `staticPublishPath: ./out`
- env vars: `NODE_VERSION` = 24, `NEXT_PUBLIC_SITE_URL` = `https://ai-job-recommendation-ui.onrender.com` (the actual hostname is confirmed when the service is created), `SITE_INDEXING` = `false`
- pull-request previews disabled

Exact key names are checked against Render's current Blueprint spec while writing the file. It's committed but not applied. Connecting the repo and creating the service is a separate, manual step.

## Risks / Trade-offs

- [Static export blocks future server features, such as AI calls that need secret API keys] → Keep secrets out of the client. When a feature needs a server, its proposal either adds an external API service or switches this site to a Render Web Service (D1 alternative). The code structure doesn't change.
- [Render may not return HTTP 404 for `out/404.html`] → Verify after the first deploy. If not, add a Render rewrite or error-page rule. The spec's not-found requirement is verified locally against `serve`, which honors `404.html`.
- [Duplicate URLs `/x` and `/x/` on Render] → Self-referencing trailing-slash canonicals (D2), plus `trailingSlash: true` so internal links are consistent.
- [Corepack is unavailable or the pnpm download fails on Render] → Node 24 still bundles Corepack. Fallback build command: `npm i -g pnpm@12.8.1 && pnpm install --frozen-lockfile && pnpm build`.
- [pnpm 12 build-script settings differ from pnpm 10 documentation] → D11 is resolved empirically from the install output, not from memory.
- [A page is added without a registry entry and is missing from the sitemap] → Convention plus review for now. A route-registry test can be added when `@playwright/test` arrives.
- [The `onrender.com` hostname differs from the service name, e.g. a suffix is added] → Update `NEXT_PUBLIC_SITE_URL` in Render after the service is created. It's build-time, so redeploy afterwards.

## Migration Plan

No existing system, so there's nothing to migrate. Rollback means deleting the generated files, and git (initialized in task 1) makes this trivial.
