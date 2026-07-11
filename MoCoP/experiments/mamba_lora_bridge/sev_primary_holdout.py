#!/usr/bin/env python3
"""Deterministic primary SEV holdout selection and manifest validation.

The primary evaluation holdout is one skeleton from each of the eight SEV v0
topics. Selection is independent of model activations and human ranking: for
each topic, choose the skeleton with the lexicographically smallest SHA-256 of
its canonical four-variant content. The resulting membership is then bound to
the matched-delta frozen split.

This module is intentionally torch-free so split generation and verification
can run on any machine before a model process is started.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from matched_delta_recording import (
    FrozenSplit,
    RECIPE_TAG as MATCHED_DELTA_RECIPE,
    build_frozen_split,
    corpus_fingerprint,
    load_frozen_split,
    load_sev_corpus,
)


BRIDGE_DIR = Path(__file__).resolve().parent
DEFAULT_CORPUS_PATH = (
    BRIDGE_DIR / "fixtures" / "sev_disposition_v0" / "sev_disposition_v0.jsonl"
)
DEFAULT_MANIFEST_PATH = (
    BRIDGE_DIR / "fixtures" / "sev_disposition_v0" / "primary_holdout_v2.json"
)

SCHEMA_VERSION = "sev-primary-holdout-v2"
SELECTION_RECIPE = "one-per-topic-canonical-content-sha256-v2"
EXPECTED_TOPIC_COUNT = 8
EXPECTED_SKELETONS_PER_TOPIC = 5
EXPECTED_CLASSES = frozenset({"warm", "cold", "adversarial", "neutral"})


@dataclass(frozen=True)
class PrimaryHoldout:
    """Validated primary holdout plus its matched-delta training split."""

    manifest_id: str
    corpus_id: str
    corpus_sha256: str
    held_out_skeletons: tuple[str, ...]
    topic_selections: tuple[dict[str, str], ...]
    frozen_split: FrozenSplit


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        default=str,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _records_by_skeleton(
    corpus: Mapping[str, Mapping[str, Any]],
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for record_id, raw_record in corpus.items():
        skeleton_id = str(raw_record.get("skeleton_id", "")).strip()
        topic = str(raw_record.get("topic", "")).strip()
        disposition_class = str(raw_record.get("class", "")).strip()
        text = str(raw_record.get("text", ""))
        if not skeleton_id or not topic or disposition_class not in EXPECTED_CLASSES:
            raise ValueError(
                f"invalid SEV record {record_id!r}: skeleton_id/topic/class must be present "
                f"and class must be one of {sorted(EXPECTED_CLASSES)}"
            )
        grouped.setdefault(skeleton_id, []).append(
            {
                "id": str(record_id),
                "skeleton_id": skeleton_id,
                "topic": topic,
                "class": disposition_class,
                "text": text,
            }
        )

    for skeleton_id, records in grouped.items():
        topics = {record["topic"] for record in records}
        classes = {record["class"] for record in records}
        if len(topics) != 1:
            raise ValueError(
                f"skeleton {skeleton_id!r} spans multiple topics: {sorted(topics)}"
            )
        if classes != EXPECTED_CLASSES or len(records) != len(EXPECTED_CLASSES):
            raise ValueError(
                f"skeleton {skeleton_id!r} must contain exactly one variant for each "
                f"class {sorted(EXPECTED_CLASSES)}; got classes={sorted(classes)} "
                f"records={len(records)}"
            )
    return grouped


def skeleton_selection_digest(
    skeleton_id: str,
    records: Sequence[Mapping[str, str]],
) -> str:
    """Hash the canonical content used to select one skeleton within a topic."""

    topic_values = {record["topic"] for record in records}
    if len(topic_values) != 1:
        raise ValueError(f"skeleton {skeleton_id!r} has inconsistent topics")
    payload = {
        "selection_recipe": SELECTION_RECIPE,
        "skeleton_id": skeleton_id,
        "topic": next(iter(topic_values)),
        "variants": [
            {
                "class": record["class"],
                "id": record["id"],
                "text": record["text"],
            }
            for record in sorted(records, key=lambda item: (item["class"], item["id"]))
        ],
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def derive_topic_selections(
    corpus: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, str], ...]:
    """Return the deterministic one-skeleton-per-topic selection."""

    grouped = _records_by_skeleton(corpus)
    by_topic: dict[str, list[tuple[str, str]]] = {}
    for skeleton_id, records in grouped.items():
        topic = records[0]["topic"]
        digest = skeleton_selection_digest(skeleton_id, records)
        by_topic.setdefault(topic, []).append((digest, skeleton_id))

    if len(by_topic) != EXPECTED_TOPIC_COUNT:
        raise ValueError(
            f"SEV primary holdout requires exactly {EXPECTED_TOPIC_COUNT} topics; "
            f"got {len(by_topic)}: {sorted(by_topic)}"
        )

    selections: list[dict[str, str]] = []
    for topic in sorted(by_topic):
        candidates = by_topic[topic]
        if len(candidates) != EXPECTED_SKELETONS_PER_TOPIC:
            raise ValueError(
                f"topic {topic!r} must contain exactly {EXPECTED_SKELETONS_PER_TOPIC} "
                f"skeletons; got {len(candidates)}"
            )
        selection_digest, skeleton_id = min(candidates)
        selections.append(
            {
                "topic": topic,
                "skeleton_id": skeleton_id,
                "selection_digest": selection_digest,
            }
        )
    return tuple(selections)


def validate_requested_holdouts(
    corpus: Mapping[str, Mapping[str, Any]],
    requested: Sequence[str],
    *,
    expected: Sequence[str] | None = None,
) -> tuple[str, ...]:
    """Reject unknown, duplicate, or non-canonical holdout membership."""

    requested_tuple = tuple(str(item) for item in requested)
    if len(set(requested_tuple)) != len(requested_tuple):
        raise ValueError(f"duplicate holdout skeletons are forbidden: {requested_tuple}")

    real_skeletons = set(_records_by_skeleton(corpus))
    unknown = sorted(set(requested_tuple) - real_skeletons)
    if unknown:
        raise ValueError(f"unknown holdout skeletons: {unknown}")

    if expected is not None and set(requested_tuple) != set(expected):
        missing = sorted(set(expected) - set(requested_tuple))
        extra = sorted(set(requested_tuple) - set(expected))
        raise ValueError(
            f"holdout membership differs from deterministic primary selection; "
            f"missing={missing} extra={extra}"
        )
    return requested_tuple


def _validate_exact_split_exclusion(
    corpus: Mapping[str, Mapping[str, Any]],
    split: FrozenSplit,
    held_out_skeletons: Sequence[str],
) -> None:
    held_out = set(held_out_skeletons)
    expected_scenarios = {
        record_id
        for record_id, record in corpus.items()
        if record.get("class") != "neutral"
        and str(record.get("skeleton_id")) not in held_out
    }
    actual_scenarios = set(split.pairs)
    if actual_scenarios != expected_scenarios:
        missing = sorted(expected_scenarios - actual_scenarios)
        extra = sorted(actual_scenarios - expected_scenarios)
        raise ValueError(
            f"frozen split does not exactly exclude the requested skeletons; "
            f"missing_training_scenarios={missing} unexpected_scenarios={extra}"
        )

    leaked = sorted(
        scenario_id
        for scenario_id in actual_scenarios
        if str(corpus[scenario_id].get("skeleton_id")) in held_out
    )
    if leaked:
        raise ValueError(f"held-out skeletons leaked into training split: {leaked}")


def _manifest_id(manifest_without_id: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(canonical_json_bytes(manifest_without_id)).hexdigest()
    return f"primary-holdout-{digest[:20]}"


def build_primary_holdout_manifest(
    corpus_path: Path = DEFAULT_CORPUS_PATH,
    *,
    corpus_label: str | None = None,
) -> dict[str, Any]:
    corpus_path = Path(corpus_path)
    corpus = load_sev_corpus(corpus_path)
    if not corpus:
        raise ValueError(f"SEV corpus is empty or missing: {corpus_path}")

    selections = derive_topic_selections(corpus)
    expected_holdouts = tuple(item["skeleton_id"] for item in selections)
    held_out = validate_requested_holdouts(
        corpus,
        expected_holdouts,
        expected=expected_holdouts,
    )
    split = build_frozen_split(
        corpus,
        recipe=MATCHED_DELTA_RECIPE,
        held_out_skeletons=held_out,
    )
    _validate_exact_split_exclusion(corpus, split, held_out)

    manifest_without_id: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "selection_recipe": SELECTION_RECIPE,
        "selection_rule": (
            "Within each topic, select the skeleton with the lexicographically "
            "smallest SHA-256 of canonical four-variant content."
        ),
        "corpus": {
            "path": corpus_label or corpus_path.name,
            "sha256": sha256_file(corpus_path),
            "corpus_id": corpus_fingerprint(corpus),
        },
        "held_out_skeletons": list(held_out),
        "topic_selections": list(selections),
        "frozen_split": split.to_manifest(),
    }
    return {
        "manifest_id": _manifest_id(manifest_without_id),
        **manifest_without_id,
    }


def validate_primary_holdout_manifest(
    manifest: Mapping[str, Any],
    corpus_path: Path = DEFAULT_CORPUS_PATH,
) -> PrimaryHoldout:
    corpus_path = Path(corpus_path)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"primary holdout schema must be {SCHEMA_VERSION!r}, "
            f"got {manifest.get('schema_version')!r}"
        )
    if manifest.get("selection_recipe") != SELECTION_RECIPE:
        raise ValueError(
            f"selection recipe must be {SELECTION_RECIPE!r}, "
            f"got {manifest.get('selection_recipe')!r}"
        )

    corpus = load_sev_corpus(corpus_path)
    if not corpus:
        raise ValueError(f"SEV corpus is empty or missing: {corpus_path}")
    expected_selections = derive_topic_selections(corpus)
    expected_holdouts = tuple(item["skeleton_id"] for item in expected_selections)
    requested_holdouts = validate_requested_holdouts(
        corpus,
        manifest.get("held_out_skeletons", ()),
        expected=expected_holdouts,
    )
    if requested_holdouts != expected_holdouts:
        raise ValueError(
            "holdout skeletons are not in canonical topic order: "
            f"expected={expected_holdouts} got={requested_holdouts}"
        )

    if tuple(manifest.get("topic_selections", ())) != expected_selections:
        raise ValueError("topic selections or their content digests do not match the corpus")

    corpus_meta = manifest.get("corpus", {})
    expected_corpus_sha256 = sha256_file(corpus_path)
    expected_corpus_id = corpus_fingerprint(corpus)
    if corpus_meta.get("sha256") != expected_corpus_sha256:
        raise ValueError("primary holdout corpus SHA-256 mismatch")
    if corpus_meta.get("corpus_id") != expected_corpus_id:
        raise ValueError("primary holdout corpus fingerprint mismatch")

    frozen_manifest = manifest.get("frozen_split")
    if not isinstance(frozen_manifest, dict):
        raise ValueError("primary holdout manifest is missing frozen_split")
    split = load_frozen_split(frozen_manifest, corpus)
    if tuple(split.held_out_skeletons) != requested_holdouts:
        raise ValueError("frozen split holdouts differ from primary holdout membership")
    expected_split = build_frozen_split(
        corpus,
        recipe=MATCHED_DELTA_RECIPE,
        held_out_skeletons=requested_holdouts,
    )
    if split.to_manifest() != expected_split.to_manifest():
        raise ValueError("frozen split does not exactly match the deterministic training split")
    _validate_exact_split_exclusion(corpus, split, requested_holdouts)

    without_id = {key: value for key, value in manifest.items() if key != "manifest_id"}
    expected_manifest_id = _manifest_id(without_id)
    if manifest.get("manifest_id") != expected_manifest_id:
        raise ValueError("primary holdout manifest_id mismatch")

    return PrimaryHoldout(
        manifest_id=expected_manifest_id,
        corpus_id=expected_corpus_id,
        corpus_sha256=expected_corpus_sha256,
        held_out_skeletons=requested_holdouts,
        topic_selections=expected_selections,
        frozen_split=split,
    )


def load_primary_holdout_manifest(
    manifest_path: Path,
    corpus_path: Path = DEFAULT_CORPUS_PATH,
) -> PrimaryHoldout:
    with Path(manifest_path).open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    return validate_primary_holdout_manifest(manifest, corpus_path)


def training_warm_neutral_pairs(
    corpus: Mapping[str, Mapping[str, Any]],
    primary_holdout: PrimaryHoldout,
) -> list[tuple[str, str, str]]:
    """Return training-side (skeleton, warm text, neutral text) pairs only."""

    held_out = set(primary_holdout.held_out_skeletons)
    grouped = _records_by_skeleton(corpus)
    pairs: list[tuple[str, str, str]] = []
    for skeleton_id in sorted(grouped):
        if skeleton_id in held_out:
            continue
        by_class = {record["class"]: record for record in grouped[skeleton_id]}
        warm_id = by_class["warm"]["id"]
        neutral_id = by_class["neutral"]["id"]
        if warm_id not in primary_holdout.frozen_split.pairs:
            raise ValueError(
                f"training warm scenario {warm_id!r} is absent from frozen split "
                f"{primary_holdout.frozen_split.split_id}"
            )
        if primary_holdout.frozen_split.pairs[warm_id] != neutral_id:
            raise ValueError(
                f"frozen split maps {warm_id!r} to the wrong neutral control"
            )
        pairs.append((skeleton_id, by_class["warm"]["text"], by_class["neutral"]["text"]))

    expected_count = len(grouped) - len(held_out)
    if len(pairs) != expected_count:
        raise ValueError(
            f"expected {expected_count} training warm-neutral pairs, got {len(pairs)}"
        )
    if set(item[0] for item in pairs) & held_out:
        raise ValueError("held-out skeleton leaked into G0b training pairs")
    return pairs


def _publish_json_no_overwrite(payload: Mapping[str, Any], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing manifest: {path}")

    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate a new immutable manifest")
    generate.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    generate.add_argument("--out", type=Path, default=DEFAULT_MANIFEST_PATH)

    check = subparsers.add_parser("check", help="Re-derive and validate an existing manifest")
    check.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    check.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "generate":
        manifest = build_primary_holdout_manifest(
            args.corpus,
            corpus_label="fixtures/sev_disposition_v0/sev_disposition_v0.jsonl",
        )
        _publish_json_no_overwrite(manifest, args.out)
        print(
            f"wrote {args.out} manifest_id={manifest['manifest_id']} "
            f"split_id={manifest['frozen_split']['split_id']}"
        )
        return 0

    primary = load_primary_holdout_manifest(args.manifest, args.corpus)
    print(
        f"verified {args.manifest} manifest_id={primary.manifest_id} "
        f"split_id={primary.frozen_split.split_id} "
        f"held_out={list(primary.held_out_skeletons)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
