from memory_evidence import (
    DIRECT_SHARED,
    GROUP_SHARED,
    THIRD_PARTY,
    UNCERTAIN,
    classify_evidence_for_subject,
    collection_owner,
    enrich_memory_evidence_metadata,
)


def test_collection_owner_from_private_qdrant_name():
    assert collection_owner("mocop_private_vesper") == "Vesper"
    assert collection_owner("exocortex") == ""


def test_direct_shared_episode_for_current_interlocutor():
    metadata = {
        "speaker_name": "Laura",
        "qdrant_collection": "mocop_private_alex",
        "user": "Laura said the croissant was almond.",
        "response": "I will remember almond croissant.",
    }

    enriched = enrich_memory_evidence_metadata("Laura and Alex discussed croissants.", metadata)

    assert enriched["evidence_schema_version"] == "d2_memory_evidence_v1"
    assert enriched["instance_owner"] == "Alex"
    assert enriched["current_interlocutor"] == "Laura"
    assert enriched["speaker"] == "Laura"
    assert enriched["participant_set"] == ["Laura"]
    assert enriched["evidence_kind"] == DIRECT_SHARED
    assert enriched["evidence_confidence"] == 0.95
    assert classify_evidence_for_subject(enriched, "Laura") == DIRECT_SHARED


def test_third_party_mention_is_distinct_from_direct_speaker():
    metadata = {
        "speaker_name": "Vesper",
        "qdrant_collection": "mocop_private_vesper",
        "people": ["Vesper", "Pinky"],
        "user": "Vesper said Pinky likes loud NARF greetings.",
        "response": "I noted that Pinky has a distinctive greeting style.",
    }

    enriched = enrich_memory_evidence_metadata("Vesper mentioned Pinky.", metadata)

    assert enriched["evidence_kind"] == DIRECT_SHARED
    assert "Pinky" in enriched["mentioned_entities"]
    assert classify_evidence_for_subject(enriched, "Vesper") == DIRECT_SHARED
    assert classify_evidence_for_subject(enriched, "Pinky") == THIRD_PARTY


def test_direct_other_session_can_still_be_direct_for_queried_person():
    metadata = {
        "speaker_name": "Pinky",
        "instance_id": "vesper",
        "qdrant_collection": "mocop_private_vesper",
        "user": "Pinky asked whether Alex remembered Vesper.",
        "response": "Hi Pinky. Yes, I remember Vesper.",
    }

    enriched = enrich_memory_evidence_metadata("Pinky directly spoke with Alex.", metadata)

    assert enriched["instance_owner"] == "Vesper"
    assert enriched["current_interlocutor"] == "Pinky"
    assert classify_evidence_for_subject(enriched, "Pinky", active_interlocutor="Vesper") == DIRECT_SHARED
    assert classify_evidence_for_subject(enriched, "Vesper", active_interlocutor="Vesper") != DIRECT_SHARED


def test_group_episode_tracks_multiple_interlocutors():
    metadata = {
        "current_interlocutors": ["Vesper", "Pinky"],
        "speaker": "Pinky",
        "participant_set": ["Vesper", "Pinky"],
        "user": "Pinky and Vesper discussed Alex together.",
        "response": "I can follow both of you.",
    }

    enriched = enrich_memory_evidence_metadata("A group chat happened.", metadata)

    assert enriched["evidence_kind"] == GROUP_SHARED
    assert enriched["current_interlocutor"] == ""
    assert enriched["current_interlocutors"] == ["Vesper", "Pinky"]
    assert enriched["participant_set"] == ["Vesper", "Pinky"]


def test_unknown_speaker_stays_low_confidence_instead_of_guessing():
    enriched = enrich_memory_evidence_metadata(
        "A memory existed but had weak legacy metadata.",
        {"qdrant_collection": "mocop_private_vesper"},
    )

    assert enriched["instance_owner"] == "Vesper"
    assert enriched["speaker"] == ""
    assert enriched["participant_set"] == []
    assert enriched["evidence_kind"] == UNCERTAIN
    assert enriched["evidence_confidence"] == 0.35
