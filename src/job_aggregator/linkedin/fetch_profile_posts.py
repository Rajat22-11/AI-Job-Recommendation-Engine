"""Fetch the newest posts of one LinkedIn profile through the Apify actor, using the credential pool.

Actor input (confirmed from the actor's published schema): targetUrls, maxPosts, postedLimit,
includeReposts, includeQuotePosts. Output field names are not published; `profile_post_from_item`
accepts the likely names and is to be confirmed by the Apify spike (tasks.md 17.2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from job_aggregator.apify.run_actor import ActorRunner, run_apify_actor
from job_aggregator.credentials.credential_pool import CredentialPool, rotate_on_quota_error


@dataclass(frozen=True)
class ProfilePost:
    post_url: str
    text: str
    posted_at: date | None


def _first(item: dict, *keys: str) -> Any:
    for key in keys:
        value = item.get(key)
        if value:
            return value
    return None


def _posted_date(value: Any) -> date | None:
    if isinstance(value, dict):
        value = value.get("date") or value.get("timestamp")
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value / (1000 if value > 10**11 else 1), UTC).date()
    if isinstance(value, str) and len(value) >= 10:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def profile_post_from_item(item: dict) -> ProfilePost | None:
    post_url = _first(item, "linkedinUrl", "postUrl", "url", "shareUrl")
    text = _first(item, "content", "text", "commentary", "postText")
    if not post_url or not text:
        return None
    return ProfilePost(post_url=str(post_url), text=str(text),
                       posted_at=_posted_date(_first(item, "postedAt", "postedDate", "date")))


class ApifyProfilePostClient:
    def __init__(self, pool: CredentialPool, actor_id: str, runner: ActorRunner = run_apify_actor) -> None:
        self._pool = pool
        self._actor_id = actor_id
        self._runner = runner

    def fetch_profile_posts(self, profile_url: str, max_posts: int) -> list[ProfilePost]:
        """Return at most `max_posts` newest posts of one profile, without cookies or a LinkedIn account."""
        run_input = {
            "targetUrls": [profile_url],
            "maxPosts": max_posts,
            "postedLimit": "week",
            "includeReposts": False,
            "includeQuotePosts": True,
        }
        items = rotate_on_quota_error(self._pool, lambda token: self._runner(token, self._actor_id, run_input))
        posts = [post for item in items if (post := profile_post_from_item(item))]
        return posts[:max_posts]
