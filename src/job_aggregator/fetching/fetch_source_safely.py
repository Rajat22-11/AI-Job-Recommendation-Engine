"""Run one fetcher and turn any failure into a recorded status, so one source never stops the others."""

from __future__ import annotations

import logging

from job_aggregator.credentials.secret_redaction import redact_secrets
from job_aggregator.domain.errors import AllTokensExhaustedError, SourceBlockedError, SourceTimeoutError
from job_aggregator.domain.models import FetchResult, SearchConfig, SourceStatus
from job_aggregator.fetching.job_fetcher import JobFetcher
from job_aggregator.registry.source_entry import SourceEntry

logger = logging.getLogger(__name__)


def fetch_source_safely(
    fetcher: JobFetcher, source: SourceEntry, search_config: SearchConfig, max_listings: int
) -> FetchResult:
    """Call the fetcher; never raise. Caps the listing count and records why a source failed."""
    try:
        result = fetcher.fetch(source, search_config)
    except SourceBlockedError as exc:
        logger.warning("%s blocked: %s", source.id, exc)
        return FetchResult(source_id=source.id, status=SourceStatus.BLOCKED, message=redact_secrets(str(exc)),
                           block_kind=exc.kind)
    except (SourceTimeoutError, AllTokensExhaustedError) as exc:
        logger.warning("%s failed: %s", source.id, exc)
        return FetchResult(source_id=source.id, status=SourceStatus.FAILED, message=redact_secrets(str(exc)))
    except Exception as exc:  # noqa: BLE001 - isolation is the point of this function
        logger.exception("%s failed with an unexpected error", source.id)
        message = redact_secrets(f"{type(exc).__name__}: {exc}")[:500]
        return FetchResult(source_id=source.id, status=SourceStatus.FAILED, message=message)

    if len(result.listings) > max_listings:
        note = f"capped at {max_listings} of {len(result.listings)} listings"
        result = result.model_copy(update={
            "listings": result.listings[:max_listings],
            "message": f"{result.message}; {note}".strip("; "),
        })
    return result
