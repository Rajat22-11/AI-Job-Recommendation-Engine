# Tasks

## 1. Correct the main specs

- [x] 1.1 Sync the four delta specs (source-registry, job-source-fetching, job-fit-scoring, credential-pool) into `openspec/specs/`
- [x] 1.2 Run `openspec validate --specs` and confirm all seven main specs pass
- [x] 1.3 Check each corrected requirement against the code: the UI-owned `enabled` flag, `not_fetched` skipped rows, Naukri through Apify, word-ratio keyword matching, the senior-title penalty, the Gemini prompt file and pacing, and `.env` loading

## 2. Archived change documents

- [x] 2.1 Decide whether to correct the outdated text in the archived `proposal.md`, `design.md` and `tasks.md` of `add-programmatic-job-aggregation`; if yes, edit those files directly, not by delta (decided: no; the archived documents stay as they are)
- [ ] 2.2 (not required: 2.1 was decided no) If 2.1 is yes, append a "Post-implementation changes" group to the archived `tasks.md` recording: the Apify Naukri fetcher, the three new sources, keyword matching, the Gemini prompt file and pacing, `.env` loading, the pins (supabase 2.34.1, apify-shared 1.2.1, pydantic 2.14.3) and the trigger-script diagnostics; leave 16.4, 17.3, 17.5 and 17.6 unchecked
