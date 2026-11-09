"""Deterministic 1-5 fit score from `search_config`, with a plain-text reason. No network, no randomness."""

from __future__ import annotations

import math
import re
from collections.abc import Sequence

from job_aggregator.domain.models import NormalizedJob, SearchConfig
from job_aggregator.fetching.keyword_matching import DEFAULT_MATCHER, KeywordMatcher
from job_aggregator.scoring.job_scorer import NEUTRAL_SCORE, FitScore
from job_aggregator.settings.app_settings import ScoringSettings


def _has_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(phrase.lower())}(?!\w)", text) is not None


def detect_internship_or_batch(job: NormalizedJob, settings: ScoringSettings) -> str | None:
    """Return 'internship' or 'batch-restricted' when the job is one, else None."""
    title = job.title.lower()
    if job.employment_type == "internship" or any(_has_phrase(title, w) for w in settings.internship_words):
        return "internship"
    text = " ".join(part for part in (job.title, job.summary or "") if part)
    if re.search(settings.batch_pattern, text, re.IGNORECASE):
        return "batch-restricted"
    return None


def _location_matches(job: NormalizedJob, wanted_locations: list[str], place_words: Sequence[str]) -> bool | None:
    """True/False when the job's location can be judged, None when it is unknown.

    A wanted entry such as "Remote India" means remote work in India, "Remote International" means remote
    work outside it, and "Gandhinagar GIFT City" matches any known place word it contains (gandhinagar,
    gift city) found in the job's location.
    """
    if not job.location and not job.work_mode:
        return None
    text = (job.location or "").lower()
    for wanted in wanted_locations:
        wanted_lower = wanted.strip().lower()
        if not wanted_lower:
            continue
        if wanted_lower.startswith("remote"):
            if job.work_mode == "remote":
                if "india" in wanted_lower and job.location_bucket == "remote_india":
                    return True
                if "international" in wanted_lower and job.location_bucket == "remote_international":
                    return True
                if wanted_lower == "remote":
                    return True
            continue
        words = [w for w in place_words if _has_phrase(wanted_lower, w)] or [wanted_lower]
        if any(_has_phrase(text, w) for w in words):
            return True
    return False


class RulesScorer:
    def __init__(self, settings: ScoringSettings, matcher: KeywordMatcher = DEFAULT_MATCHER,
                 place_words: Sequence[str] = ()) -> None:
        self._settings = settings
        self._matcher = matcher
        self._place_words = list(place_words)

    def score(self, job: NormalizedJob, search_config: SearchConfig) -> FitScore:
        weights = self._settings.weights
        points = float(NEUTRAL_SCORE)
        reasons: list[str] = []

        # Title and skills only: a long description mentions "AI" or "data" in almost any role.
        matched, keyword = self._matcher.counts_for_score([job.title, " ".join(job.skills)], search_config.keywords)
        if matched:
            points += weights.keyword_match
            reasons.append(f"matches search '{keyword}'")
        elif search_config.keywords:
            points += weights.no_keyword_match
            reasons.append("no search keyword matched")

        location_ok = _location_matches(job, search_config.locations, self._place_words)
        if location_ok is True:
            points += weights.location_match
            reasons.append(f"location fits ({job.location or job.work_mode})")
        elif location_ok is False:
            points += weights.location_mismatch
            reasons.append(f"location outside preferences ({job.location or job.location_bucket})")
        else:
            reasons.append("location unknown")

        if job.min_yoe is not None and job.min_yoe > search_config.max_required_yoe:
            points += weights.experience_over_limit
            reasons.append(f"needs {job.min_yoe:g}+ years, above the {search_config.max_required_yoe:g}-year limit")
        elif job.min_yoe is not None:
            upper = f"{job.max_yoe:g}" if job.max_yoe is not None else "?"
            reasons.append(f"experience {job.min_yoe:g}-{upper} years fits")
        else:
            title = job.title.lower()
            senior_word = next((w for w in self._settings.seniority_words if _has_phrase(title, w)), None)
            if senior_word:
                points += weights.senior_title
                reasons.append(f"'{senior_word}' in the title and no years stated, likely above the "
                               f"{search_config.max_required_yoe:g}-year limit")

        minimum = f"the {search_config.min_salary_lpa:g} minimum"
        if job.salary_max_lpa is None:
            reasons.append("salary undisclosed")
        elif job.salary_max_lpa >= search_config.min_salary_lpa:
            points += weights.salary_meets_min
            reasons.append(f"salary up to {job.salary_max_lpa:g} LPA meets {minimum}")
        else:
            points += weights.salary_below_min
            reasons.append(f"salary up to {job.salary_max_lpa:g} LPA is below {minimum}")

        flag = detect_internship_or_batch(job, self._settings)
        if flag:
            points += weights.internship_or_batch
            reasons.append("internship" if flag == "internship" else "restricted to a graduating batch")

        score = max(1, min(5, math.floor(points + 0.5)))
        reason = "; ".join(reasons)
        return FitScore(score=score, reason=reason[:1].upper() + reason[1:],
                        borderline=score in self._settings.borderline_scores)
