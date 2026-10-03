## Purpose

Give the app a dark color scheme that is the default, with a visible user choice between Dark, Light and System that is remembered and applied before first paint.

## ADDED Requirements

### Requirement: Dark by default
A visitor with no saved theme choice SHALL see the dark theme on every page, including the login page and error pages, whatever the operating system's color-scheme preference.

#### Scenario: First visit on a light-mode device
- **WHEN** a visitor with no saved choice opens the app on a device set to light mode
- **THEN** pages render with the dark theme

### Requirement: Theme choice
The app SHALL offer a Dark, Light and System choice from a control reachable on every authenticated page and from the login page. System MUST follow the operating system's current color-scheme preference, including when it changes while the app is open. The choice MUST be saved in a cookie and persist across visits and sessions. The control MUST be operable by keyboard, have an accessible name, and indicate the current choice with text or an icon label, not color alone.

#### Scenario: Switch to Light
- **WHEN** the user chooses Light
- **THEN** the page switches to the light theme immediately, and later visits are light until the choice is changed

#### Scenario: System follows the device
- **WHEN** the user chooses System and the device is set to light mode
- **THEN** the app is light, and switches to dark if the device switches to dark

### Requirement: No flash of the wrong theme
The theme MUST be applied in the server-rendered HTML for Dark and Light choices, so the first paint already uses it. For System, the correct theme MUST be applied before the page is first painted. Navigating between pages MUST NOT cause a visible flash of the other theme.

#### Scenario: Reload in light theme
- **WHEN** the user has chosen Light and reloads
- **THEN** no dark-themed frame is shown before the light theme

### Requirement: Readable in both themes
Text and interactive components MUST meet WCAG 2.2 AA contrast in both themes: 4.5:1 for normal text and 3:1 for large text and for the boundaries of controls. Status meaning (new, saved, applied, skipped, warning, error, "Meets min") MUST remain readable and MUST NOT rely on color alone. Focus indicators MUST be visible in both themes.

#### Scenario: Warning banner in dark
- **WHEN** a source needs a login and the banner is shown in the dark theme
- **THEN** its text and link meet 4.5:1 contrast against the banner background

#### Scenario: Status badges
- **WHEN** a job card with "NEW", source and fit badges is shown in either theme
- **THEN** every badge's text meets 4.5:1 contrast and carries its text label

### Requirement: Browser chrome follows the theme
The page SHALL declare its color scheme to the browser so form controls, scrollbars and the mobile browser toolbar color match the active theme.

#### Scenario: Native controls
- **WHEN** the dark theme is active
- **THEN** native selects, checkboxes and scrollbars render in their dark variants
