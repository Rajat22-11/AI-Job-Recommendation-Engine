"""Matching and scoring with the owner's real search_config (read from the live database on 2026-11-08).

The live keywords are long search phrases and the locations include "Remote India" and "Gandhinagar GIFT City",
which short test keywords hid.
"""

import pytest

from job_aggregator.domain.models import NormalizedJob, SearchConfig
from job_aggregator.fetching.keyword_matching import KeywordMatcher, matches_any_keyword
from job_aggregator.scoring.rules_scorer import RulesScorer

LIVE = SearchConfig(
    keywords=["java spring boot developer", "java backend engineer", "software engineer java",
              "machine learning engineer", "AI engineer", "data scientist", "data engineer", "full stack java react"],
    locations=["Pune", "Mumbai", "Ahmedabad", "Gandhinagar GIFT City", "Surat", "Vadodara", "Remote India",
               "Remote International"],
    min_salary_lpa=8.2, max_required_yoe=2.0, max_job_age_days=30, excluded_companies=[])


@pytest.fixture
def matcher(app_settings):
    return KeywordMatcher.from_settings(app_settings.matching)


@pytest.mark.parametrize(
    ("title", "kept"),
    [("Java Developer", True), ("Backend Engineer", True), ("Software Engineer II - Java", True),
     ("Senior Java Spring Boot Developer", True), ("Machine Learning Engineer", True), ("AI Engineer", True),
     ("Full Stack Developer", True), ("Data Engineer", True), ("Sales Manager", False),
     ("Account Executive", False), ("Python Developer", False)],
)
def test_prefilter_with_live_keywords(matcher, title, kept):
    assert matches_any_keyword([title], LIVE.keywords, matcher) is kept


def _job(location, bucket, mode, title="Java Developer"):
    return NormalizedJob(
        dedupe_key="k", title=title, company="Acme", apply_url="https://x", source_id="s", source_url="https://x",
        location=location, location_bucket=bucket, work_mode=mode, min_yoe=1, max_yoe=2, salary_min_lpa=10,
        salary_max_lpa=14, skills=["Java", "Spring Boot"], summary="Build services with Java and Spring Boot")


@pytest.fixture
def scorer(app_settings, matcher):
    processing = app_settings.processing
    place_words = [*processing.known_cities, *(w for words in processing.location_buckets.values() for w in words)]
    return RulesScorer(app_settings.scoring, matcher, place_words)


@pytest.mark.parametrize(
    ("location", "bucket", "mode"),
    [("Pune, Maharashtra", "pune", "onsite"), ("Remote (India)", "remote_india", "remote"),
     ("Surat, Gujarat", "gujarat", "onsite"), ("Gandhinagar", "gujarat", "onsite"),
     ("GIFT City, Gujarat", "gujarat", "onsite"), ("Anywhere, Remote", "remote_international", "remote")],
)
def test_good_java_job_scores_high_in_every_wanted_place(scorer, location, bucket, mode):
    result = scorer.score(_job(location, bucket, mode), LIVE)
    assert result.score >= 4, result.reason
    assert "matches search" in result.reason.lower() and "outside preferences" not in result.reason


def test_unwanted_city_is_penalised_and_off_topic_job_scores_low(scorer):
    nearby = scorer.score(_job("Pune", "pune", "onsite"), LIVE).score
    assert scorer.score(_job("Chennai", "other", "onsite"), LIVE).score < nearby
    off_topic = scorer.score(_job("Pune", "pune", "onsite", title="Sales Manager").model_copy(
        update={"skills": ["CRM"], "summary": "Close deals"}), LIVE)
    assert off_topic.score < nearby and "no search keyword matched" in off_topic.reason.lower()


def test_remote_international_wanted_matches_international_remote_only(scorer):
    only_intl = LIVE.model_copy(update={"locations": ["Remote International"]})
    assert "outside preferences" not in scorer.score(_job("Worldwide", "remote_international", "remote"),
                                                       only_intl).reason
    assert "outside preferences" in scorer.score(_job("Remote (India)", "remote_india", "remote"), only_intl).reason
