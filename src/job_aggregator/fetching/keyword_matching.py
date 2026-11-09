"""Match listings against the owner's search keywords from `search_config`.

The keywords are search phrases such as "java spring boot developer", not text that appears in a title.
A keyword is therefore measured by its *significant words* (the phrase minus generic role words like
"developer"): the ratio is the share of those words found as whole words in the text.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from job_aggregator.settings.app_settings import MatchingSettings

DEFAULT_GENERIC_WORDS = frozenset({
    "developer", "engineer", "engineering", "software", "senior", "junior", "sr", "jr", "full",
    "the", "and", "for", "of", "in", "a", "an", "with", "to",
})
_WORD = re.compile(r"[a-z0-9+#.]+")


def words_of(text: str) -> list[str]:
    return [w.strip(".") for w in _WORD.findall(text.lower()) if w.strip(".")]


@dataclass(frozen=True)
class KeywordMatcher:
    generic_words: frozenset[str] = DEFAULT_GENERIC_WORDS
    prefilter_min_ratio: float = 0.3
    score_min_ratio: float = 0.5

    @classmethod
    def from_settings(cls, settings: MatchingSettings) -> KeywordMatcher:
        return cls(frozenset(w.lower() for w in settings.generic_words), settings.prefilter_min_ratio,
                   settings.score_min_ratio)

    def significant_words(self, keyword: str) -> list[str]:
        words = words_of(keyword)
        significant = [w for w in words if w not in self.generic_words]
        return significant or words

    def best_ratio(self, texts: Iterable[str | None], keywords: Iterable[str]) -> tuple[float, str | None]:
        """Highest keyword ratio over the text, with the keyword that achieved it."""
        present = set(words_of(" ".join(t for t in texts if t)))
        best, best_keyword = 0.0, None
        for keyword in keywords:
            needed = self.significant_words(keyword) if keyword and keyword.strip() else []
            if not needed:
                continue
            ratio = sum(1 for w in needed if w in present) / len(needed)
            if ratio > best:
                best, best_keyword = ratio, keyword
        return best, best_keyword

    def passes_prefilter(self, texts: Iterable[str | None], keywords: Iterable[str]) -> bool:
        """Loose test for whole-feed sources. No keywords configured keeps everything."""
        keywords = [k for k in keywords if k and k.strip()]
        if not keywords:
            return True
        return self.best_ratio(texts, keywords)[0] >= self.prefilter_min_ratio

    def counts_for_score(self, texts: Iterable[str | None], keywords: Iterable[str]) -> tuple[bool, str | None]:
        ratio, keyword = self.best_ratio(texts, keywords)
        return ratio >= self.score_min_ratio, keyword


DEFAULT_MATCHER = KeywordMatcher()


def matches_any_keyword(texts: Iterable[str | None], keywords: Iterable[str],
                        matcher: KeywordMatcher = DEFAULT_MATCHER) -> bool:
    """Prefilter test used by sources that return a whole feed."""
    return matcher.passes_prefilter(texts, keywords)
