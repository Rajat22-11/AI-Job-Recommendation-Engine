## Purpose

Make changing a feed filter a one-step action: filters apply on their own, the user sees that a request is in progress, and the applied filters stay visible, without scrolling to a submit button.

## ADDED Requirements

### Requirement: Filters apply automatically
With JavaScript available, changing a feed filter control SHALL update the feed to match without the user pressing a submit button, and the filter panel MUST NOT show an "Apply filters" button. Every automatic apply MUST reset to page 1 and keep all other filter values. Selects (sort, minimum fit, salary, posted within) MUST apply immediately on change. Checkbox groups (status, role track, location, work mode, source) MUST apply after about 700 ms without a further change, so a run of ticks produces one update. The search box MUST apply after about 400 ms without typing, or immediately on Enter. The URL MUST reflect the applied filters, so a reload or bookmark shows the same view.

#### Scenario: Select applies immediately
- **WHEN** the user changes "Sort by" to "Newest"
- **THEN** the feed reloads sorted by newest without any further action, and the URL contains `sort=newest`

#### Scenario: Several checkboxes, one update
- **WHEN** the user ticks "Pune", "Remote (India)" and "Hybrid" within 700 ms of each other
- **THEN** exactly one update is made, after the last tick, with all three selected

#### Scenario: Typing in search
- **WHEN** the user types "python" and pauses for 400 ms
- **THEN** the feed shows jobs matching "python"

#### Scenario: Back to page 1
- **WHEN** the user is on page 3 and changes any filter
- **THEN** the feed shows page 1 of the new result set

### Requirement: Pending feedback
While an automatic apply is in progress the feed MUST show a spinner near the result count and MUST dim the result list, and MUST remove both when the new results are shown. The spinner MUST last exactly as long as the request, with no fixed minimum or maximum delay. The result count region MUST announce the new count to assistive technology when results arrive. If the request fails, the app's error page MUST be shown with a way to retry.

#### Scenario: Slow response
- **WHEN** the server takes 3 seconds to respond to a filter change
- **THEN** the spinner and dimmed list stay visible for the whole 3 seconds, then disappear when the new results appear

#### Scenario: Fast response
- **WHEN** the server responds in 150 ms
- **THEN** the results update with no lingering spinner

#### Scenario: Failed request
- **WHEN** the filter request fails
- **THEN** the spinner is gone and the app's error page is shown with a way to retry

### Requirement: Position is preserved
Applying a filter automatically MUST NOT scroll the page, and MUST NOT collapse the filter panel on narrow screens. Keyboard focus MUST stay on the control the user changed.

#### Scenario: Filtering from the bottom of the panel
- **WHEN** the user, with the mobile panel open and scrolled to "Source", ticks a source
- **THEN** the panel stays open at the same scroll position, focus stays on that checkbox, and the results update

### Requirement: Active filters as chips
The feed SHALL list each active non-default filter as a chip above the results, with a control that removes just that filter and applies immediately. When no filter differs from the default view, no chips are shown. Each chip's remove control MUST have an accessible name that says which filter it removes.

#### Scenario: Remove one filter
- **WHEN** filters are `loc=pune` and `fit=4` and the user removes the "Pune" chip
- **THEN** the feed shows results for `fit=4` only, and the "Pune" chip is gone

#### Scenario: Default view
- **WHEN** the user opens `/` with no parameters
- **THEN** no filter chips are shown

### Requirement: Reset stays available
A "Reset filters" control SHALL remain in the filter panel and return the feed to the default view.

#### Scenario: Reset
- **WHEN** the user activates "Reset filters"
- **THEN** the feed shows the default view and all chips disappear

### Requirement: Works without JavaScript
Without JavaScript the filter panel MUST remain a working form: a visible submit button MUST be present, and submitting it MUST apply all selected filters and return to page 1. With JavaScript running, that button MUST NOT be shown or focusable.

#### Scenario: JavaScript disabled
- **WHEN** the user changes three filters with scripting disabled and presses "Apply filters"
- **THEN** the feed shows page 1 with all three applied

### Requirement: Touch target size
Filter controls and the chip remove controls MUST be at least 44 by 44 CSS pixels (or sit within a 44 pixel target) and usable at 360 px viewport width without horizontal scrolling.

#### Scenario: Narrow viewport
- **WHEN** the feed is open at 360 px width with several chips shown
- **THEN** the chips wrap onto more lines, nothing scrolls horizontally, and each remove control is tappable
