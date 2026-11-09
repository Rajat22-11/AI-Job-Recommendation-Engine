from pathlib import Path

import pytest

from job_aggregator.domain.errors import InvalidRegistryError
from job_aggregator.registry.load_source_registry import (
    enabled_entries,
    load_source_registry,
    validate_source_registry,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _entry(**overrides):
    entry = {"id": "himalayas", "name": "Himalayas", "fetch_method": "open_api", "provider": "himalayas",
             "enabled": True}
    entry.update(overrides)
    return {k: v for k, v in entry.items() if v is not ...}


def test_real_registry_file_loads():
    entries = load_source_registry(REPO_ROOT / "config" / "sources.yaml")
    ids = {e.id for e in entries}
    assert {"jobcode", "himalayas", "indeed", "naukri", "li_swadesh_kumar"} <= ids


def test_entry_carries_its_own_settings():
    [entry] = validate_source_registry({"sources": [_entry(max_pages=2)]})
    assert entry.fetch_method == "open_api"
    assert entry.setting("provider") == "himalayas"
    assert entry.setting("max_pages") == 2


def test_duplicate_identifier_rejected():
    with pytest.raises(InvalidRegistryError, match="himalayas.*duplicate"):
        validate_source_registry({"sources": [_entry(), _entry()]})


@pytest.mark.parametrize("field", ["id", "fetch_method", "enabled", "name"])
def test_missing_required_field_names_entry_and_field(field):
    with pytest.raises(InvalidRegistryError) as info:
        validate_source_registry({"sources": [_entry(**{field: ...})]})
    assert f"'{field}'" in str(info.value)
    expected_label = "#1" if field == "id" else "himalayas"
    assert expected_label in str(info.value)


def test_unknown_fetch_method_rejected():
    with pytest.raises(InvalidRegistryError, match="himalayas.*unsupported fetch method 'scrape_magic'"):
        validate_source_registry({"sources": [_entry(fetch_method="scrape_magic")]})


def test_missing_method_setting_rejected():
    with pytest.raises(InvalidRegistryError, match="'profile_url'"):
        validate_source_registry({"sources": [_entry(id="li_x", fetch_method="linkedin_profile_posts")]})


@pytest.mark.parametrize(
    "overrides",
    [{"api_token": "abc"}, {"password": "x"}, {"notes": "apify_api_ABCDEFGHIJKLMNOP"}],
)
def test_secrets_in_file_rejected(overrides):
    with pytest.raises(InvalidRegistryError, match="secret|token"):
        validate_source_registry({"sources": [_entry(**overrides)]})


def test_enabled_flag_must_be_boolean_and_disabled_entries_are_filtered():
    with pytest.raises(InvalidRegistryError, match="enabled"):
        validate_source_registry({"sources": [_entry(enabled="yes")]})
    entries = validate_source_registry({"sources": [_entry(), _entry(id="remotive", enabled=False)]})
    assert [e.id for e in enabled_entries(entries)] == ["himalayas"]


def test_top_level_shape_required():
    with pytest.raises(InvalidRegistryError, match="sources"):
        validate_source_registry({"targets": []})
