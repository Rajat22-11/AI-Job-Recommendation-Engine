## Context

See proposal.md for motivation. Current state:

- The feed is a Server Component page. [filter-panel.tsx](src/components/filter-panel.tsx) is a server-rendered plain GET form (`action="/" method="get"`) inside a `<details>`, with "Apply filters" and "Reset filters" at the bottom. `parseFeedParams` and `serializeFeedParams` / `feedHref` in `src/lib/feed/params.ts` already parse and build the URL, and unknown values are ignored.
- Styling goes through `@theme` tokens in [globals.css](src/app/globals.css), which resets `--color-*` and defines a light palette. `ui.ts` holds shared class strings. `text-white` is hardcoded on the primary button, the toast, the tracker status chip and the global-error button. The root layout hardcodes `colorScheme: "light"` and `themeColor: "#ffffff"`.
- Project constraints: minimal client JS, forms must work without JavaScript, no raw hex in markup, 44 px targets, usable at 360 px, no new directories or dependencies unless needed.

## Goals / Non-Goals

**Goals:**
- Filter changes feel instant and never need a scroll to a submit button, with no change to the URL contract or the server query code.
- Theme is correct on first paint, defaults to dark, and is user-switchable.

**Non-Goals:**
- No change to which filters exist, their defaults, or how results are queried.
- No live result count per tick (no extra count query), no bottom-sheet drawer.
- No per-page or per-device theme settings, no database storage of the theme.

## Decisions

### D1. Filter panel becomes one client island that navigates with `router.replace`
The panel stays a real `<form method="get">` (the no-JS fallback), but gains a small client wrapper. On a `change` or `input` event it reads the form with `FormData`, builds the query string, and calls `router.replace(url, { scroll: false })` inside `startTransition`. `isPending` drives the spinner and the dimmed results.

- Reuse `serializeFeedParams` rules: omit `page`, omit defaults where the existing code does, keep the hidden `seen=24h` input. Building the query from the form's fields (not from React state) keeps one source of truth, and the server's `parseFeedParams` stays the only parser.
- `replace` rather than `push`: each tick would otherwise add a history entry, and Back would walk through every intermediate state.
- Alternatives: (a) `<form>.requestSubmit()` on change gives a full page load, flicker, and scroll reset, so no. (b) Client-side fetch with local result state would duplicate the server rendering and break the URL contract, so no. (c) A sticky "Show N jobs" bar needs a count endpoint per change, which is heavier; rejected for this change.

### D2. Debounce policy by control type
Selects fire at once; checkboxes after 700 ms; search after 400 ms or on Enter. One shared timer per form: any new event clears the pending timer, and a select or Enter flushes it immediately, so the latest state always wins and a quick tick-then-select produces one request. A pending-timer cleanup on unmount prevents late navigation.

- Why not apply checkboxes at once: multi-select groups are ticked in runs, and each request is a server round trip plus a Supabase query on a free Render instance with cold starts.
- Why 700 ms not 1 s: long enough for a second tick, short enough not to feel stuck. The spinner reflects real request time, not a fixed delay.

### D3. Pending UI sits in the page, not only in the panel
The result count and list live in the page, while the panel is a sibling. A tiny client component, a pending context provider wrapping both, shares `isPending` so the panel can show the spinner and the results section can dim (`aria-busy`, reduced opacity, `pointer-events` left on so links still work). The count region keeps `aria-live="polite"`. A failed navigation shows the existing `(app)/error.tsx` boundary, which has a retry control; while pending, the transition keeps the old results on screen.

- Alternative: `loading.tsx`. The existing [loading.tsx](src/app/(app)/loading.tsx) shows a full skeleton on every navigation and would flash the list away for fast requests, so the transition's pending state is preferred for in-place filter changes.

### D4. Keep position and focus
With `scroll: false` and a form that is not remounted (it receives `defaultValue`s from the server), the scroll position and the focused checkbox survive. The panel's `<details>` open state is kept in the island, so it is not reset when props change. The form needs a stable `key` so React does not remount it on each navigation; checkbox `defaultChecked` is only read at mount, so the client state is the truth while the user is interacting, and the server-sent values are authoritative on reload, Reset, and chip removal.

- Risk: the URL changes (chip removed, Reset) must update the form's inputs. Mitigation: key the form by the serialized filters only for those external changes, not for changes the form itself caused.

### D5. Active filter chips are links
Chips are rendered by the server page as ordinary `<Link>`s built with `feedHref(filters, { ...removed })`. That gives them no-JS support and prefetching for free, and they share the pending state through the `Link`'s navigation. Each has an accessible name like "Remove filter: Pune". Only values that differ from `DEFAULT_FILTERS` produce chips.

### D6. No-JS fallback via a `<noscript>` submit button
The submit button lives in a `<noscript>` block inside the form, so it is rendered only when scripting is off, and never flashes before hydration. With JavaScript, Enter in the search box submits the form (the only text field blocks implicit submission), and the handler applies it at once. Known limit, not introduced here: the feed streams behind `loading.tsx`, and streamed content needs JavaScript to be swapped in, so a no-JS browser sees an empty page until that is addressed separately.

### D7. Theme is a cookie read on the server, applied on `<html>`
- A `theme` cookie holds `dark`, `light` or `system`; missing or invalid means `dark`. The root layout reads it with `cookies()` and sets `data-theme` and `style={{ colorScheme }}` on `<html>`. Reading cookies makes the layout dynamic, which is fine: the app is already request-time, and every route behind the gate is dynamic.
- For `system`, an inline blocking script in `<head>` runs before paint and sets `data-theme` from `matchMedia("(prefers-color-scheme: dark)")`; a small client toggle also listens for OS changes while open. Dark and Light need no script.
- Palette: the light token values stay in `@theme`. Dark values override the same CSS variables under `[data-theme="dark"]` in `globals.css`, so components keep using `bg-surface`, `text-text` and so on with no `dark:` variants and no raw hex in markup. This matches the repo's token convention.
- Alternatives: (a) `prefers-color-scheme` only, which cannot default to dark over a light OS and has no toggle; (b) localStorage plus a script, which gives a flash on first paint for server-rendered markup and cannot be read on the server; (c) next-themes, a new dependency for a task a cookie and about 20 lines handle.

### D8. Dark palette and token additions
- Soft near-black canvas, slightly lighter surfaces, a lighter blue accent so text on it and on `accent-soft` meets 4.5:1. Status colors (`success`, `warning`, `danger` and their `*-soft`) get dark-appropriate pairs. Final values are chosen with the frontend-design contrast checker and recorded in the CSS.
- New tokens: `--color-on-accent` (text on accent and danger fills) replacing hardcoded `text-white` on those fills, and `--color-inverse` / `--color-on-inverse` for the toast so it stays high-contrast in both themes. The button, toast, tracker chip and global-error usages move to the tokens.
- `layout.tsx` `viewport` becomes `generateViewport` using the same cookie for `colorScheme` and `themeColor`.
- `global-error.tsx` replaces the root layout and cannot read the cookie reliably, so it uses the dark default token values.

### D9. Toggle placement
A small client "Theme" control (a labelled select or three-way radio group, the choice shown as text) in the app header next to Log out, and a compact version on the login page. It writes the cookie (`path=/`, one year, `SameSite=Lax`) with `document.cookie`, and updates `data-theme` immediately without a reload. It holds no secrets and is not security-sensitive, so no httpOnly or Server Action is needed.

### D10. Config and spec housekeeping
`openspec/config.yaml` UI line changes from "light theme only" to "dark theme by default with Dark/Light/System choice". The two superseded `implement-ui` requirements are reconciled when specs are synced (see proposal).

## Risks / Trade-offs

- [Unmounted debounce or stale timer fires a navigation after leaving the page] → clear the timer on unmount and on every new event; flush only one request.
- [Form inputs out of sync with the URL after chip removal or Reset] → re-key the form from server-supplied filters only for external changes (D4).
- [Rapid changes race: an older navigation resolves after a newer one] → `router.replace` in a transition supersedes the older one, and the URL is the source of truth, so the last request wins.
- [Flash of light theme for System on a dark OS, or the reverse] → blocking head script for System only; Dark and Light are server-rendered.
- [Cookie reads make every page dynamic] → already true for the whole gated app; the login page is the only other visitor-facing page and it is cheap.
- [Dark status colors lose meaning] → every status keeps its text label, and contrast is verified with the checker rather than eyeballed.
- [A client island adds JavaScript] → it is one small component plus a toggle, in line with "client islands only where needed"; no new dependency.

## Migration Plan

No data or schema migration. Ship in one deploy. Existing visitors have no theme cookie, so they get the dark default. Rollback is reverting the commit; the leftover `theme` cookie is harmless.

## Open Questions

- Exact dark palette values, settled during implementation against the contrast checker.
- Whether the toggle is a select or a segmented control; either meets the spec, so it can be decided when it is built.
