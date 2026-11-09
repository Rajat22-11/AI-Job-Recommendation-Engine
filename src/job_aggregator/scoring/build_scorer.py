"""Choose the scorer from settings and make sure scoring can never stop a job from being stored."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from job_aggregator.credentials.credential_pool import CredentialPool
from job_aggregator.domain.models import NormalizedJob, SearchConfig
from job_aggregator.fetching.keyword_matching import DEFAULT_MATCHER, KeywordMatcher
from job_aggregator.scoring.gemini_prompt import GeminiPrompt
from job_aggregator.scoring.gemini_scorer import GeminiScorer
from job_aggregator.scoring.job_scorer import NEUTRAL_SCORE, JobScorer
from job_aggregator.scoring.rules_scorer import RulesScorer
from job_aggregator.settings.app_settings import ScoringSettings

logger = logging.getLogger(__name__)


def build_scorer(
    settings: ScoringSettings,
    credential_pools: dict[str, CredentialPool],
    matcher: KeywordMatcher = DEFAULT_MATCHER,
    place_words: Sequence[str] = (),
    prompt: GeminiPrompt | None = None,
) -> JobScorer:
    """Rules by default; Gemini on top only when enabled in settings."""
    rules = RulesScorer(settings, matcher, place_words)
    if not settings.gemini.enabled:
        return rules
    pool = credential_pools.get("gemini") or CredentialPool("gemini", [])
    if pool.size == 0:
        logger.warning("scoring.gemini is enabled but GEMINI_API_KEYS is empty; using rules only")
        return rules
    return GeminiScorer(rules, pool, settings.gemini, prompt=prompt)


def score_job_safely(scorer: JobScorer, job: NormalizedJob, search_config: SearchConfig) -> NormalizedJob:
    """Return the job with fit_score and fit_reason set; a scoring error gives a neutral score instead."""
    try:
        result = scorer.score(job, search_config)
        return job.model_copy(update={"fit_score": result.score, "fit_reason": result.reason})
    except Exception as exc:  # noqa: BLE001 - storing the job matters more than its score
        logger.exception("scoring failed for '%s' at %s", job.title, job.company)
        return job.model_copy(update={"fit_score": NEUTRAL_SCORE,
                                      "fit_reason": f"Scoring failed ({type(exc).__name__}); neutral score given"})
