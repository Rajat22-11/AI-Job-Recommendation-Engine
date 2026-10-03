## Why

On a phone the feed's filter panel is about ten controls tall, and "Apply filters" sits at the very bottom. Changing one filter means scrolling down to apply, then back up to read the results. The app is also light-only, while the owner wants dark as the everyday look.

## What Changes

- Feed filters apply themselves; there is no "Apply filters" button when JavaScript is available.
  - Selects (sort, minimum fit, salary, posted within) apply immediately on change.
  - Checkbox groups (status, role track, location, work mode, source) apply after about 700 ms without further changes, so several ticks produce one request.
  - The search box applies after about 400 ms without typing, or on Enter.
  - A spinner and a dimmed result list show while the request is pending, for exactly as long as it takes (no fixed 1 s delay).
  - Applying keeps the scroll position and keeps the mobile panel open.
- Active filters appear as removable chips above the results.
- "Reset filters" stays. The form remains a plain GET form, and without JavaScript a submit button is still available.
- Dark mode, on by default. A Dark / Light / System toggle in the header stores the choice in a cookie, so the server renders the right theme on first paint with no flash.
- A dark palette is added through the existing `@theme` tokens, a toast inverse token replaces hardcoded white-on-text, and the viewport `colorScheme` / `themeColor` follow the theme.
- `openspec/config.yaml` no longer says "light theme only".
- **BREAKING (spec-level):** supersedes two `implement-ui` requirements: the explicit-submit filter form in `job-feed`, and "Light theme only" in `app-hosting`.

## Capabilities

### New Capabilities
- `feed-auto-filter`: filter changes apply automatically with debounce, pending feedback and active-filter chips, with a no-JavaScript fallback.
- `color-theme`: dark-by-default theming with a Dark / Light / System preference stored in a cookie and rendered server-side.

### Modified Capabilities
- `app-hosting`: the "Light theme only" requirement is removed in favour of `color-theme`.

`job-feed` "URL-driven filters" is unchanged: it doesn't mention how filters are submitted, so automatic applying (`feed-auto-filter`) adds to it without contradicting it. Both depend on `implement-ui` being synced first.

## Impact

- Code: [filter-panel.tsx](src/components/filter-panel.tsx) (becomes a client island), a new theme toggle component, the app layout header, the root layout, [globals.css](src/app/globals.css), [ui.ts](src/components/ui.ts), [toast.tsx](src/components/toast.tsx), and tracker / global-error styling that uses `text-white`.
- No schema, database, API or dependency changes. No new packages are expected.
- Config: `openspec/config.yaml` UI line.
- Verification: `pnpm check`, `pnpm build`, a Playwright pass at 360 px and desktop in both themes, and the frontend-design contrast checker on the dark palette.
