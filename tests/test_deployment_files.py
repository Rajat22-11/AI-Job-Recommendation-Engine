"""Deployment files parse, reference only known secrets, and never contain secret values."""

import re

import pytest
import yaml

from tests.conftest import REPO_ROOT

WORKFLOWS = REPO_ROOT / ".github" / "workflows"
SECRET_VALUE = re.compile(
    r"(apify_api_[A-Za-z0-9]{10,}|AIza[0-9A-Za-z_\-]{20,}|eyJ[A-Za-z0-9_\-]{20,}|sk-[A-Za-z0-9]{20,})"
)


def _workflow(name):
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    return text, yaml.safe_load(text)


@pytest.mark.parametrize("name", ["daily-job-run.yml", "health-check.yml", "fallback-pipeline-in-actions.yml"])
def test_workflow_parses_and_has_no_secret_values(name):
    text, workflow = _workflow(name)
    triggers = workflow.get("on", workflow.get(True))  # YAML 1.1 reads the key `on` as True
    assert "workflow_dispatch" in triggers
    assert workflow["jobs"] and all("timeout-minutes" in job for job in workflow["jobs"].values())
    assert not SECRET_VALUE.search(text)


@pytest.mark.parametrize("name", ["daily-job-run.yml", "health-check.yml"])
def test_trigger_workflows_hold_only_trigger_url_and_secret(name):
    text, workflow = _workflow(name)
    assert set(re.findall(r"secrets\.([A-Z_]+)", text)) == {"TRIGGER_URL", "TRIGGER_SECRET"}
    triggers = workflow.get("on", workflow.get(True))
    assert triggers["schedule"][0]["cron"]


def test_fallback_is_manual_only_until_switched():
    _, workflow = _workflow("fallback-pipeline-in-actions.yml")
    triggers = workflow.get("on", workflow.get(True))
    assert "schedule" not in triggers


def test_daily_trigger_and_fallback_share_a_concurrency_group():
    _, daily = _workflow("daily-job-run.yml")
    _, fallback = _workflow("fallback-pipeline-in-actions.yml")
    assert daily["concurrency"]["group"] == fallback["concurrency"]["group"]


def test_render_blueprint_parses_and_declares_secrets_without_values():
    text = (REPO_ROOT / "render.yaml").read_text(encoding="utf-8")
    blueprint = yaml.safe_load(text)
    [service] = blueprint["services"]
    assert service["plan"] == "free" and service["healthCheckPath"] == "/healthz"
    assert "--factory" in service["startCommand"]
    secrets = {v["key"]: v for v in service["envVars"] if v["key"] != "PYTHON_VERSION"}
    assert {"SUPABASE_SERVICE_KEY", "APIFY_TOKENS", "TRIGGER_SECRETS", "NTFY_TOPIC"} <= set(secrets)
    assert all(v.get("sync") is False and "value" not in v for v in secrets.values())
    assert not SECRET_VALUE.search(text)


def test_local_scripts_hold_no_secret_values():
    for script in (REPO_ROOT / "scripts").iterdir():
        if not script.is_file():
            continue
        assert not SECRET_VALUE.search(script.read_text(encoding="utf-8")), script.name
