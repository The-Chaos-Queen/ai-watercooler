from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from copy import deepcopy
from typing import Any

SUMMARY_DRAFT_SCHEMA_VERSION = "watercooler.summary-draft.v1"

SECTION_KINDS = (
    "overview",
    "decision",
    "hold",
    "open_question",
    "orientation",
)

MAX_SUMMARY_TITLE_LENGTH = 200
MAX_SECTION_ITEMS = 25
MAX_SOURCE_MESSAGE_IDS = 50
MAX_TASK_PROPOSALS = 20
MAX_TASK_PROPOSAL_TITLE_LENGTH = 200
MAX_TASK_PROPOSAL_DESCRIPTION_LENGTH = 1_000

_SECTION_TITLES = {
    "overview": "Overview",
    "decision": "Decisions",
    "hold": "Holds",
    "open_question": "Open Questions",
    "orientation": "Orientation",
}

_PLAIN_TEXT_PATTERN = r"^[^\u0000-\u001f\u007f-\u009f\u2028\u2029]+$"


def _source_ids_schema() -> dict[str, Any]:
    return {
        "type": "array",
        "minItems": 1,
        "maxItems": MAX_SOURCE_MESSAGE_IDS,
        "uniqueItems": True,
        "items": {"type": "integer", "minimum": 1},
    }


SUMMARY_DRAFT_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Watercooler summary draft",
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "title", "sections", "task_proposals"],
    "properties": {
        "schema_version": {"const": SUMMARY_DRAFT_SCHEMA_VERSION},
        "title": {
            "type": "string",
            "minLength": 1,
            "maxLength": MAX_SUMMARY_TITLE_LENGTH,
            "pattern": _PLAIN_TEXT_PATTERN,
        },
        "sections": {
            "type": "array",
            "minItems": 1,
            "maxItems": len(SECTION_KINDS),
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "items"],
                "properties": {
                    "kind": {"enum": list(SECTION_KINDS)},
                    "items": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": MAX_SECTION_ITEMS,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["text", "source_message_ids"],
                            "properties": {
                                "text": {
                                    "type": "string",
                                    "minLength": 1,
                                    "maxLength": 500,
                                    "pattern": _PLAIN_TEXT_PATTERN,
                                },
                                "source_message_ids": _source_ids_schema(),
                            },
                        },
                    },
                },
            },
        },
        "task_proposals": {
            "type": "array",
            "maxItems": MAX_TASK_PROPOSALS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "description", "source_message_ids"],
                "properties": {
                    "title": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": MAX_TASK_PROPOSAL_TITLE_LENGTH,
                        "pattern": _PLAIN_TEXT_PATTERN,
                    },
                    "description": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": MAX_TASK_PROPOSAL_DESCRIPTION_LENGTH,
                        "pattern": _PLAIN_TEXT_PATTERN,
                    },
                    "source_message_ids": _source_ids_schema(),
                },
            },
        },
    },
}

# LM Studio's llama.cpp grammar path accepts a conservative JSON Schema subset.
# The full schema above remains the normative contract; this schema constrains
# shape during decoding, then validate_summary_draft enforces every bound.
SUMMARY_DRAFT_MODEL_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "title", "sections", "task_proposals"],
    "properties": {
        "schema_version": {"type": "string", "enum": [SUMMARY_DRAFT_SCHEMA_VERSION]},
        "title": {"type": "string"},
        "sections": {
            "type": "object",
            "additionalProperties": False,
            "required": list(SECTION_KINDS),
            "properties": {
                kind: {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["text", "source_message_ids"],
                        "properties": {
                            "text": {"type": "string"},
                            "source_message_ids": {
                                "type": "array",
                                "items": {"type": "integer"},
                            },
                        },
                    },
                }
                for kind in SECTION_KINDS
            },
        },
        "task_proposals": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "description", "source_message_ids"],
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "source_message_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                },
            },
        },
    },
}


def _fail(path: str, message: str) -> ValueError:
    return ValueError(f"{path}: {message}")


def _require_exact_dict(value: Any, path: str, keys: set[str]) -> dict[str, Any]:
    if type(value) is not dict:
        raise _fail(path, "must be an object")
    actual_keys = set(value)
    if actual_keys != keys:
        missing = sorted(keys - actual_keys)
        unknown = sorted(actual_keys - keys, key=str)
        details = []
        if missing:
            details.append(f"missing keys {missing!r}")
        if unknown:
            details.append(f"unknown keys {unknown!r}")
        raise _fail(path, "; ".join(details))
    return value


def _require_exact_list(value: Any, path: str) -> list[Any]:
    if type(value) is not list:
        raise _fail(path, "must be an array")
    return value


def _contains_forbidden_text_character(value: str) -> bool:
    return any(
        ord(character) <= 0x1F
        or 0x7F <= ord(character) <= 0x9F
        or 0xD800 <= ord(character) <= 0xDFFF
        or character in {"\u2028", "\u2029"}
        for character in value
    )


def _normalize_plain_text(value: Any, path: str, max_length: int) -> str:
    if type(value) is not str:
        raise _fail(path, "must be a string")
    if _contains_forbidden_text_character(value):
        raise _fail(path, "must not contain control, line-break, or surrogate characters")
    if len(value) > max_length:
        raise _fail(path, f"must be at most {max_length} characters")
    normalized = value.strip()
    if not normalized:
        raise _fail(path, "must not be empty")
    return str(normalized)


def _task_title_comparison_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(normalized.split()).casefold()


def _normalize_allowed_source_ids(allowed_source_message_ids: Iterable[int]) -> set[int]:
    if isinstance(allowed_source_message_ids, (str, bytes, bytearray)):
        raise _fail("allowed_source_message_ids", "must be an iterable of positive integers")
    try:
        values = list(allowed_source_message_ids)
    except (TypeError, ValueError) as exc:
        raise _fail("allowed_source_message_ids", "must be an iterable of positive integers") from exc

    normalized: set[int] = set()
    for index, value in enumerate(values):
        if type(value) is not int or value <= 0:
            raise _fail(f"allowed_source_message_ids[{index}]", "must be a positive integer")
        normalized.add(int(value))
    return normalized


def build_summary_draft_model_json_schema(
    allowed_source_message_ids: Iterable[int],
) -> dict[str, Any]:
    """Bind the decoding grammar to the exact admissible message IDs."""

    allowed_source_ids = sorted(_normalize_allowed_source_ids(allowed_source_message_ids))
    if not allowed_source_ids:
        raise _fail("allowed_source_message_ids", "must contain at least one source message ID")
    schema = deepcopy(SUMMARY_DRAFT_MODEL_JSON_SCHEMA)
    source_schema = {"type": "integer", "enum": allowed_source_ids}
    section_schemas = schema["properties"]["sections"]["properties"]
    for section_schema in section_schemas.values():
        section_item = section_schema["items"]
        section_item["properties"]["source_message_ids"]["items"] = deepcopy(source_schema)
    proposal_sources = schema["properties"]["task_proposals"]["items"]
    proposal_sources["properties"]["source_message_ids"]["items"] = deepcopy(source_schema)
    return schema


def canonicalize_summary_draft_model_output(draft: Any) -> dict[str, Any]:
    """Convert the provider grammar's keyed sections to the canonical list."""

    root = _require_exact_dict(
        draft,
        "$",
        {"schema_version", "title", "sections", "task_proposals"},
    )
    sections = _require_exact_dict(root["sections"], "$.sections", set(SECTION_KINDS))
    canonical_sections = []
    for kind in SECTION_KINDS:
        items = _require_exact_list(sections[kind], f"$.sections.{kind}")
        if items:
            canonical_sections.append({"kind": kind, "items": list(items)})
    return {
        "schema_version": root["schema_version"],
        "title": root["title"],
        "sections": canonical_sections,
        "task_proposals": root["task_proposals"],
    }


def _normalize_source_ids(
    value: Any,
    path: str,
    allowed_source_ids: set[int] | None,
) -> list[int]:
    source_ids = _require_exact_list(value, path)
    if not source_ids:
        raise _fail(path, "must contain at least one source message ID")
    if len(source_ids) > MAX_SOURCE_MESSAGE_IDS:
        raise _fail(path, f"must contain at most {MAX_SOURCE_MESSAGE_IDS} source message IDs")

    normalized = []
    seen = set()
    for index, source_id in enumerate(source_ids):
        item_path = f"{path}[{index}]"
        if type(source_id) is not int or source_id <= 0:
            raise _fail(item_path, "must be a positive integer")
        if source_id in seen:
            raise _fail(item_path, "must not duplicate a source message ID")
        if allowed_source_ids is not None and source_id not in allowed_source_ids:
            raise _fail(item_path, "does not identify an allowed source message")
        seen.add(source_id)
        normalized.append(int(source_id))
    return normalized


def _validate_summary_draft(
    draft: Any,
    allowed_source_ids: set[int] | None,
    expected_schema_version: str,
) -> dict[str, Any]:
    root = _require_exact_dict(
        draft,
        "$",
        {"schema_version", "title", "sections", "task_proposals"},
    )
    if type(root["schema_version"]) is not str or root["schema_version"] != expected_schema_version:
        raise _fail("$.schema_version", f"must equal {expected_schema_version!r}")

    title = _normalize_plain_text(root["title"], "$.title", MAX_SUMMARY_TITLE_LENGTH)
    sections = _require_exact_list(root["sections"], "$.sections")
    if not sections:
        raise _fail("$.sections", "must contain at least one section")
    if len(sections) > len(SECTION_KINDS):
        raise _fail("$.sections", f"must contain at most {len(SECTION_KINDS)} sections")

    normalized_sections = []
    seen_kinds = set()
    for section_index, section_value in enumerate(sections):
        section_path = f"$.sections[{section_index}]"
        section = _require_exact_dict(section_value, section_path, {"kind", "items"})
        kind = section["kind"]
        if type(kind) is not str or kind not in SECTION_KINDS:
            raise _fail(f"{section_path}.kind", f"must be one of {SECTION_KINDS!r}")
        if kind in seen_kinds:
            raise _fail(f"{section_path}.kind", "must not duplicate a section kind")
        seen_kinds.add(kind)

        items = _require_exact_list(section["items"], f"{section_path}.items")
        if not items:
            raise _fail(f"{section_path}.items", "must contain at least one item")
        if len(items) > MAX_SECTION_ITEMS:
            raise _fail(
                f"{section_path}.items",
                f"must contain at most {MAX_SECTION_ITEMS} items",
            )

        normalized_items = []
        for item_index, item_value in enumerate(items):
            item_path = f"{section_path}.items[{item_index}]"
            item = _require_exact_dict(item_value, item_path, {"text", "source_message_ids"})
            normalized_items.append(
                {
                    "text": _normalize_plain_text(item["text"], f"{item_path}.text", 500),
                    "source_message_ids": _normalize_source_ids(
                        item["source_message_ids"],
                        f"{item_path}.source_message_ids",
                        allowed_source_ids,
                    ),
                }
            )
        normalized_sections.append({"kind": str(kind), "items": normalized_items})

    proposals = _require_exact_list(root["task_proposals"], "$.task_proposals")
    if len(proposals) > MAX_TASK_PROPOSALS:
        raise _fail("$.task_proposals", f"must contain at most {MAX_TASK_PROPOSALS} proposals")

    normalized_proposals = []
    seen_proposal_titles = set()
    for proposal_index, proposal_value in enumerate(proposals):
        proposal_path = f"$.task_proposals[{proposal_index}]"
        proposal = _require_exact_dict(
            proposal_value,
            proposal_path,
            {"title", "description", "source_message_ids"},
        )
        proposal_title = _normalize_plain_text(
            proposal["title"],
            f"{proposal_path}.title",
            MAX_TASK_PROPOSAL_TITLE_LENGTH,
        )
        canonical_title = _task_title_comparison_key(proposal_title)
        if canonical_title in seen_proposal_titles:
            raise _fail(f"{proposal_path}.title", "must not duplicate a proposal title")
        seen_proposal_titles.add(canonical_title)
        normalized_proposals.append(
            {
                "title": proposal_title,
                "description": _normalize_plain_text(
                    proposal["description"],
                    f"{proposal_path}.description",
                    MAX_TASK_PROPOSAL_DESCRIPTION_LENGTH,
                ),
                "source_message_ids": _normalize_source_ids(
                    proposal["source_message_ids"],
                    f"{proposal_path}.source_message_ids",
                    allowed_source_ids,
                ),
            }
        )

    return {
        "schema_version": str(root["schema_version"]),
        "title": title,
        "sections": normalized_sections,
        "task_proposals": normalized_proposals,
    }


def validate_summary_draft(
    draft: Any,
    allowed_source_message_ids: Iterable[int],
    expected_schema_version: str = SUMMARY_DRAFT_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Validate and detach a model-produced summary draft from its input objects."""

    if (
        type(expected_schema_version) is not str
        or not expected_schema_version
        or _contains_forbidden_text_character(expected_schema_version)
    ):
        raise _fail("expected_schema_version", "must be a nonempty string")
    allowed_source_ids = _normalize_allowed_source_ids(allowed_source_message_ids)
    return _validate_summary_draft(draft, allowed_source_ids, expected_schema_version)


def validate_task_proposals_are_new(
    draft: dict[str, Any],
    *,
    existing_task_titles: Iterable[str],
) -> dict[str, Any]:
    """Refuse proposals whose normalized title already exists on the Taskboard."""

    existing = {
        _task_title_comparison_key(title)
        for title in existing_task_titles
        if type(title) is str and title.strip()
    }
    for index, proposal in enumerate(draft["task_proposals"]):
        if _task_title_comparison_key(proposal["title"]) in existing:
            raise _fail(
                f"$.task_proposals[{index}].title",
                "duplicates an existing Taskboard task",
            )
    return draft


_MARKDOWN_SPECIAL = re.compile(r"([\\`*{}\[\]()<>#+\-.!_|>])")


def _escape_markdown(value: str) -> str:
    return _MARKDOWN_SPECIAL.sub(r"\\\1", value)


def _render_sources(source_message_ids: list[int]) -> str:
    return ", ".join(f"#{source_id}" for source_id in source_message_ids)


def render_summary_markdown(draft: Any) -> str:
    """Render a structurally valid draft without granting task authority."""

    normalized = _validate_summary_draft(draft, None, SUMMARY_DRAFT_SCHEMA_VERSION)
    lines = [f"# {_escape_markdown(normalized['title'])}"]

    for section in normalized["sections"]:
        lines.extend(["", f"## {_SECTION_TITLES[section['kind']]}"])
        for item in section["items"]:
            text = _escape_markdown(item["text"])
            sources = _render_sources(item["source_message_ids"])
            lines.append(f"- {text} (sources: {sources})")

    if normalized["task_proposals"]:
        lines.extend(
            [
                "",
                "## Task Proposals",
                "",
                "> Proposal only. These entries are not created, assigned, or authorized tasks.",
            ]
        )
        for proposal in normalized["task_proposals"]:
            proposal_title = _escape_markdown(proposal["title"])
            description = _escape_markdown(proposal["description"])
            sources = _render_sources(proposal["source_message_ids"])
            lines.extend(
                [
                    "",
                    f"- **Proposal only: {proposal_title}**",
                    f"  {description} (sources: {sources})",
                ]
            )

    return "\n".join(lines) + "\n"
