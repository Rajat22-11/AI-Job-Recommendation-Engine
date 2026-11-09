"""Composition root: the only place that wires concrete classes together."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path

from job_aggregator.credentials.credential_pool import build_credential_pools
from job_aggregator.credentials.secret_redaction import register_secret
from job_aggregator.fetching.ats_boards.ashby_board_fetcher import AshbyBoardFetcher
from job_aggregator.fetching.ats_boards.greenhouse_board_fetcher import GreenhouseBoardFetcher
from job_aggregator.fetching.ats_boards.lever_board_fetcher import LeverBoardFetcher
from job_aggregator.fetching.feeds.weworkremotely_feed_fetcher import WeWorkRemotelyFeedFetcher
from job_aggregator.fetching.fetcher_factory import FetcherFactory, dispatch_by_provider
from job_aggregator.fetching.job_boards.apify_naukri_fetcher import ApifyNaukriFetcher
from job_aggregator.fetching.job_boards.jobspy_board_fetcher import JobSpyBoardFetcher
from job_aggregator.fetching.keyword_matching import KeywordMatcher
from job_aggregator.fetching.open_api.himalayas_fetcher import HimalayasFetcher
from job_aggregator.fetching.open_api.jobcode_fetcher import JobcodeFetcher
from job_aggregator.fetching.open_api.remoteok_fetcher import RemoteOkFetcher
from job_aggregator.fetching.open_api.remotive_fetcher import RemotiveFetcher
from job_aggregator.fetching.open_api.workingnomads_fetcher import WorkingNomadsFetcher
from job_aggregator.fetching.polite_http_client import PoliteHttpClient
from job_aggregator.fetching.web_pages.arc_fetcher import ArcFetcher
from job_aggregator.linkedin.fetch_profile_posts import ApifyProfilePostClient
from job_aggregator.linkedin.linkedin_profile_posts_fetcher import LinkedInProfilePostsFetcher
from job_aggregator.notifications.notifier import NoNotifier, Notifier, NtfyNotifier
from job_aggregator.orchestration.daily_run_pipeline import (
    DailyRunPipeline,
    Repositories,
    RunComponents,
    RunContext,
)
from job_aggregator.persistence.database_client import DatabaseClient, SupabaseDatabaseClient
from job_aggregator.persistence.job_repository import JobRepository
from job_aggregator.persistence.run_repository import RunRepository
from job_aggregator.persistence.search_config_repository import SearchConfigRepository
from job_aggregator.persistence.seen_post_repository import SeenPostRepository
from job_aggregator.persistence.source_repository import SourceRepository
from job_aggregator.registry.load_source_registry import load_not_fetched, load_source_registry
from job_aggregator.scoring.build_scorer import build_scorer
from job_aggregator.scoring.gemini_prompt import PROMPT_FILE_NAME, GeminiPrompt, load_gemini_prompt
from job_aggregator.settings.app_settings import AppSettings
from job_aggregator.settings.load_settings import load_settings
from job_aggregator.settings.read_secrets import PipelineSecrets, read_secret_lists_from_environment

logger = logging.getLogger(__name__)
DEFAULT_CONFIG_DIR = Path("config")


def build_repositories(database: DatabaseClient) -> Repositories:
    return Repositories(
        search_config=SearchConfigRepository(database),
        sources=SourceRepository(database),
        runs=RunRepository(database),
        jobs=JobRepository(database),
        seen_posts=SeenPostRepository(database),
    )


def build_notifier(settings: AppSettings, secrets: PipelineSecrets) -> Notifier:
    if settings.notifications.channel == "ntfy":
        if secrets.ntfy_topic:
            return NtfyNotifier(settings.notifications.ntfy_server, secrets.ntfy_topic)
        logger.warning("notifications.channel is ntfy but NTFY_TOPIC is not set; notifications are off")
    return NoNotifier()


def make_run_components_factory(settings: AppSettings, secrets: PipelineSecrets, repos: Repositories,
                                gemini_prompt: GeminiPrompt | None = None):
    """Return a function building fresh fetchers, token pools and scorer for each run."""

    def make(context: RunContext) -> RunComponents:
        pools = build_credential_pools(secrets.service_tokens)  # tokens spent in one run are fresh in the next
        http = PoliteHttpClient(settings.fetching)
        matcher = KeywordMatcher.from_settings(settings.matching)
        processing = settings.processing
        bucket_words = (w for words in processing.location_buckets.values() for w in words)
        place_words = [*processing.known_cities, *bucket_words]
        open_api = {
            "jobcode": JobcodeFetcher(http, repos.runs.last_successful_source_run_at, now=lambda: context.now),
            "himalayas": HimalayasFetcher(http),
            "remotive": RemotiveFetcher(
                http, lambda source_id: repos.runs.count_source_calls_today(source_id, context.now), matcher),
            "remoteok": RemoteOkFetcher(http, matcher),
            "workingnomads": WorkingNomadsFetcher(http, matcher),
        }
        ats_boards = {
            "greenhouse": GreenhouseBoardFetcher(http, matcher),
            "lever": LeverBoardFetcher(http, matcher),
            "ashby": AshbyBoardFetcher(http, matcher),
        }
        jobspy = JobSpyBoardFetcher(settings.jobspy)
        linkedin = LinkedInProfilePostsFetcher(
            ApifyProfilePostClient(pools["apify"], settings.linkedin.apify_actor_id),
            settings.linkedin,
            find_seen_posts=repos.seen_posts.find_seen_post_urls,
            record_post_outcome=context.record_post_outcome,
        )
        factory = FetcherFactory({
            "open_api": dispatch_by_provider(open_api),
            "ats_board": dispatch_by_provider(ats_boards),
            "rss_feed": dispatch_by_provider({"weworkremotely": WeWorkRemotelyFeedFetcher(http, matcher)}),
            "web_page": dispatch_by_provider({"arc": ArcFetcher(http, matcher)}),
            "jobspy_board": lambda source: jobspy,
            "apify_job_board": dispatch_by_provider({"naukri": ApifyNaukriFetcher(pools["apify"])}),
            "linkedin_profile_posts": lambda source: linkedin,
        })
        scorer = build_scorer(settings.scoring, pools, matcher, place_words, prompt=gemini_prompt)
        return RunComponents(fetcher_factory=factory, scorer=scorer)

    return make


def build_pipeline(
    config_dir: str | Path = DEFAULT_CONFIG_DIR,
    environ: Mapping[str, str] | None = None,
    database: DatabaseClient | None = None,
    make_run_components=None,
    notifier: Notifier | None = None,
    output=print,
) -> DailyRunPipeline:
    """Build the pipeline from the registry, settings and environment secrets.

    Tests pass a fake `database`, `make_run_components` and `notifier`, so nothing touches the network.
    """
    config_path = Path(config_dir)
    settings = load_settings(config_path / "settings.yaml")
    gemini_prompt = load_gemini_prompt(config_path / PROMPT_FILE_NAME)
    entries = load_source_registry(config_path / "sources.yaml")
    not_fetched = load_not_fetched(config_path / "sources.yaml")
    secrets = read_secret_lists_from_environment(environ)
    register_secret(secrets.supabase_service_key, "supabase service key")
    if secrets.ntfy_topic:
        register_secret(secrets.ntfy_topic, "ntfy topic")
    if secrets.heartbeat_url:
        register_secret(secrets.heartbeat_url, "heartbeat url")

    database = database or SupabaseDatabaseClient(secrets.supabase_url, secrets.supabase_service_key)
    repos = build_repositories(database)
    return DailyRunPipeline(
        entries=entries,
        settings=settings,
        repositories=repos,
        make_run_components=make_run_components or make_run_components_factory(settings, secrets, repos, gemini_prompt),
        notifier=notifier or build_notifier(settings, secrets),
        heartbeat_url=secrets.heartbeat_url,
        not_fetched=not_fetched,
        output=output,
    )
