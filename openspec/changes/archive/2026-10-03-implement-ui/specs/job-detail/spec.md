## Purpose

A dedicated page per job that shows everything known about the posting and lets the user record and edit their application: status, date, resume version, referral contact and notes.

## ADDED Requirements

### Requirement: Job detail route
Each job SHALL have a page at `/jobs/<id>` that shows every field on the feed card, plus:
- the full `summary`
- employment type
- the salary range in LPA when known
- every source link, labelled with the source name
- `first_seen_at` and `last_seen_at`

The page title MUST include the job title and company. The page MUST work for inactive jobs too, showing a notice that the posting is no longer active along with its last-seen date.

#### Scenario: Opening from the feed
- **WHEN** the user taps a job title in the feed
- **THEN** that job's detail page opens with its summary and all source links

#### Scenario: Inactive job
- **WHEN** the user opens the detail page of a job with `is_active = false`
- **THEN** the page shows "No longer active", the last-seen date, and the rest of the job details

### Requirement: Return to the originating feed view
The detail page SHALL offer a "Back to feed" link that returns to the feed view the user came from, with the same filters, sort and page. When there is no originating view, for example a bookmarked detail URL, it MUST link to the default feed.

#### Scenario: Back keeps filters
- **WHEN** the user opens a job from `/?track=data&page=2` and then follows "Back to feed"
- **THEN** they land on `/?track=data&page=2`

### Requirement: Detail page actions
The detail page SHALL show the same "Apply" link (new tab, `noopener noreferrer`) and the same quick Save / Applied / Skip actions as the feed card.

#### Scenario: Apply from detail
- **WHEN** the user taps "Apply" on the detail page
- **THEN** `apply_url` opens in a new tab

### Requirement: Editable application panel
The detail page SHALL contain a form for the application with these fields:
- status: one of New, Saved, Applied, Interview, Offer, Rejected, Skipped
- applied-on date
- resume version, at most 200 characters
- referral contact, at most 200 characters
- notes, at most 5000 characters

Saving with any status other than New MUST create or update the job's application record and set `updated_at` to the current time. Changing the status to Applied while the applied-on date is empty MUST fill in today's IST date. Saving with status New MUST remove the application record, but only after the user confirms that the notes and other fields will be discarded. The form MUST work without client-side JavaScript. After saving, it MUST show a "Saved" confirmation. A validation failure MUST show the message next to the field and keep everything the user entered.

#### Scenario: First save creates the record
- **WHEN** a job with status `new` is saved with status Interview and notes "Round 1 on Fri"
- **THEN** an application record exists with status `interview` and those notes, and "Saved" is shown

#### Scenario: Applied fills the date
- **WHEN** the status is changed to Applied with an empty applied-on date and saved
- **THEN** `applied_on` is stored as today's IST date

#### Scenario: Reset to new
- **WHEN** the user picks status New, saves, and confirms the warning
- **THEN** the application record is deleted and the job shows status `new` everywhere

#### Scenario: Notes too long
- **WHEN** notes longer than 5000 characters are submitted
- **THEN** nothing is saved, an error is shown next to notes, and the entered text is still in the form

#### Scenario: Future applied date
- **WHEN** an applied-on date later than today (IST) is submitted
- **THEN** nothing is saved and the date field shows "Date can't be in the future"
