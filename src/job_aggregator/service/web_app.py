"""HTTP endpoints of the hosted service.

  GET  /healthz           liveness, unauthenticated, returns no data (204)
  POST /runs              start a run in the background -> 202 {run_id, started, state, reason}
  GET  /runs/{run_id}     run state and summary
  POST /health-check      missed-run and stuck-source check -> {alerts}

Every endpoint except /healthz needs `Authorization: Bearer <secret>` matching one of TRIGGER_SECRETS.
Secrets are never logged or echoed.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from job_aggregator.orchestration.daily_run_pipeline import RunOptions
from job_aggregator.service.run_manager import RunManager
from job_aggregator.service.shared_secret_auth import extract_bearer_token, is_valid_secret


class StartRunRequest(BaseModel):
    trigger_id: str = Field(default="github-cron", max_length=60, pattern=r"^[A-Za-z0-9_.:-]+$")
    force: bool = False
    only_sources: list[str] = Field(default_factory=list)
    only_methods: list[str] = Field(default_factory=list)


def create_app(run_manager: RunManager, check_health: Callable[[], list[str]], trigger_secrets: list[str]) -> FastAPI:
    if not trigger_secrets:
        raise ValueError("at least one trigger secret is required")
    app = FastAPI(title="job-aggregator", docs_url=None, redoc_url=None, openapi_url=None)

    def require_secret(request: Request) -> None:
        token = extract_bearer_token(request.headers.get("authorization"))
        if not is_valid_secret(token, trigger_secrets):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing or invalid secret",
                                headers={"WWW-Authenticate": "Bearer"})

    @app.get("/healthz", status_code=status.HTTP_204_NO_CONTENT)
    def liveness() -> Response:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/runs", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_secret)])
    def start_run(body: StartRunRequest | None = None) -> dict:
        body = body or StartRunRequest()
        options = RunOptions(only_sources=tuple(body.only_sources), only_methods=tuple(body.only_methods))
        outcome = run_manager.start(trigger_id=body.trigger_id, force=body.force, options=options)
        return {"run_id": outcome.run_id, "started": outcome.started, "state": outcome.state, "reason": outcome.reason}

    @app.get("/runs/{run_id}", dependencies=[Depends(require_secret)])
    def run_status(run_id: str) -> dict:
        result = run_manager.status(run_id)
        if result is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown run id")
        return result

    @app.post("/health-check", dependencies=[Depends(require_secret)])
    def health_check() -> dict:
        return {"alerts": check_health()}

    return app
