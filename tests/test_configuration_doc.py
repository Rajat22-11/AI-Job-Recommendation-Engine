"""Every key in config/settings.yaml and every secret the code reads is documented in docs/configuration.md."""

import yaml

from job_aggregator.settings import read_secrets
from tests.conftest import REPO_ROOT


def _leaf_keys(node, prefix=""):
    for key, value in node.items():
        if isinstance(value, dict) and key not in ("field_aliases", "location_buckets", "role_tracks", "weights"):
            yield from _leaf_keys(value, f"{prefix}{key}.")
        else:
            yield f"{prefix}{key}"


def test_every_setting_is_documented():
    doc = (REPO_ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")
    settings = yaml.safe_load((REPO_ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    missing = [key for key in _leaf_keys(settings) if f"`{key.split('.', 1)[1]}`" not in doc]
    assert missing == []


def test_every_secret_name_is_documented():
    doc = (REPO_ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")
    names = [value for name, value in vars(read_secrets).items() if name.isupper() and isinstance(value, str)
             and name != "LIST_SEPARATOR"]
    names += ["TRIGGER_URL", "TRIGGER_SECRET", "SKIP_FETCH_METHODS", "SPIKE_FAKE_PIPELINE_MINUTES"]
    assert [name for name in names if f"`{name}`" not in doc] == []
