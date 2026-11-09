"""Recognise "<Company> IS HIRING" posts and read their labelled lines (Role, Experience, Location, ...).

Marker phrases and label aliases come from settings, so a new influencer's wording is a config change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from job_aggregator.settings.app_settings import LinkedInSettings

_URL = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)
_LABEL_LINE = re.compile(r"^\s*[\W_]*\s*([A-Za-z][A-Za-z /&'()-]{0,40}?)\s*[:\-–]\s*(.*)$")


class PostKind(str, Enum):
    HIRING = "hiring"
    IGNORED = "ignored"    # no hiring marker or no link: not a job post
    UNPARSED = "unparsed"  # looks like a hiring post but no role could be read


@dataclass
class ParsedHiringPost:
    kind: PostKind
    reason: str = ""
    company: str | None = None
    role: str | None = None
    experience: str | None = None
    batch: str | None = None
    location: str | None = None
    skills: list[str] = field(default_factory=list)
    stipend: str | None = None
    apply_link: str | None = None


def _alias_lookup(settings: LinkedInSettings) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for field_name, aliases in settings.field_aliases.model_dump().items():
        for alias in aliases:
            lookup.setdefault(alias.strip().lower(), field_name)
    return lookup


def _find_marker_line(lines: list[str], markers: list[str]) -> tuple[int, str] | None:
    for index, line in enumerate(lines):
        lower = line.lower()
        for marker in markers:
            if marker.lower() in lower:
                return index, marker
    return None


def _company_from_marker(line: str, marker: str) -> str | None:
    position = line.lower().find(marker.lower())
    candidate = re.sub(r"^[\W_]+|[\W_]+$", "", line[:position]).strip()
    if not candidate or candidate.lower() in ("we", "we are", "we're", "now"):
        return None
    return candidate


def _read_labelled_fields(lines: list[str], aliases: dict[str, str]) -> dict[str, str]:
    """Map field -> value. A label with an empty value takes the following lines up to a blank line or label."""
    fields: dict[str, str] = {}
    block_stop_labels = set(aliases) | {"soft skills", "good to have", "responsibilities"}
    index = 0
    while index < len(lines):
        match = _LABEL_LINE.match(lines[index])
        field_name = aliases.get(match.group(1).strip().lower()) if match else None
        if not field_name:
            index += 1
            continue
        value = match.group(2).strip()
        index += 1
        if not value:
            block: list[str] = []
            while index < len(lines) and lines[index].strip():
                next_match = _LABEL_LINE.match(lines[index])
                if next_match and next_match.group(1).strip().lower() in block_stop_labels:
                    break
                block.append(lines[index].strip())
                index += 1
            value = " ".join(block).strip()
        if value and field_name not in fields:
            fields[field_name] = value
    return fields


def _split_skills(text: str | None) -> list[str]:
    if not text:
        return []
    flat = re.sub(r"\([^)]*\)", lambda m: m.group(0).replace(",", ";"), text)  # keep "(e.g., Python, Java)" whole
    return [part.strip(" .;") for part in flat.split(",") if part.strip(" .;")]


def parse_hiring_post(text: str, settings: LinkedInSettings) -> ParsedHiringPost:
    """Classify a post and, for hiring posts, read its fields."""
    lines = [line.rstrip() for line in (text or "").splitlines()]
    marker = _find_marker_line(lines, settings.hiring_markers)
    urls = _URL.findall(text or "")
    if not marker:
        return ParsedHiringPost(PostKind.IGNORED, reason="no hiring marker")
    if not urls:
        return ParsedHiringPost(PostKind.IGNORED, reason="hiring marker but no link")

    aliases = _alias_lookup(settings)
    fields = _read_labelled_fields(lines, aliases)
    apply_link = None
    labelled_link = fields.get("apply_link", "")
    if found := _URL.search(labelled_link):
        apply_link = found.group(0)
    else:
        apply_link = next((u for u in urls if "lnkd.in" in u.lower()), urls[0])

    marker_index, marker_phrase = marker
    company = fields.get("company") or _company_from_marker(lines[marker_index], marker_phrase)
    role = fields.get("role")
    if not role:
        return ParsedHiringPost(PostKind.UNPARSED, reason="hiring marker and link found but no role line",
                                company=company, apply_link=apply_link)
    if not company:
        return ParsedHiringPost(PostKind.UNPARSED, reason="role found but no company", role=role,
                                apply_link=apply_link)
    return ParsedHiringPost(
        PostKind.HIRING,
        company=company,
        role=role,
        experience=fields.get("experience"),
        batch=fields.get("batch"),
        location=fields.get("location"),
        skills=_split_skills(fields.get("skills")),
        stipend=fields.get("stipend"),
        apply_link=apply_link,
    )
