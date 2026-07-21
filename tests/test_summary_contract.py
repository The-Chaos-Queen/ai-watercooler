from __future__ import annotations

import copy

import pytest

from watercooler.summary_contract import (
    MAX_SECTION_ITEMS,
    MAX_TASK_PROPOSALS,
    SUMMARY_DRAFT_JSON_SCHEMA,
    SUMMARY_DRAFT_MODEL_JSON_SCHEMA,
    SUMMARY_DRAFT_SCHEMA_VERSION,
    build_summary_draft_model_json_schema,
    canonicalize_summary_draft_model_output,
    render_summary_markdown,
    validate_summary_draft,
)


def valid_draft() -> dict:
    return {
        "schema_version": SUMMARY_DRAFT_SCHEMA_VERSION,
        "title": "  Project state  ",
        "sections": [
            {
                "kind": "overview",
                "items": [
                    {"text": "  The dispatcher is running.  ", "source_message_ids": [101, 102]},
                ],
            },
            {
                "kind": "open_question",
                "items": [
                    {"text": "Which model should own triage?", "source_message_ids": [103]},
                ],
            },
        ],
        "task_proposals": [
            {
                "title": "  Benchmark local triage  ",
                "description": "Compare deterministic and local-model modes.",
                "source_message_ids": [102, 103],
            }
        ],
    }


def test_validate_normalizes_and_detaches_builtins() -> None:
    draft = valid_draft()
    normalized = validate_summary_draft(draft, (101, 102, 103))

    assert normalized == {
        "schema_version": SUMMARY_DRAFT_SCHEMA_VERSION,
        "title": "Project state",
        "sections": [
            {
                "kind": "overview",
                "items": [
                    {"text": "The dispatcher is running.", "source_message_ids": [101, 102]},
                ],
            },
            {
                "kind": "open_question",
                "items": [
                    {"text": "Which model should own triage?", "source_message_ids": [103]},
                ],
            },
        ],
        "task_proposals": [
            {
                "title": "Benchmark local triage",
                "description": "Compare deterministic and local-model modes.",
                "source_message_ids": [102, 103],
            }
        ],
    }
    assert normalized is not draft
    assert normalized["sections"] is not draft["sections"]
    normalized["sections"][0]["items"][0]["source_message_ids"].append(999)
    assert draft["sections"][0]["items"][0]["source_message_ids"] == [101, 102]


@pytest.mark.parametrize(
    "location",
    [
        ("sections", 999),
        ("task_proposals", 999),
    ],
)
def test_validate_rejects_hallucinated_source_ids(location: tuple[str, int]) -> None:
    draft = valid_draft()
    collection, hallucinated_id = location
    if collection == "sections":
        draft["sections"][0]["items"][0]["source_message_ids"] = [hallucinated_id]
    else:
        draft["task_proposals"][0]["source_message_ids"] = [hallucinated_id]

    with pytest.raises(ValueError, match="allowed source message"):
        validate_summary_draft(draft, {101, 102, 103})


@pytest.mark.parametrize(
    "mutate",
    [
        lambda draft: draft.update({"unexpected": True}),
        lambda draft: draft.__setitem__("sections", tuple(draft["sections"])),
        lambda draft: draft["sections"][0].update({"extra": "field"}),
        lambda draft: draft["sections"][0]["items"][0].__setitem__("source_message_ids", [True]),
        lambda draft: draft["sections"][0]["items"][0].__setitem__("text", "two\nlines"),
        lambda draft: draft["sections"][0]["items"][0].__setitem__("text", "lone \ud800"),
        lambda draft: draft["sections"].append(copy.deepcopy(draft["sections"][0])),
        lambda draft: draft["task_proposals"].append(
            {
                "title": "benchmark LOCAL triage",
                "description": "Duplicate after case folding.",
                "source_message_ids": [101],
            }
        ),
        lambda draft: draft["task_proposals"].append(
            {
                "title": "Benchmark   LOCAL triage",
                "description": "Duplicate after whitespace normalization.",
                "source_message_ids": [101],
            }
        ),
        lambda draft: draft["task_proposals"][0].__setitem__("source_message_ids", [102, 102]),
    ],
    ids=[
        "root-extra-key",
        "non-list-sections",
        "section-extra-key",
        "boolean-source-id",
        "control-character",
        "surrogate-character",
        "duplicate-section-kind",
        "duplicate-proposal-title",
        "duplicate-proposal-title-whitespace",
        "duplicate-source-id",
    ],
)
def test_validate_rejects_malformed_or_ambiguous_drafts(mutate) -> None:
    draft = valid_draft()
    mutate(draft)

    with pytest.raises(ValueError):
        validate_summary_draft(draft, {101, 102, 103})


def test_render_escapes_model_controlled_markdown_and_labels_proposals() -> None:
    draft = valid_draft()
    draft["title"] = "# State <unsafe>"
    draft["sections"][0]["items"][0]["text"] = "[click](javascript:alert(1)) *now* <script>"
    draft["task_proposals"][0]["title"] = "[Run](https://example.test)"
    draft["task_proposals"][0]["description"] = "Use `shell` > output"
    normalized = validate_summary_draft(draft, {101, 102, 103})

    rendered = render_summary_markdown(normalized)

    assert rendered.startswith("# \\# State \\<unsafe\\>\n")
    assert "[click](javascript" not in rendered
    assert "\\[click\\]\\(javascript:alert\\(1\\)\\) \\*now\\* \\<script\\>" in rendered
    assert "**Proposal only: \\[Run\\]\\(https://example\\.test\\)**" in rendered
    assert "> Proposal only. These entries are not created, assigned, or authorized tasks." in rendered
    assert "Use \\`shell\\` \\> output" in rendered


def test_render_is_deterministic() -> None:
    normalized = validate_summary_draft(valid_draft(), {101, 102, 103})

    first = render_summary_markdown(normalized)
    second = render_summary_markdown(copy.deepcopy(normalized))

    assert first == second
    assert first.endswith("\n")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda draft: draft["sections"][0].__setitem__(
            "items",
            [
                {"text": f"Item {index}", "source_message_ids": [101]}
                for index in range(MAX_SECTION_ITEMS + 1)
            ],
        ),
        lambda draft: draft.__setitem__(
            "task_proposals",
            [
                {
                    "title": f"Proposal {index}",
                    "description": "Bounded proposal.",
                    "source_message_ids": [101],
                }
                for index in range(MAX_TASK_PROPOSALS + 1)
            ],
        ),
        lambda draft: draft["sections"][0]["items"][0].__setitem__("text", "x" * 501),
    ],
    ids=["section-items", "task-proposals", "section-text"],
)
def test_validate_enforces_collection_and_text_bounds(mutate) -> None:
    draft = valid_draft()
    mutate(draft)

    with pytest.raises(ValueError, match="at most"):
        validate_summary_draft(draft, {101, 102, 103})


def test_structured_output_schema_is_closed_and_versioned() -> None:
    assert SUMMARY_DRAFT_JSON_SCHEMA["additionalProperties"] is False
    assert SUMMARY_DRAFT_JSON_SCHEMA["properties"]["schema_version"] == {
        "const": SUMMARY_DRAFT_SCHEMA_VERSION
    }
    section_schema = SUMMARY_DRAFT_JSON_SCHEMA["properties"]["sections"]["items"]
    proposal_schema = SUMMARY_DRAFT_JSON_SCHEMA["properties"]["task_proposals"]["items"]
    assert section_schema["additionalProperties"] is False
    assert section_schema["properties"]["items"]["items"]["additionalProperties"] is False
    assert proposal_schema["additionalProperties"] is False


def test_model_schema_uses_lmstudio_compatible_subset() -> None:
    assert SUMMARY_DRAFT_MODEL_JSON_SCHEMA["additionalProperties"] is False
    assert SUMMARY_DRAFT_MODEL_JSON_SCHEMA["properties"]["schema_version"] == {
        "type": "string",
        "enum": [SUMMARY_DRAFT_SCHEMA_VERSION],
    }

    def schema_keywords(value):
        if type(value) is dict:
            for key, child in value.items():
                yield key
                yield from schema_keywords(child)
        elif type(value) is list:
            for child in value:
                yield from schema_keywords(child)

    keywords = set(schema_keywords(SUMMARY_DRAFT_MODEL_JSON_SCHEMA))
    assert {"$schema", "const", "pattern", "uniqueItems"}.isdisjoint(keywords)


def test_model_schema_binds_both_citation_surfaces_to_allowed_ids() -> None:
    schema = build_summary_draft_model_json_schema({103, 101})
    proposal_item = schema["properties"]["task_proposals"]["items"]

    for section_schema in schema["properties"]["sections"]["properties"].values():
        assert section_schema["items"]["properties"]["source_message_ids"]["items"] == {
            "type": "integer",
            "enum": [101, 103],
        }
    assert proposal_item["properties"]["source_message_ids"]["items"] == {
        "type": "integer",
        "enum": [101, 103],
    }
    for section_schema in SUMMARY_DRAFT_MODEL_JSON_SCHEMA["properties"]["sections"][
        "properties"
    ].values():
        assert section_schema["items"]["properties"]["source_message_ids"]["items"] == {
            "type": "integer"
        }


def test_model_output_keyed_sections_canonicalize_in_fixed_order() -> None:
    model_output = {
        "schema_version": SUMMARY_DRAFT_SCHEMA_VERSION,
        "title": "Orientation",
        "sections": {
            "overview": [],
            "decision": [{"text": "Decision", "source_message_ids": [101]}],
            "hold": [],
            "open_question": [{"text": "Question", "source_message_ids": [102]}],
            "orientation": [],
        },
        "task_proposals": [],
    }

    canonical = canonicalize_summary_draft_model_output(model_output)
    assert [section["kind"] for section in canonical["sections"]] == ["decision", "open_question"]
    assert validate_summary_draft(canonical, {101, 102}) == canonical
