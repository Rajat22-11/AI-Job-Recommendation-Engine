## 1. Theme tokens and palette

- [x] 1.1 Add dark palette overrides under `[data-theme="dark"]` in globals.css for canvas, surface, muted, border, border-strong, text, text-muted, accent, accent-hover, accent-soft and the success / warning / danger pairs; keep light values as the `@theme` defaults
- [x] 1.2 Add `on-accent` and `inverse` / `on-inverse` tokens for both themes, and set `color-scheme` per theme
- [x] 1.3 Replace hardcoded `text-white` in ui.ts, toast.tsx, tracker/page.tsx and global-error.tsx with the new tokens
- [x] 1.4 Run the frontend-design contrast checker on every text/background and control-border pair in both themes; adjust values until normal text is at least 4.5:1 and borders and focus ring at least 3:1

## 2. Theme preference and toggle

- [x] 2.1 Add a small theme helper (cookie name, allowed values, default `dark`, validation of unknown values)
- [x] 2.2 Read the cookie in the root layout; set `data-theme` and `colorScheme` on `<html>`; make the viewport `colorScheme` / `themeColor` follow the theme
- [x] 2.3 Add the blocking head script that resolves `system` before first paint, and an OS-change listener while the app is open
- [x] 2.4 Build the Theme toggle client component (Dark / Light / System, labelled, keyboard operable, current choice shown as text); it writes the cookie (path `/`, one year, SameSite Lax) and updates `data-theme` immediately
- [x] 2.5 Place the toggle in the app header beside Log out, and on the login page; confirm the 44 px target and a clean 360 px header
- [x] 2.6 Make global-error.tsx work with the dark default tokens without reading the cookie

## 3. Auto-applying filters

- [x] 3.1 Add a pending-state provider shared by the filter panel and the results section, driven by `useTransition`
- [x] 3.2 Convert the filter panel into a client island that builds the query from `FormData`, omits `page`, keeps the `seen` hidden input, and calls `router.replace(url, { scroll: false })` in a transition
- [x] 3.3 Implement the debounce policy: selects at once, checkboxes after 700 ms, search after 400 ms or on Enter, one shared timer, cleared on unmount
- [x] 3.4 Remove the visible "Apply filters" button; keep a `<noscript>` submit button so the form still submits without JavaScript
- [x] 3.5 Keep the mobile `<details>` open and the focus on the changed control while applying; re-sync inputs when the URL changes from outside (chip removal, Reset, New today)
- [x] 3.6 Show the spinner next to the result count and dim the list with `aria-busy` while pending; keep the existing `aria-live` count announcement
- [x] 3.7 Render removable active-filter chips as links above the results (accessible name "Remove filter: ..."), shown only for non-default values; wrap cleanly at 360 px with 44 px targets
- [x] 3.8 Keep "Reset filters" in the panel, styled as a secondary action

## 4. Tests

- [x] 4.1 Unit test the query-building helper (omits `page` and defaults, repeated keys for checkbox groups, keeps `seen`) against `parseFeedParams` round-trips
- [x] 4.2 Unit test the theme helper (valid values, invalid and missing cookie fall back to dark)
- [x] 4.3 Unit test the chip derivation (no chips for the default view; one chip per non-default value; each removal link drops only that value)

## 5. Config and verification

- [x] 5.1 Update the UI line in openspec/config.yaml from light-only to dark by default with a Dark / Light / System choice
- [x] 5.2 Run `pnpm check` and `pnpm build`; fix anything they report
- [x] 5.3 With playwright-cli, check the feed, filters (open), a job detail, tracker, sources, settings and login at 360 px and at desktop width, in dark and light; save screenshots outside the repo
- [x] 5.4 With playwright-cli, verify behavior: select applies at once; several ticks make one request; search debounce; spinner lasts the request; scroll position, panel and focus are kept; a chip removes one filter; Reset works; the theme toggle persists after reload with no flash; with JavaScript disabled the form still submits (no-JS: the form markup and noscript button are verified; the page itself needs JS today because of loading.tsx streaming, see design D6)
- [x] 5.5 Remove the `.playwright-cli/` scratch folder, or add it to .gitignore, so it is not committed
