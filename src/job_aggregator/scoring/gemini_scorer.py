"""Optional Google Gemini review of borderline jobs. Off by default; falls back to rules on any failure.

Only minimal job text and a short criteria summary are sent. The API key travels in a header, never in
the URL, so it cannot leak through logged URLs.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from pathlib import Path

import httpx

from job_aggregator.credentials.credential_pool import CredentialPool, rotate_on_quota_error
from job_aggregator.domain.models import NormalizedJob, SearchConfig
from job_aggregator.scoring.gemini_prompt import PROMPT_FILE_NAME, GeminiPrompt, load_gemini_prompt
from job_aggregator.scoring.job_scorer import FitScore, JobScorer
from job_aggregator.settings.app_settings import GeminiSettings

logger = logging.getLogger(__name__)
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_PROMPT_PATH = Path(__file__).resolve().parents[3] / "config" / PROMPT_FILE_NAME


class GeminiApiError(Exception):
    """Non-2xx answer from Gemini, carrying the status and message for the token classifier."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"Gemini HTTP {status_code}: {message[:300]}")
        self.status_code = status_code


def build_prompt(job: NormalizedJob, search_config: SearchConfig, rules_result: FitScore,
                 prompt: GeminiPrompt) -> str:
    """Instruction and per-job data, with the wording taken from config/gemini_prompt.yaml."""
    job_text = {
        "title": job.title, "company": job.company, "location": job.location, "work_mode": job.work_mode,
        "experience_years": [job.min_yoe, job.max_yoe], "salary_lpa": [job.salary_min_lpa, job.salary_max_lpa],
        "skills": job.skills[:10], "summary": (job.summary or "")[:300],
    }
    criteria = {
        "keywords": search_config.keywords, "locations": search_config.locations,
        "max_required_years": search_config.max_required_yoe, "min_salary_lpa": search_config.min_salary_lpa,
    }
    data = prompt.data_template.format(
        criteria=json.dumps(criteria), job=json.dumps(job_text),
        rules_score=rules_result.score, rules_reason=rules_result.reason)
    return f"{prompt.instruction}\n{data}"


GeminiCall = Callable[[str, str], dict]
"""(api_key, prompt) -> parsed JSON answer {"score": int, "reason": str}"""


class GeminiScorer:
    """Asks Gemini to re-score jobs the rules marked borderline, up to a per-run limit."""

    def __init__(self, rules: JobScorer, pool: CredentialPool, settings: GeminiSettings,
                 call: GeminiCall | None = None, prompt: GeminiPrompt | None = None) -> None:
        self._rules = rules
        self._prompt = prompt or load_gemini_prompt(DEFAULT_PROMPT_PATH)
        self._pool = pool
        self._settings = settings
        self._call = call or self._call_gemini
        self._reviews_left = settings.max_jobs_per_run
        self._last_call_at: float | None = None

    def score(self, job: NormalizedJob, search_config: SearchConfig) -> FitScore:
        rules_result = self._rules.score(job, search_config)
        if not rules_result.borderline or self._reviews_left <= 0:
            return rules_result
        self._reviews_left -= 1
        prompt = build_prompt(job, search_config, rules_result, self._prompt)
        try:
            answer = rotate_on_quota_error(self._pool, lambda key: self._call(key, prompt))
            score = int(answer["score"])
            reason = str(answer.get("reason") or "").strip()
            if not 1 <= score <= 5 or not reason:
                raise ValueError(f"unusable answer: {answer!r}"[:200])
        except Exception as exc:  # noqa: BLE001 - any failure falls back to the rules result
            logger.info("Gemini review skipped for '%s': %s", job.title, exc)
            return rules_result
        return FitScore(score=score, reason=f"{reason} (model review; rules said {rules_result.score})")

    def _pace(self) -> None:
        """Keep calls at least `min_seconds_between_calls` apart; bursts trip Gemini's per-minute limit."""
        gap = self._settings.min_seconds_between_calls
        if self._last_call_at is not None and gap > 0:
            wait = gap - (time.monotonic() - self._last_call_at)
            if wait > 0:
                time.sleep(wait)
        self._last_call_at = time.monotonic()

    def _call_gemini(self, api_key: str, prompt: str) -> dict:
        self._pace()
        response = httpx.post(
            API_URL.format(model=self._settings.model),
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
            },
            timeout=self._settings.request_timeout_seconds,
        )
        if response.status_code >= 400:
            raise GeminiApiError(response.status_code, response.text)
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
