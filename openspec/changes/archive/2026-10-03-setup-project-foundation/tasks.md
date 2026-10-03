## 1. Repository preparation

- [x] 1.1 Run `git init`, add `.gitattributes` (`* text=auto eol=lf`), and make an initial commit of the existing `.claude/` and `openspec/` so the scaffold lands as a reviewable diff
- [x] 1.2 Confirm local toolchain: `node -v` reports 24.x and `corepack pnpm -v` reports 12.8.1

## 2. Scaffold Next.js (design D5)

- [x] 2.1 Run `pnpm create next-app@16.3.8` in the session scratchpad with TypeScript, Tailwind, ESLint, App Router, `src/` dir, `@/*` alias, pnpm, no React Compiler
- [x] 2.2 Copy scaffold config and source into the repo (`package.json`, `tsconfig.json`, `next.config.ts`, `eslint.config.mjs`, `postcss.config.mjs`, `.gitignore`, `next-env.d.ts`, `src/app/*`, `public/favicon.ico`) without overwriting `.claude/` or `openspec/`; review any generated agent-instruction file and do not copy it over existing config
- [x] 2.3 Remove demo content: default page markup, demo SVGs in `public/`, Geist `next/font` wiring and its CSS variables
- [x] 2.4 Set `package.json`: `name: "ai-job-recommendation-ui"`, `private: true`, `packageManager: "pnpm@12.8.1"`, `engines.node: "24.x"`; pin `typescript` to `^5` and `eslint` to `^9` (design D3)
- [x] 2.5 Add `.node-version` containing `24`
- [x] 2.6 Run `pnpm install`, review ignored build scripts, and allowlist only the required ones in `pnpm-workspace.yaml` (design D11); verify `pnpm install --frozen-lockfile` succeeds afterwards and that only `pnpm-lock.yaml` exists

## 3. Next.js configuration (design D1, D2, D6)

- [x] 3.1 Configure `next.config.ts`: `output: "export"`, `trailingSlash: true`, `images: { unoptimized: true }`, `typedRoutes: true`
- [x] 3.2 Set `tsconfig.json` `strict: true` and `noUncheckedIndexedAccess: true`, and keep the `@/*` alias

## 4. Lint, format and scripts (design D10)

- [x] 4.1 Add dev dependencies `prettier`, `prettier-plugin-tailwindcss`, `eslint-config-prettier`
- [x] 4.2 Write `eslint.config.mjs`: next core-web-vitals + typescript presets, `eslint-config-prettier` last, ignores for `.next/`, `out/`, `next-env.d.ts`, and a `no-restricted-imports` rule blocking `@/content/*` outside `src/lib/`
- [x] 4.3 Add `.prettierrc.json` (`endOfLine: "lf"`, Tailwind plugin, `tailwindStylesheet: "./src/app/globals.css"`) and `.prettierignore` (`.next/`, `out/`, `pnpm-lock.yaml`, `openspec/`, `.claude/`)
- [x] 4.4 Define scripts `dev`, `build`, `lint`, `typecheck`, `format`, `format:check`, `check`, `preview`; remove `start`

## 5. Site config, content layer and route registry (design D7, D8, D12)

- [x] 5.1 Create `src/lib/site.ts`: `siteName`; `siteUrl` validated from `NEXT_PUBLIC_SITE_URL` (throws a named error in production builds when missing or malformed; falls back to `http://localhost:3000` in dev); `indexingEnabled` from `SITE_INDEXING === "true"`
- [x] 5.2 Create `src/content/types.ts` (serializable `PageContent` with `slug`, `seo.title`, `seo.description` and placeholder body fields) and `src/content/pages.ts` with the `home` entry
- [x] 5.3 Create `src/lib/content.ts` with async `getPageContent(slug)` that throws an error naming the slug when no entry exists
- [x] 5.4 Create `src/lib/routes.ts` with the route registry containing only `/` (home)
- [x] 5.5 Add `.env.example` documenting `NEXT_PUBLIC_SITE_URL` and `SITE_INDEXING`

## 6. App shell and SEO plumbing (design D6, D9, D12)

- [x] 6.1 Rewrite `src/app/globals.css`: `@import "tailwindcss";`, `@theme` with neutral placeholder tokens (grayscale + one placeholder accent, system `--font-sans`), minimal base styles
- [x] 6.2 Rewrite `src/app/layout.tsx`: `lang="en"`, `metadataBase` from `siteUrl`, title template using `siteName`, `robots` noindex when indexing is disabled, `globals.css` import
- [x] 6.3 Rewrite `src/app/page.tsx` as an undesigned placeholder rendering the home content from `getPageContent("home")`, with `generateMetadata` (title, description, trailing-slash canonical) from the same entry
- [x] 6.4 Add placeholder `src/app/not-found.tsx`
- [x] 6.5 Add `src/app/sitemap.ts` (force-static) listing absolute trailing-slash URLs from the route registry
- [x] 6.6 Add `src/app/robots.ts` (force-static): `Disallow: /` unless indexing is enabled; when enabled, allow and reference the sitemap URL

## 7. Render blueprint (design D13)

- [x] 7.1 Write `render.yaml` defining static site `ai-job-recommendation-ui` (build command, `staticPublishPath: ./out`, `NODE_VERSION`, `NEXT_PUBLIC_SITE_URL`, `SITE_INDEXING=false`, PR previews off), checking key names against Render's current Blueprint spec; do not deploy

## 8. Project context

- [x] 8.1 Fill in `openspec/config.yaml` `context` (stack and versions, pnpm, static export on Render Free Tier, trailing-slash URLs, content-layer and route-registry conventions, token-only styling)

## 9. Verification

- [x] 9.1 `pnpm check` exits 0
- [x] 9.2 `pnpm build` without `NEXT_PUBLIC_SITE_URL` fails with an error naming the variable
- [x] 9.3 `NEXT_PUBLIC_SITE_URL=https://ai-job-recommendation-ui.onrender.com pnpm build` exits 0; `out/` contains `index.html`, `404.html`, `sitemap.xml`, `robots.txt`
- [x] 9.4 Inspect output: `robots.txt` has `Disallow: /`; `index.html` has a `noindex` meta tag and canonical `https://ai-job-recommendation-ui.onrender.com/`; `sitemap.xml` lists exactly that URL
- [x] 9.5 Rebuild with `SITE_INDEXING=true` and confirm `robots.txt` allows crawling and references the sitemap, and `noindex` is gone
- [x] 9.6 `pnpm preview`: `/` renders with styles; `/this-page-does-not-exist/` returns the not-found page with HTTP 404
- [x] 9.7 Negative checks: a temporary type error fails `pnpm typecheck`; a temporary unformatted file fails `pnpm format:check`; a temporary `@/content/pages` import in `src/app/page.tsx` fails `pnpm lint`; a temporary unknown slug fails the build. Revert all temporary edits
- [x] 9.8 Commit the foundation
