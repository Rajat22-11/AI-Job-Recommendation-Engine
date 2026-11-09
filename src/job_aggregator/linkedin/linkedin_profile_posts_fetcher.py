"""`JobFetcher` for `linkedin_profile_posts` registry entries.

For each enabled profile: fetch the newest posts (within the per-run cap), skip posts already
processed, keep hiring posts, resolve their short links, and return them as raw listings. Ignored and
unparsed posts are recorded at once; posts that become jobs are recorded by the pipeline after storing.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from job_aggregator.domain.models import FetchResult, RawListing, SearchConfig, SourceStatus
from job_aggregator.linkedin.fetch_profile_posts import ApifyProfilePostClient, ProfilePost
from job_aggregator.linkedin.parse_hiring_post import ParsedHiringPost, PostKind, parse_hiring_post
from job_aggregator.linkedin.resolve_short_link import ResolvedLink, resolve_short_link
from job_aggregator.registry.source_entry import SourceEntry
from job_aggregator.settings.app_settings import LinkedInSettings

UNRESOLVED_NOTE = "Apply link could not be resolved; the LinkedIn short link is stored instead."

SeenPostLookup = Callable[[list[str]], set[str]]
PostOutcomeRecorder = Callable[[str, str, str, str | None], None]
"""(post_url, source_id, outcome, note) -> None"""
LinkResolver = Callable[[str], ResolvedLink]


@dataclass
class PostBudget:
    """Posts still allowed in this run across all profiles."""

    remaining: int

    def take(self, wanted: int) -> int:
        granted = max(0, min(wanted, self.remaining))
        self.remaining -= granted
        return granted


def hiring_post_to_listing(
    post: ProfilePost, parsed: ParsedHiringPost, link: ResolvedLink, source_id: str
) -> RawListing:
    details = [f"Experience: {parsed.experience}" if parsed.experience else "",
               f"Batch: {parsed.batch}" if parsed.batch else "",
               f"Stipend: {parsed.stipend}" if parsed.stipend else "",
               "" if link.resolved else UNRESOLVED_NOTE]
    experience_text = " ".join(part for part in (parsed.experience, f"Batch {parsed.batch}" if parsed.batch else "")
                               if part) or None
    return RawListing(
        source_id=source_id,
        title=parsed.role or "",
        company=parsed.company or "",
        apply_url=link.url,
        source_url=post.post_url,
        location=parsed.location,
        description=" | ".join(d for d in details if d) + "\n\n" + post.text,
        salary_text=parsed.stipend,
        employment_type="internship" if parsed.role and "intern" in parsed.role.lower() else None,
        experience_text=experience_text,
        skills=parsed.skills,
        posted_at=post.posted_at,
        apply_url_kind="employer" if link.resolved else "board",
    )


class LinkedInProfilePostsFetcher:
    def __init__(
        self,
        client: ApifyProfilePostClient,
        settings: LinkedInSettings,
        find_seen_posts: SeenPostLookup,
        record_post_outcome: PostOutcomeRecorder,
        link_resolver: LinkResolver | None = None,
    ) -> None:
        self._client = client
        self._settings = settings
        self._find_seen_posts = find_seen_posts
        self._record = record_post_outcome
        self._resolve = link_resolver or (
            lambda url: resolve_short_link(url, timeout_seconds=settings.short_link_timeout_seconds)
        )
        self.budget = PostBudget(settings.max_posts_per_run)

    def fetch(self, source: SourceEntry, search_config: SearchConfig) -> FetchResult:
        wanted = int(source.setting("posts_per_run", self._settings.default_posts_per_profile))
        granted = self.budget.take(wanted)
        if granted == 0:
            return FetchResult(source_id=source.id, status=SourceStatus.SKIPPED,
                               message=f"per-run post cap of {self._settings.max_posts_per_run} reached")
        posts = self._client.fetch_profile_posts(source.setting("profile_url"), granted)
        seen = self._find_seen_posts([post.post_url for post in posts])
        listings: list[RawListing] = []
        counts = {"seen": 0, "ignored": 0, "unparsed": 0, "unresolved": 0}
        for post in posts:
            if post.post_url in seen:
                counts["seen"] += 1
                continue
            parsed = parse_hiring_post(post.text, self._settings)
            if parsed.kind is PostKind.IGNORED:
                counts["ignored"] += 1
                self._record(post.post_url, source.id, "ignored", parsed.reason)
                continue
            if parsed.kind is PostKind.UNPARSED:
                counts["unparsed"] += 1
                self._record(post.post_url, source.id, "unparsed", parsed.reason)
                continue
            link = self._resolve(parsed.apply_link or "")
            counts["unresolved"] += 0 if link.resolved else 1
            listings.append(hiring_post_to_listing(post, parsed, link, source.id))

        message = (f"{len(posts)} post(s) fetched; {len(listings)} hiring; {counts['seen']} already seen; "
                   f"{counts['ignored']} ignored; {counts['unparsed']} unparsed; "
                   f"{counts['unresolved']} link(s) unresolved")
        if granted < wanted:
            message += f"; limited to {granted} of {wanted} by the per-run cap"
        status = SourceStatus.PARTIAL if granted < wanted else SourceStatus.SUCCEEDED
        return FetchResult(source_id=source.id, status=status, listings=listings, message=message)
