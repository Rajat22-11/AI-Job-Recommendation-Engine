# LinkedIn influencer profiles

Some LinkedIn creators post job openings in a fixed template, for example:

```
Oracle IS HIRING!
Role: Software Engineer - I (Application engineer)
Experience: 0-3 year's
Location : Bengaluru, India
Skills Required :
SQL, PL-SQL, ...
Apply link :
https://lnkd.in/guxXTkA9
```

The pipeline reads the newest posts of each listed profile through the Apify actor `harvestapi/linkedin-profile-posts`. It needs no LinkedIn account or cookies. It keeps only hiring posts and turns each into a job, with the `lnkd.in` link resolved to the employer's own apply page.

## Add a profile

Add an entry to `config/sources.yaml`:

```yaml
  - id: li_firstname_lastname          # unique; start with li_
    name: "LinkedIn: Firstname Lastname"
    base_url: https://www.linkedin.com/in/their-profile-slug/
    fetch_method: linkedin_profile_posts
    profile_url: https://www.linkedin.com/in/their-profile-slug/
    posts_per_run: 3                   # newest posts read per run
    credential_service: apify
    enabled: true
```

Then check it: `python -m job_aggregator.registry.check_source_registry`. On the next run the profile is added to the database `sources` table automatically.

**Cost:** Apify charges per post fetched, about $1.50 per 1,000 posts at the time of writing. `linkedin.max_posts_per_run` in `config/settings.yaml` caps the total across all profiles per run (default 15). When the cap is reached, the remaining profiles are recorded as skipped for that run. With 2 profiles × 3 posts × 30 days, that is about 180 posts, roughly $0.30 a month, well inside the free $5 monthly credit.

## What happens to each post

| Post | Outcome | Recorded in `linkedin_seen_posts` as |
|---|---|---|
| Has a hiring marker and a link, and a Role line can be read | Becomes a job; the post URL is stored as the job's source link | `job_created` |
| Has a hiring marker and a link but no Role (or no company) | No job; kept for review | `unparsed` |
| No hiring marker, or no link (e.g. a study cheatsheet) | Ignored, not an error | `ignored` |
| Already in `linkedin_seen_posts` | Skipped | (unchanged) |

If an `lnkd.in` link cannot be resolved, the job is still stored with the short link as its apply URL, and its summary says the link is unresolved.

## When an influencer words posts differently

Recognition is driven by `config/settings.yaml`, not code:

- `linkedin.hiring_markers`: phrases that mark a hiring post (case-insensitive), for example `is hiring` or `we're hiring`. Add the influencer's phrase here.
- `linkedin.field_aliases`: label words for each field. A line `Label: value` (or `Label - value`) is read when the label matches an alias. A label with nothing after the colon takes the following lines up to a blank line. For example, if a creator writes `Designation: ...`, `designation` is already under `role`; if they write `Opening: ...`, add `opening` to `role`.
- The company is the `company` label if present, otherwise the text before the hiring marker (`Oracle IS HIRING!` gives `Oracle`).

After changing these, run the LinkedIn tests (`pytest tests/test_linkedin.py`). To cover the new wording, add the post's text as a fixture in `tests/fixtures/`.
