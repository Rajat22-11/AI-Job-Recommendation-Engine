"""The example entries in the docs must pass registry validation, so following a doc always works."""

import re

import yaml

from job_aggregator.registry.check_source_registry import main as check_registry
from job_aggregator.registry.load_source_registry import validate_source_registry
from tests.conftest import REPO_ROOT


def _yaml_blocks(doc_name):
    text = (REPO_ROOT / "docs" / doc_name).read_text(encoding="utf-8")
    return re.findall(r"```yaml\n(.*?)```", text, re.S)


def _entries_from_block(block):
    parsed = yaml.safe_load(block)
    return parsed["sources"] if isinstance(parsed, dict) else parsed


def test_registry_doc_examples_validate():
    for block in _yaml_blocks("source-registry.md"):
        entries = validate_source_registry({"sources": _entries_from_block(block)})
        assert entries


def test_linkedin_doc_example_added_to_real_registry_validates():
    registry = yaml.safe_load((REPO_ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))
    [block] = _yaml_blocks("linkedin-profiles.md")
    registry["sources"].extend(_entries_from_block(block))
    entries = validate_source_registry(registry)
    assert any(e.id == "li_firstname_lastname" and e.fetch_method == "linkedin_profile_posts" for e in entries)


def test_check_command_reports_ok(capsys):
    assert check_registry([str(REPO_ROOT / "config" / "sources.yaml")]) == 0
    assert "OK:" in capsys.readouterr().out
