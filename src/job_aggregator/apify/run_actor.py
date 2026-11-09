"""Run one Apify actor and return its dataset items. Shared by every fetcher that uses Apify."""

from __future__ import annotations

from collections.abc import Callable

ACTOR_RUN_TIMEOUT_SECONDS = 300

ActorRunner = Callable[[str, str, dict], list[dict]]
"""(token, actor_id, run_input) -> dataset items."""


def run_apify_actor(token: str, actor_id: str, run_input: dict) -> list[dict]:
    from apify_client import ApifyClient  # imported lazily so tests never need it

    client = ApifyClient(token)
    run = client.actor(actor_id).call(run_input=run_input, timeout_secs=ACTOR_RUN_TIMEOUT_SECONDS)
    if not run or not run.get("defaultDatasetId"):
        raise RuntimeError(f"Apify actor {actor_id} returned no dataset (status {run and run.get('status')})")
    return list(client.dataset(run["defaultDatasetId"]).list_items().items)
