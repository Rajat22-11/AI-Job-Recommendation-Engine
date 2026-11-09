import copy
from pathlib import Path

import pytest
import yaml

from job_aggregator.domain.errors import InvalidSettingsError, MissingSecretError
from job_aggregator.settings.load_settings import load_settings, parse_settings
from job_aggregator.settings.read_secrets import (
    read_secret_list,
    read_secret_lists_from_environment,
    read_trigger_secrets,
)

SETTINGS_PATH = Path(__file__).resolve().parents[1] / "config" / "settings.yaml"


@pytest.fixture
def settings_document():
    return yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8"))


def test_real_settings_file_loads():
    settings = load_settings(SETTINGS_PATH)
    assert settings.scoring.gemini.enabled is True
    assert settings.scoring.gemini.model == "gemini-3.5-flash-lite"
    assert settings.trigger.repeat_trigger_behaviour == "return_finished"


def test_unknown_key_rejected_with_its_name(settings_document):
    doc = copy.deepcopy(settings_document)
    doc["fetching"]["max_retires"] = 3
    with pytest.raises(InvalidSettingsError, match=r"fetching\.max_retires.*unknown key"):
        parse_settings(doc)


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [("fetching", "max_retries", -1), ("notifications", "channel", "pigeon"),
     ("trigger", "repeat_trigger_behaviour", "maybe"), ("health", "low_ratio_alert", 2)],
)
def test_invalid_value_rejected(settings_document, section, key, value):
    doc = copy.deepcopy(settings_document)
    doc[section][key] = value
    with pytest.raises(InvalidSettingsError, match=rf"{section}\.{key}"):
        parse_settings(doc)


def test_location_bucket_must_be_allowed_by_database(settings_document):
    doc = copy.deepcopy(settings_document)
    doc["processing"]["location_buckets"]["bengaluru"] = ["bengaluru"]
    with pytest.raises(InvalidSettingsError, match="location_buckets"):
        parse_settings(doc)


def test_bad_regex_rejected(settings_document):
    doc = copy.deepcopy(settings_document)
    doc["scoring"]["batch_pattern"] = "(unclosed"
    with pytest.raises(InvalidSettingsError, match="batch_pattern"):
        parse_settings(doc)


def test_secret_list_missing_single_and_multiple():
    with pytest.raises(MissingSecretError, match="APIFY_TOKENS"):
        read_secret_list("APIFY_TOKENS", {})
    assert read_secret_list("APIFY_TOKENS", {"APIFY_TOKENS": "only-one"}) == ["only-one"]
    assert read_secret_list("APIFY_TOKENS", {"APIFY_TOKENS": "a, b;c\n d"}) == ["a", "b", "c", "d"]
    assert read_secret_list("APIFY_TOKENS", {}, required=False) == []


def test_pipeline_secrets_names_missing_variable_and_hides_values():
    with pytest.raises(MissingSecretError, match="SUPABASE_SERVICE_KEY"):
        read_secret_lists_from_environment({"SUPABASE_URL": "https://x.supabase.co"})
    secrets = read_secret_lists_from_environment(
        {"SUPABASE_URL": "u", "SUPABASE_SERVICE_KEY": "super-secret", "APIFY_TOKENS": "t1,t2"}
    )
    assert secrets.service_tokens["apify"] == ["t1", "t2"]
    assert secrets.service_tokens["gemini"] == []
    assert "super-secret" not in repr(secrets) and "t1" not in repr(secrets)


def test_trigger_secrets_required():
    with pytest.raises(MissingSecretError, match="TRIGGER_SECRETS"):
        read_trigger_secrets({})
    assert read_trigger_secrets({"TRIGGER_SECRETS": "old,new"}) == ["old", "new"]
