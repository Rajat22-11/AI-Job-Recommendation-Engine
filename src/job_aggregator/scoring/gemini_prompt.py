"""Load the Gemini review prompt from `config/gemini_prompt.yaml`, so its wording can change without code edits."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from job_aggregator.domain.errors import InvalidSettingsError

PROMPT_FILE_NAME = "gemini_prompt.yaml"
REQUIRED_PLACEHOLDERS = ("{criteria}", "{job}", "{rules_score}", "{rules_reason}")


@dataclass(frozen=True)
class GeminiPrompt:
    instruction: str       # sent as written; holds the JSON answer format the code relies on
    data_template: str     # filled in per job with the placeholders in REQUIRED_PLACEHOLDERS


def load_gemini_prompt(path: str | Path) -> GeminiPrompt:
    """Read and check the prompt file. A missing key, an empty text or a missing placeholder stops the run."""
    file_path = Path(path)
    try:
        document = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise InvalidSettingsError("gemini_prompt.yaml", f"cannot be read: {exc}") from exc
    except yaml.YAMLError as exc:
        raise InvalidSettingsError("gemini_prompt.yaml", f"not valid YAML: {exc}") from exc
    if not isinstance(document, dict):
        raise InvalidSettingsError("gemini_prompt.yaml", "must be a mapping with 'instruction' and 'data_template'")
    for key in ("instruction", "data_template"):
        value = document.get(key)
        if not isinstance(value, str) or not value.strip():
            raise InvalidSettingsError(key, "must be a non-empty text in gemini_prompt.yaml")
    template = document["data_template"]
    missing = [name for name in REQUIRED_PLACEHOLDERS if name not in template]
    if missing:
        raise InvalidSettingsError("data_template", f"must contain {', '.join(missing)}")
    try:
        template.format(criteria="", job="", rules_score=0, rules_reason="")
    except (KeyError, IndexError, ValueError) as exc:
        raise InvalidSettingsError("data_template", f"has a stray brace or unknown placeholder: {exc}") from exc
    return GeminiPrompt(instruction=document["instruction"].strip(), data_template=template.strip())
