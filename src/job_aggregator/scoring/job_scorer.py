"""The scorer interface and its result."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from job_aggregator.domain.models import NormalizedJob, SearchConfig

NEUTRAL_SCORE = 3


@dataclass(frozen=True)
class FitScore:
    score: int
    reason: str
    borderline: bool = False


class JobScorer(Protocol):
    def score(self, job: NormalizedJob, search_config: SearchConfig) -> FitScore: ...
