from datetime import UTC, date, datetime

import httpx
import pytest

from job_aggregator.credentials.credential_pool import CredentialPool
from job_aggregator.domain.models import SourceStatus
from job_aggregator.linkedin.fetch_profile_posts import ApifyProfilePostClient, profile_post_from_item
from job_aggregator.linkedin.linkedin_profile_posts_fetcher import LinkedInProfilePostsFetcher
from job_aggregator.linkedin.parse_hiring_post import PostKind, parse_hiring_post
from job_aggregator.linkedin.resolve_short_link import ResolvedLink, destination_from_interstitial, resolve_short_link
from job_aggregator.persistence.job_repository import JobRepository
from job_aggregator.persistence.seen_post_repository import SeenPostRepository
from job_aggregator.processing.normalize_listing import normalize_listing
from job_aggregator.registry.source_entry import SourceEntry
from tests.conftest import FIXTURES
from tests.fakes import FakeDatabaseClient

NOW = datetime(2026, 11, 8, 15, 0, tzinfo=UTC)


def _post_text(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def _profile(source_id="li_swadesh_kumar", posts_per_run=3, enabled=True):
    return SourceEntry(id=source_id, name=source_id, fetch_method="linkedin_profile_posts", enabled=enabled,
                       settings={"profile_url": f"https://www.linkedin.com/in/{source_id}/",
                                 "posts_per_run": posts_per_run})


def _items():
    return [
        {"linkedinUrl": "https://www.linkedin.com/posts/oracle-1", "content": _post_text("post_oracle_hiring.txt"),
         "postedAt": {"date": "2026-11-07T10:00:00Z"}},
        {"linkedinUrl": "https://www.linkedin.com/posts/sql-2", "content": _post_text("post_sql_cheatsheet.txt")},
        {"linkedinUrl": "https://www.linkedin.com/posts/stripe-3", "content": _post_text("post_stripe_intern.txt")},
    ]


# ---------- parsing ----------

def test_oracle_post_accepted_with_fields(app_settings):
    parsed = parse_hiring_post(_post_text("post_oracle_hiring.txt"), app_settings.linkedin)
    assert parsed.kind is PostKind.HIRING
    assert parsed.company == "Oracle"
    assert parsed.role == "Software Engineer - I (Application engineer)"
    assert parsed.experience == "0-3 year's"
    assert parsed.location == "Bengaluru, India"
    assert parsed.skills[:2] == ["SQL", "PL-SQL"] and "Programming (e.g.; Python; Java; C++)" in parsed.skills
    assert parsed.apply_link == "https://lnkd.in/guxXTkA9"
    assert parsed.stipend is None  # optional line absent, post still accepted


def test_stripe_post_accepted_with_batch_and_stipend(app_settings):
    parsed = parse_hiring_post(_post_text("post_stripe_intern.txt"), app_settings.linkedin)
    assert parsed.kind is PostKind.HIRING
    assert (parsed.company, parsed.role) == ("Stripe", "Software Engineer - I (Intern)")
    assert parsed.batch == "2028/2027" and parsed.stipend == "1.2-1.5 lakh/month"
    assert parsed.apply_link == "https://lnkd.in/dGjHcMMa"


def test_cheatsheet_post_ignored(app_settings):
    parsed = parse_hiring_post(_post_text("post_sql_cheatsheet.txt"), app_settings.linkedin)
    assert parsed.kind is PostKind.IGNORED


def test_marker_and_link_without_role_is_unparsed(app_settings):
    text = "Acme IS HIRING!\nLots of roles open across teams.\nApply link: https://lnkd.in/abc123"
    parsed = parse_hiring_post(text, app_settings.linkedin)
    assert parsed.kind is PostKind.UNPARSED and "role" in parsed.reason


def test_marker_without_link_is_ignored(app_settings):
    assert parse_hiring_post("Acme IS HIRING!\nRole: Dev", app_settings.linkedin).kind is PostKind.IGNORED


# ---------- short links ----------

@pytest.mark.parametrize(
    ("page", "expected"),
    [("lnkd_oracle.html", "https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/job/344313/"),
     ("lnkd_stripe.html", "https://stripe.com/careers/listing/software-engineer-intern/8031833")],
)
def test_saved_interstitial_pages_resolve_to_employer(page, expected):
    html = (FIXTURES / page).read_text(encoding="utf-8")
    assert destination_from_interstitial(html) == expected
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=html)))
    assert resolve_short_link("https://lnkd.in/xyz", client) == ResolvedLink(expected, resolved=True)


def test_failed_fetch_keeps_short_link():
    def fail(request):
        raise httpx.ConnectError("down")

    client = httpx.Client(transport=httpx.MockTransport(fail))
    assert resolve_short_link("https://lnkd.in/xyz", client) == ResolvedLink("https://lnkd.in/xyz", resolved=False)


def test_non_short_link_returned_unchanged():
    assert resolve_short_link("https://careers.acme.com/1") == ResolvedLink("https://careers.acme.com/1", True)


# ---------- Apify client and fetcher ----------

def test_apify_client_requests_newest_n_posts_and_maps_items():
    calls = []

    def runner(token, actor_id, run_input):
        calls.append((token, actor_id, run_input))
        return _items() + [{"noUrl": True}]

    client = ApifyProfilePostClient(CredentialPool("apify", ["tok-aaaa"]), "harvestapi/linkedin-profile-posts", runner)
    posts = client.fetch_profile_posts("https://www.linkedin.com/in/x/", 2)
    assert len(posts) == 2
    assert calls[0][2]["maxPosts"] == 2 and calls[0][2]["targetUrls"] == ["https://www.linkedin.com/in/x/"]
    assert posts[0].posted_at == date(2026, 11, 7)
    assert profile_post_from_item({"url": "u", "text": "t"}).post_url == "u"


def _fetcher(app_settings, db, items=None, recorded=None, max_posts_per_run=None):
    settings = app_settings.linkedin.model_copy(
        update={"max_posts_per_run": max_posts_per_run or app_settings.linkedin.max_posts_per_run})
    requested = []

    def runner(token, actor_id, run_input):
        requested.append(run_input["maxPosts"])
        return list(items if items is not None else _items())[: run_input["maxPosts"]]

    seen_repo = SeenPostRepository(db)
    recorded = recorded if recorded is not None else []
    fetcher = LinkedInProfilePostsFetcher(
        ApifyProfilePostClient(CredentialPool("apify", ["tok-aaaa"]), settings.apify_actor_id, runner),
        settings,
        find_seen_posts=seen_repo.find_seen_post_urls,
        record_post_outcome=lambda url, source, outcome, note: (
            recorded.append((url, outcome)), seen_repo.record_post(url, source, outcome, NOW, note=note)),
        link_resolver=lambda url: ResolvedLink(f"https://employer.example/{url.rsplit('/', 1)[-1]}", True),
    )
    return fetcher, requested


def test_fetcher_turns_hiring_posts_into_listings_and_records_others(app_settings, search_config):
    db = FakeDatabaseClient()
    recorded = []
    fetcher, requested = _fetcher(app_settings, db, recorded=recorded)
    result = fetcher.fetch(_profile(), search_config)
    assert result.status is SourceStatus.SUCCEEDED and requested == [3]
    assert [(listing.company, listing.apply_url) for listing in result.listings] == [
        ("Oracle", "https://employer.example/guxXTkA9"), ("Stripe", "https://employer.example/dGjHcMMa")]
    oracle = result.listings[0]
    assert oracle.source_url == "https://www.linkedin.com/posts/oracle-1" and oracle.source_id == "li_swadesh_kumar"
    assert recorded == [("https://www.linkedin.com/posts/sql-2", "ignored")]


def test_per_run_cap_enforced_across_profiles(app_settings, search_config):
    fetcher, requested = _fetcher(app_settings, FakeDatabaseClient(), max_posts_per_run=4)
    first = fetcher.fetch(_profile("li_a", 3), search_config)
    second = fetcher.fetch(_profile("li_b", 3), search_config)
    third = fetcher.fetch(_profile("li_c", 3), search_config)
    assert requested == [3, 1]
    assert first.status is SourceStatus.SUCCEEDED
    assert second.status is SourceStatus.PARTIAL and "limited" in second.message
    assert third.status is SourceStatus.SKIPPED and "cap" in third.message


def test_same_post_twice_creates_one_job(app_settings, search_config):
    db = FakeDatabaseClient()
    jobs = JobRepository(db)
    seen = SeenPostRepository(db)
    for _ in range(2):
        fetcher, _ = _fetcher(app_settings, db, items=_items()[:1])
        result = fetcher.fetch(_profile(), search_config)
        normalized = [normalize_listing(listing, app_settings.processing, search_config) for listing in result.listings]
        stored = jobs.store_jobs(normalized, NOW)
        ids = jobs.job_ids_for_keys(stored.new_keys)
        for job in normalized:  # what the pipeline does after storing
            seen.record_post(job.source_url, job.source_id, "job_created", NOW, job_id=ids.get(job.dedupe_key))
    assert len(db.rows("jobs")) == 1
    assert len(db.rows("linkedin_seen_posts")) == 1
    link = db.rows("job_sources")[0]
    assert link["source_id"] == "li_swadesh_kumar" and link["url"] == "https://www.linkedin.com/posts/oracle-1"
