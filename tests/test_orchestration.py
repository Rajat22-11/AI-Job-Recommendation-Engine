import copy
from datetime import UTC, date, datetime, timedelta

import pytest

from job_aggregator.domain.models import FetchResult, RawListing, RunStatus, SourceStatus
from job_aggregator.fetching.fetcher_factory import FetcherFactory
from job_aggregator.orchestration import run_daily
from job_aggregator.orchestration.build_pipeline import build_pipeline
from job_aggregator.orchestration.daily_run_pipeline import RunComponents, RunOptions, select_sources
from job_aggregator.registry.source_entry import SourceEntry
from job_aggregator.scoring.rules_scorer import RulesScorer
from tests.conftest import REPO_ROOT
from tests.fakes import FakeDatabaseClient

NOW = datetime(2026, 11, 8, 15, 0, tzinfo=UTC)
ENV = {"SUPABASE_URL": "https://fake.supabase.co", "SUPABASE_SERVICE_KEY": "service-key-value",
       "APIFY_TOKENS": "apify_api_AAAAAAAAAAAA", "NTFY_TOPIC": "topic-secret"}


def _seed_database():
    return FakeDatabaseClient({
        "search_config": [{"id": 1, "keywords": ["java", "python"], "locations": ["Pune", "Remote"],
                           "min_salary_lpa": 8.2, "max_required_yoe": 3, "max_job_age_days": 30,
                           "excluded_companies": ["BadCo"]}],
        "sources": [{"id": "indeed", "name": "Indeed", "base_url": "https://in.indeed.com", "enabled": True,
                     "access_method": "connector", "consecutive_empty_runs": 0}],
    })


def _listing(source_id, title="Java Developer", company="Acme", url="https://x/1", **extra):
    extra.setdefault("posted_at", date(2026, 11, 7))
    return RawListing(source_id=source_id, title=title, company=company, apply_url=url, source_url=url,
                      location="Pune, Maharashtra", **extra)


class StaticFetcher:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    def fetch(self, source, search_config):
        self.calls.append(source.id)
        if self.error:
            raise self.error
        listings = [listing.model_copy(update={"source_id": source.id}) for listing in self.result.listings]
        return self.result.model_copy(update={"source_id": source.id, "listings": listings})


class RecordingNotifier:
    def __init__(self):
        self.messages = []

    def send(self, title, message, priority="default", click_url=None):
        self.messages.append((title, message, priority))


def _fake_components(fetchers_by_source, app_settings):
    def make(context):
        builders = {method: (lambda source: fetchers_by_source[source.id]) for method in
                    ("open_api", "ats_board", "jobspy_board", "apify_job_board", "linkedin_profile_posts")}
        return RunComponents(FetcherFactory(builders), RulesScorer(app_settings.scoring))
    return make


def _pipeline(app_settings, db, fetchers, notifier=None, output=None):
    pipeline = build_pipeline(REPO_ROOT / "config", ENV, database=db,
                              make_run_components=_fake_components(fetchers, app_settings),
                              notifier=notifier or RecordingNotifier(), output=output or (lambda line: None))
    pipeline._clock = lambda: NOW
    return pipeline


def _fetchers():
    good = StaticFetcher(FetchResult(source_id="x", status=SourceStatus.SUCCEEDED, listings=[
        _listing("x", url="https://in.indeed.com/1", salary_text="10-14 LPA"),
        _listing("x", company="BadCo", url="https://in.indeed.com/2"),
        _listing("x", title="Python Engineer", url="https://in.indeed.com/3", posted_at=date(2026, 8, 1)),
    ]))
    same_job_elsewhere = StaticFetcher(FetchResult(source_id="x", status=SourceStatus.SUCCEEDED, listings=[
        _listing("x", url="https://naukri.com/1")]))
    empty = StaticFetcher(FetchResult(source_id="x", status=SourceStatus.SUCCEEDED))
    broken = StaticFetcher(error=RuntimeError("boom"))
    return {"indeed": good, "naukri": same_job_elsewhere, "glassdoor": broken, "jobcode": empty,
            "himalayas": empty, "remotive": empty, "remoteok": empty, "greenhouse": empty,
            "li_swadesh_kumar": empty, "li_vishakha_singhal": empty}


def test_composition_root_builds_with_fakes_and_no_network(app_settings):
    pipeline = build_pipeline(REPO_ROOT / "config", ENV, database=_seed_database(), notifier=RecordingNotifier())
    from job_aggregator.orchestration.daily_run_pipeline import RunContext

    components = pipeline._make_run_components(RunContext("r", NOW, True, lambda *a: None))
    linkedin = SourceEntry(id="li_x", name="x", fetch_method="linkedin_profile_posts", enabled=True,
                           settings={"profile_url": "https://www.linkedin.com/in/x/"})
    assert type(components.fetcher_factory.fetcher_for(linkedin)).__name__ == "LinkedInProfilePostsFetcher"
    assert type(components.scorer).__name__ == "RulesScorer"  # no GEMINI_API_KEYS in the test environment


def test_end_to_end_run_records_run_sources_jobs_and_notifies(app_settings):
    db = _seed_database()
    notifier = RecordingNotifier()
    summary = _pipeline(app_settings, db, _fetchers(), notifier).run(
        RunOptions(trigger_id="github-cron", only_methods=("jobspy_board", "apify_job_board")))

    assert summary.status is RunStatus.PARTIAL  # glassdoor failed, the others succeeded
    [run_row] = db.rows("runs")
    assert run_row["run_id"] == summary.run_id and run_row["status"] == "partial" and run_row["notified"] is True
    statuses = {row["source_id"]: (row["status"], row["jobs_found"], row["jobs_new"]) for row in db.rows("source_runs")}
    assert statuses == {"indeed": ("ok", 3, 1), "naukri": ("ok", 1, 0), "glassdoor": ("error", 0, 0)}
    [job] = db.rows("jobs")
    assert job["dedupe_key"] == "acme|java developer|pune" and 1 <= job["fit_score"] <= 5 and job["fit_reason"]
    assert {link["source_id"] for link in db.rows("job_sources")} == {"indeed", "naukri"}
    assert {row["id"] for row in db.rows("sources")} >= {"indeed", "naukri", "glassdoor", "li_swadesh_kumar"}
    assert len(notifier.messages) == 1 and "1 new" in notifier.messages[0][0]
    glassdoor_row = next(r for r in db.rows("source_runs") if r["source_id"] == "glassdoor")
    assert "boom" in glassdoor_row["message"]


def test_ui_toggle_wins_over_registry_and_sync_keeps_ui_edits(app_settings):
    db = _seed_database()
    db.tables["sources"] += [
        {"id": "naukri", "name": "Naukri (renamed in UI)", "base_url": "https://n.example", "enabled": False,
         "access_method": "auto"},
        {"id": "himalayas", "name": "Himalayas", "base_url": "https://h", "enabled": True, "access_method": "auto"},
    ]
    fetchers = _fetchers()
    _pipeline(app_settings, db, fetchers).run(RunOptions(only_methods=("jobspy_board", "apify_job_board")))
    assert fetchers["naukri"].calls == []                     # disabled in the UI, enabled in the registry file
    assert fetchers["indeed"].calls and fetchers["glassdoor"].calls
    naukri = next(row for row in db.rows("sources") if row["id"] == "naukri")
    assert (naukri["enabled"], naukri["name"], naukri["base_url"]) == (False, "Naukri (renamed in UI)",
                                                                      "https://n.example")
    assert naukri["access_method"] == "api"             # Apify actor: no URL template needed
    assert next(r for r in db.rows("sources") if r["id"] == "himalayas")["access_method"] == "api"


def test_enabled_sources_the_pipeline_cannot_fetch_get_honest_skipped_rows(app_settings):
    db = _seed_database()
    db.tables["sources"] += [
        {"id": "wellfound", "name": "Wellfound", "base_url": "https://wellfound.com", "enabled": True},
        {"id": "brand-new-ui-source", "name": "New", "base_url": "https://new.example", "enabled": True},
        {"id": "flexjobs", "name": "FlexJobs", "base_url": "https://flexjobs.com", "enabled": False},
    ]
    pipeline = _pipeline(app_settings, db, _fetchers())
    pipeline._not_fetched = {"wellfound": "Public pages sit behind a Cloudflare Turnstile challenge; not solved."}
    pipeline.run(RunOptions())
    skipped = {r["source_id"]: r for r in db.rows("source_runs") if r["status"] == "skipped"}
    assert set(skipped) == {"wellfound", "brand-new-ui-source"}          # disabled flexjobs gets no row
    assert "Turnstile" in skipped["wellfound"]["message"]
    assert "not in the source registry" in skipped["brand-new-ui-source"]["message"]
    assert skipped["wellfound"]["jobs_found"] == 0


def test_partial_runs_do_not_write_skipped_rows_for_other_sources(app_settings):
    db = _seed_database()
    db.tables["sources"].append({"id": "wellfound", "name": "W", "base_url": "https://w", "enabled": True})
    _pipeline(app_settings, db, _fetchers()).run(RunOptions(only_methods=("jobspy_board", "apify_job_board")))
    assert all(r["source_id"] != "wellfound" for r in db.rows("source_runs"))


def test_ip_block_is_recorded_as_error_not_as_a_login_request(app_settings):
    from job_aggregator.domain.errors import SourceBlockedError

    fetchers = _fetchers()
    fetchers["indeed"] = StaticFetcher(error=SourceBlockedError("indeed", "HTTP 403", kind="ip"))
    fetchers["naukri"] = StaticFetcher(error=SourceBlockedError("naukri", "redirected to a login page", kind="login"))
    db = _seed_database()
    _pipeline(app_settings, db, fetchers).run(RunOptions(only_sources=("indeed", "naukri")))
    statuses = {row["source_id"]: row["status"] for row in db.rows("source_runs")}
    assert statuses == {"indeed": "error", "naukri": "needs_login"}


def test_dry_run_writes_nothing_and_prints_keys(app_settings):
    db = _seed_database()
    before = copy.deepcopy(db.tables)
    lines = []
    notifier = RecordingNotifier()
    summary = _pipeline(app_settings, db, _fetchers(), notifier, lines.append).run(
        RunOptions(dry_run=True, only_sources=("indeed", "naukri")))
    assert db.tables == before
    assert all(call[0] == "select" for call in db.calls)
    assert notifier.messages == []
    assert summary.jobs_new == 1
    assert any("NEW" in line and "acme|java developer|pune" in line for line in lines)


def test_only_selected_sources_are_fetched(app_settings):
    fetchers = _fetchers()
    _pipeline(app_settings, _seed_database(), fetchers).run(RunOptions(only_sources=("naukri",)))
    assert fetchers["naukri"].calls == ["naukri"]
    assert fetchers["indeed"].calls == [] and fetchers["jobcode"].calls == []


def test_select_sources_by_method_and_rejects_unknown_ids():
    entries = [SourceEntry(id="a", name="a", fetch_method="open_api", enabled=True),
               SourceEntry(id="b", name="b", fetch_method="jobspy_board", enabled=True),
               SourceEntry(id="c", name="c", fetch_method="jobspy_board", enabled=False)]
    assert [e.id for e in select_sources(entries, only_methods=("jobspy_board",))] == ["b"]
    assert [e.id for e in select_sources(entries, skip_methods=("jobspy_board",))] == ["a"]
    with pytest.raises(ValueError, match="zzz"):
        select_sources(entries, only_sources=("zzz",))


def test_health_only_mode_alerts_on_missed_run(app_settings):
    db = _seed_database()
    db.tables["runs"] = [{"run_id": "old", "started_at": (NOW - timedelta(hours=60)).isoformat(), "status": "partial"}]
    notifier = RecordingNotifier()
    alerts = _pipeline(app_settings, db, _fetchers(), notifier).check_health_only()
    assert alerts and "No pipeline run recorded" in alerts[0]
    assert notifier.messages[0][0] == "Job pipeline health alert"


def test_unreachable_notifier_still_finishes_run(app_settings):
    class Down:
        def send(self, *args, **kwargs):
            raise ConnectionError("down")

    db = _seed_database()
    summary = _pipeline(app_settings, db, _fetchers(), Down()).run(RunOptions(only_sources=("naukri",)))
    assert summary.notification_error and db.rows("runs")[0]["notified"] is False
    assert "notification failed" in db.rows("runs")[0]["summary"]


# ---------------- command-line options ----------------

def _cli(app_settings, argv, db=None, fetchers=None):
    db = db or _seed_database()
    fetchers = fetchers or _fetchers()
    code = run_daily.main(argv, pipeline_builder=lambda args: _pipeline(app_settings, db, fetchers))
    return code, db, fetchers


def test_cli_dry_run_writes_nothing(app_settings):
    db = _seed_database()
    before = copy.deepcopy(db.tables)
    code, db, _ = _cli(app_settings, ["--dry-run", "--only-sources", "naukri"], db)
    assert db.tables == before and code == 0


def test_cli_only_sources_and_only_methods(app_settings):
    _, _, fetchers = _cli(app_settings, ["--only-sources", "indeed,naukri"])
    assert fetchers["indeed"].calls and fetchers["naukri"].calls and not fetchers["glassdoor"].calls
    code, db, fetchers = _cli(app_settings, ["--only-methods", "jobspy_board,apify_job_board"])
    assert fetchers["glassdoor"].calls and not fetchers["jobcode"].calls
    assert code == 1  # partial: glassdoor failed


def test_cli_check_health_only(app_settings):
    db = _seed_database()
    db.tables["runs"] = [{"run_id": "r", "started_at": NOW.isoformat(), "status": "succeeded"}]
    code, db, fetchers = _cli(app_settings, ["--check-health-only"], db)
    assert code == 0 and not fetchers["indeed"].calls and db.rows("source_runs") == []
