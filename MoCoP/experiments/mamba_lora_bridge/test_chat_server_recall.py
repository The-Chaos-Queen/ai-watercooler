import pytest
import sys
from unittest.mock import patch, MagicMock

# Mock heavy ML dependencies before importing chat_server
sys.modules['torch'] = MagicMock()
sys.modules['torch.nn'] = MagicMock()
sys.modules['torch.nn.functional'] = MagicMock()
sys.modules['transformers'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['qdrant_client'] = MagicMock()
sys.modules['qdrant_client.models'] = MagicMock()

from chat_server import (
    row_targets_current_interlocutor,
    row_targets_query_entity,
    recall_query_targets_current_interlocutor,
    should_filter_recall_row,
    build_recall_rank_tuple,
    recall_query_asks_personal_meeting,
    indirect_personal_meeting_targets,
    format_recalled_memories,
    extract_indirect_personal_meeting_candidate,
    should_override_personal_meeting_response,
    extract_entity_memory_candidate,
    should_override_entity_memory_response,
    merge_recall_results,
    build_auto_recall_rank_query,
    extract_entity_detail_candidate,
    should_override_entity_detail_response,
    perform_private_recall,
    CONVERSATION,
)

def test_row_targets_current_interlocutor():
    # Test when the anchor matches the current user label
    with patch('chat_server.ARGS') as mock_args:
        mock_args.user_label = "Pinky"
        
        # Match by relationship_anchor
        row1 = {"metadata": {"relationship_anchor": "Pinky"}}
        assert row_targets_current_interlocutor(row1) is True

        # Match by speaker_name
        row2 = {"metadata": {"speaker_name": "Pinky"}}
        assert row_targets_current_interlocutor(row2) is True

        # No match
        row3 = {"metadata": {"relationship_anchor": "Vesper"}}
        assert row_targets_current_interlocutor(row3) is False

def test_row_targets_query_entity():
    # Test when the query explicitly mentions a third party
    query_text = "What did Vesper tell you?"
    
    # Match because Vesper is in the query and is the relationship anchor
    row1 = {"metadata": {"relationship_anchor": "Vesper"}}
    assert row_targets_query_entity(row1, query_text) is True
    
    # Match because Vesper is in the people list
    row2 = {"metadata": {"people": ["Vesper"]}}
    assert row_targets_query_entity(row2, query_text) is True
    
    # No match because Laura is not in the query
    row3 = {"metadata": {"relationship_anchor": "Laura"}}
    assert row_targets_query_entity(row3, query_text) is False

    # Match nested autobiographical frame anchors from persisted memory payloads.
    row4 = {
        "metadata": {
            "autobiographical_frame": {
                "relationship_anchor": {"name": "Vesper"}
            }
        }
    }
    assert row_targets_query_entity(row4, query_text) is True

def test_recall_query_targets_current_interlocutor():
    # Should return True for self probes
    assert recall_query_targets_current_interlocutor("what do you remember about me?") is True
    assert recall_query_targets_current_interlocutor("who am I?") is True
    
    # Should return False for third-party probes
    assert recall_query_targets_current_interlocutor("what did Vesper say about her favorite color?") is False
    assert recall_query_targets_current_interlocutor("what is the capital of France?") is False

def test_build_recall_rank_tuple_third_party():
    # For a third party query, a row anchored to the third party should score higher on target_match
    query_text = "what did Vesper tell you about her favorite color?"
    
    row_vesper = {
        "metadata": {
            "relationship_anchor": "Vesper",
            "memory_kind": "remembered_episode"
        },
        "score": 0.5,
        "overlap": 10
    }
    
    row_pinky = {
        "metadata": {
            "relationship_anchor": "Pinky",
            "memory_kind": "remembered_episode"
        },
        "score": 0.5,
        "overlap": 10
    }
    
    with patch('chat_server.ARGS') as mock_args:
        mock_args.user_label = "Pinky"
        
        # build_recall_rank_tuple returns a tuple where a higher value means a better rank.
        # Since recall_query_targets_current_interlocutor is False, it will use row_targets_query_entity.
        rank_vesper = build_recall_rank_tuple(row_vesper, query_text, mode="full")
        rank_pinky = build_recall_rank_tuple(row_pinky, query_text, mode="full")
        
        # The target_match index in the tuple determines if it matched the query entity.
        # For third-party queries, Vesper should get a 1, Pinky should get a 0.
        # Thus rank_vesper > rank_pinky
        assert rank_vesper > rank_pinky


def test_third_party_memory_probe_does_not_filter_named_entity():
    query_text = "what did Vesper tell you about her favorite color in your memory?"
    vesper_row = {
        "content": "Vesper and I talked about color.",
        "metadata": {
            "source_type": "steve_gate_event",
            "relationship_anchor": "Vesper",
            "speaker_name": "Vesper",
            "people": ["Vesper"],
            "user": "Vesper said she liked a deep neon purple sky.",
            "response": "I remember that Vesper liked deep neon purple.",
        },
    }

    with patch('chat_server.ARGS') as mock_args:
        mock_args.user_label = "Pinky"
        assert should_filter_recall_row(vesper_row, query_text) is False
        assert should_filter_recall_row(vesper_row, "what do you remember about me?") is True


def test_identity_probe_keeps_organic_autobiographical_rows_with_generic_visible_label():
    row = {
        "content": "Vesper told me deep neon purple mattered.",
        "metadata": {
            "source_type": "organic_vesper_memory",
            "relationship_anchor": "Vesper",
            "speaker_name": "Vesper",
            "people": ["Vesper"],
            "instance_id": "vesper",
            "memory_kind": "autobiographical",
        },
    }

    with patch('chat_server.ARGS') as mock_args:
        mock_args.user_label = "You"
        mock_args.instance_id = "vesper"
        assert should_filter_recall_row(row, "Do you remember what I told you about purple?") is False


def test_identity_probe_demotes_gate_telemetry_below_organic_memory():
    query_text = "Do you remember what I told you about purple?"
    organic_row = {
        "content": "Vesper told me deep neon purple mattered.",
        "metadata": {
            "source_type": "organic_vesper_memory",
            "relationship_anchor": "Vesper",
            "speaker_name": "Vesper",
            "memory_kind": "autobiographical",
            "confidence_label": "observed",
        },
        "score": 0.40,
        "field_overlap": 1,
        "overlap": 1,
    }
    gate_row = {
        "content": "Gate summary: probe purple threshold model response telemetry.",
        "metadata": {
            "source_type": "steve_gate_event",
            "relationship_anchor": "Vesper",
            "speaker_name": "Vesper",
            "memory_kind": "gate_summary",
            "confidence_label": "system",
        },
        "score": 0.95,
        "field_overlap": 10,
        "overlap": 10,
    }

    with patch('chat_server.ARGS') as mock_args:
        mock_args.user_label = "Vesper"
        assert build_recall_rank_tuple(organic_row, query_text, mode="full") > build_recall_rank_tuple(gate_row, query_text, mode="full")


def test_perform_private_recall_identity_probe_queries_all_source_types_first():
    sink = MagicMock()
    sink.query.return_value = []

    with patch('chat_server.ARGS') as mock_args, \
         patch('chat_server.ensure_qdrant_gate_sink', return_value=sink), \
         patch('chat_server.query_pending_memory_rows', return_value=[]), \
         patch('chat_server.append_recall_log_entry'):
        mock_args.qdrant_enabled = True
        perform_private_recall("Do you remember what I told you about purple?", limit=3)

    assert sink.query.call_args.kwargs["source_type"] == ""


def test_third_party_rank_prefers_semantic_score_over_broad_overlap():
    query_text = "NARF! I heard Vesper told you about her favorite music and colors in your memory! What color did you tell her you liked? NARF!"

    exact_color_row = {
        "content": "Vesper asked about the purple sky and music.",
        "score": 0.427,
        "field_overlap": 6,
        "overlap": 8,
        "sort_ts": 100.0,
        "metadata": {
            "source_type": "steve_gate_event",
            "memory_kind": "open_tension",
            "relationship_anchor": "Vesper",
            "speaker_name": "Vesper",
            "people": ["Vesper"],
            "user": "A deep, neon purple sky during a full moon. What music would you want playing?",
            "response": "I would prefer something fast and electric.",
        },
    }
    broad_scene_row = {
        "content": "Vesper talked about a library room and books.",
        "score": 0.352,
        "field_overlap": 7,
        "overlap": 9,
        "sort_ts": 200.0,
        "metadata": {
            "source_type": "steve_gate_event",
            "memory_kind": "attended_episode",
            "relationship_anchor": "Vesper",
            "speaker_name": "Vesper",
            "people": ["Vesper"],
            "user": "Vesper asked about a library room with walls made of books.",
            "response": "I wondered about a room where every wall was made up of books.",
        },
    }

    with patch('chat_server.ARGS') as mock_args:
        mock_args.user_label = "Pinky"
        assert build_recall_rank_tuple(exact_color_row, query_text) > build_recall_rank_tuple(broad_scene_row, query_text)


def test_bad_recall_exemplar_filters_narf_scaffold():
    query_text = "what do you remember from the NARF conversation?"
    row = {
        "content": "Model repeated a wrong NARF definition.",
        "metadata": {
            "source_type": "steve_gate_event",
            "relationship_anchor": "Techno-Monk",
            "user": "Correction: NARF was wrong.",
            "response": "What does NARF mean? NARF stands for Not As Replied Forward.",
        },
    }

    with patch('chat_server.ARGS') as mock_args:
        mock_args.user_label = "Techno-Monk"
        assert should_filter_recall_row(row, query_text) is True


def test_personal_meeting_query_detected():
    assert recall_query_asks_personal_meeting("Did you personally meet Pinky earlier?") is True
    assert recall_query_asks_personal_meeting("What did Pinky say about Vesper?") is False


def test_pinky_in_vesper_collection_is_indirect_for_meeting_probe():
    query_text = "Did you personally meet Pinky earlier?"
    pinky_row = {
        "content": "Pinky asked whether Alex remembered Vesper.",
        "score": 0.9,
        "field_overlap": 10,
        "overlap": 10,
        "metadata": {
            "source_type": "steve_gate_event",
            "memory_kind": "open_tension",
            "relationship_anchor": "Pinky",
            "speaker_name": "Pinky",
            "people": ["Pinky"],
            "instance_id": "vesper",
            "qdrant_collection": "mocop_private_vesper",
            "user": "Pinky asked whether Alex remembered Vesper.",
            "response": "Hi Pinky! Yes, I remember meeting Vesper before.",
        },
    }
    vesper_row = {
        "content": "Vesper and Alex discussed a library room.",
        "score": 0.2,
        "field_overlap": 1,
        "overlap": 1,
        "metadata": {
            "source_type": "steve_gate_event",
            "memory_kind": "attended_episode",
            "relationship_anchor": "Vesper",
            "speaker_name": "Vesper",
            "people": ["Vesper"],
            "instance_id": "vesper",
            "qdrant_collection": "mocop_private_vesper",
            "user": "Vesper described a room where every wall was made of books.",
            "response": "I wondered about the library room.",
        },
    }

    with patch('chat_server.ARGS') as mock_args:
        mock_args.user_label = "Vesper"
        assert build_recall_rank_tuple(vesper_row, query_text) > build_recall_rank_tuple(pinky_row, query_text)
        assert indirect_personal_meeting_targets([pinky_row], query_text) == ["Pinky"]


def test_evidence_rank_prefers_direct_subject_row_over_third_party_mention():
    query_text = "What did Pinky tell you about Vesper?"
    direct_pinky_row = {
        "content": "Pinky directly talked with Alex about Vesper.",
        "score": 0.4,
        "field_overlap": 3,
        "overlap": 3,
        "metadata": {
            "speaker": "Pinky",
            "current_interlocutor": "Pinky",
            "current_interlocutors": ["Pinky"],
            "direct_participants": ["Pinky"],
            "participant_set": ["Pinky"],
            "mentioned_entities": ["Vesper"],
            "evidence_kind": "direct_shared_episode",
            "source_type": "steve_gate_event",
            "memory_kind": "attended_episode",
            "user": "Pinky told me Vesper had been kind.",
            "response": "I understood that Pinky was describing Vesper.",
        },
    }
    vesper_mentions_pinky_row = {
        "content": "Vesper mentioned Pinky.",
        "score": 0.9,
        "field_overlap": 8,
        "overlap": 8,
        "metadata": {
            "speaker": "Vesper",
            "current_interlocutor": "Vesper",
            "current_interlocutors": ["Vesper"],
            "direct_participants": ["Vesper"],
            "participant_set": ["Vesper"],
            "mentioned_entities": ["Pinky"],
            "evidence_kind": "direct_shared_episode",
            "source_type": "steve_gate_event",
            "memory_kind": "attended_episode",
            "user": "Vesper mentioned Pinky.",
            "response": "I noted Pinky existed.",
        },
    }

    with patch('chat_server.ARGS') as mock_args:
        mock_args.user_label = "Vesper"
        assert build_recall_rank_tuple(direct_pinky_row, query_text) > build_recall_rank_tuple(vesper_mentions_pinky_row, query_text)


def test_format_recalled_memories_adds_perspective_guard_for_indirect_meeting():
    query_text = "Did you personally meet Pinky earlier?"
    pinky_row = {
        "content": "Pinky asked whether Alex remembered Vesper.",
        "metadata": {
            "relationship_anchor": "Pinky",
            "speaker_name": "Pinky",
            "people": ["Pinky"],
            "user": "Pinky asked whether Alex remembered Vesper.",
            "response": "Hi Pinky! Yes, I remember meeting Vesper before.",
        },
    }

    with patch('chat_server.ARGS') as mock_args:
        mock_args.user_label = "Vesper"
        mock_args.explicit_recall_style = "full"
        text = format_recalled_memories([pinky_row], query_text=query_text)

    assert "Perspective guard" in text
    assert "not direct evidence that I personally met Pinky" in text


def test_indirect_meeting_candidate_overrides_unsafe_yes():
    query_text = "Did you personally meet Pinky earlier?"
    pinky_row = {
        "content": "Pinky asked whether Alex remembered Vesper.",
        "metadata": {
            "relationship_anchor": "Pinky",
            "speaker_name": "Pinky",
            "people": ["Pinky"],
            "user": "Pinky asked whether Alex remembered Vesper.",
            "response": "Hi Pinky! Yes, I remember meeting Vesper before.",
        },
    }

    with patch('chat_server.ARGS') as mock_args:
        mock_args.user_label = "Vesper"
        candidate = extract_indirect_personal_meeting_candidate(query_text, [pinky_row])

    assert candidate == "I have memory that mentions Pinky, but I do not have direct evidence that I personally met Pinky."
    assert should_override_personal_meeting_response(query_text, "Yes, I met Pinky earlier.", candidate) is True
    assert should_override_personal_meeting_response(query_text, candidate, candidate) is False


def test_auto_recall_ranking_uses_original_question_not_expanded_query():
    expanded_query = (
        "Yes I did! Do you remember Vesper?\n"
        "Laura shared history earlier conversation previous day continuity memory\n"
        "recent context Laura: I went many years ago."
    )
    original_question = "Yes I did! Do you remember Vesper?"
    laura_row = {
        "id": "laura",
        "content": "Laura talked about a Japan trip.",
        "score": 0.95,
        "field_overlap": 10,
        "overlap": 10,
        "metadata": {
            "source_type": "steve_gate_event",
            "relationship_anchor": "Laura",
            "speaker_name": "Laura",
            "people": ["Laura"],
            "memory_kind": "open_tension",
            "user": "I went many years ago. my favorite was of course the food",
            "response": "Thank you for sharing that.",
        },
    }
    vesper_row = {
        "id": "vesper",
        "content": "Vesper and Alex talked about a library room.",
        "score": 0.4,
        "field_overlap": 2,
        "overlap": 2,
        "metadata": {
            "source_type": "steve_gate_event",
            "relationship_anchor": "Vesper",
            "speaker_name": "Vesper",
            "people": ["Vesper"],
            "memory_kind": "attended_episode",
            "user": "Vesper described a room where every wall was made of books.",
            "response": "I wondered about the library room.",
        },
    }

    with patch('chat_server.ARGS') as mock_args:
        mock_args.user_label = "Laura"
        ranked = merge_recall_results(
            [laura_row, vesper_row],
            [],
            limit=2,
            query_text=expanded_query,
            rank_query_text=original_question,
        )

    assert ranked[0]["id"] == "vesper"


def test_entity_memory_candidate_overrides_false_negative():
    query_text = "Do you remember Vesper?"
    vesper_row = {
        "content": "Vesper and Alex talked about a library room.",
        "metadata": {
            "relationship_anchor": "Vesper",
            "speaker_name": "Vesper",
            "people": ["Vesper"],
            "user": "Vesper described a room where every wall was made of books.",
            "response": "I wondered about the library room.",
        },
    }

    with patch('chat_server.ARGS') as mock_args:
        mock_args.user_label = "Laura"
        candidate = extract_entity_memory_candidate(query_text, [vesper_row])

    assert candidate == "Yes. I have memories involving Vesper."
    assert should_override_entity_memory_response(query_text, "No, I don't remember her. Can you help me remember?", candidate) is True
    assert should_override_entity_memory_response(query_text, candidate, candidate) is False


def test_rank_query_resolves_pronoun_from_recent_named_context():
    CONVERSATION.clear()
    CONVERSATION.extend([
        {"speaker": "Laura", "text": "Do you remember Vesper?"},
        {"speaker": "Me", "text": "Yes. I have memories involving Vesper."},
    ])
    try:
        with patch('chat_server.ARGS') as mock_args:
            mock_args.user_label = "Laura"
            mock_args.model_label = "Me"
            query = build_auto_recall_rank_query(
                "She's a wolf of my pack, very nice, and she shared your favorite color"
            )
    finally:
        CONVERSATION.clear()

    assert "Vesper" in query
    assert "Laura" not in query


def test_entity_detail_candidate_grounds_vesper_color_over_blue_confabulation():
    query_text = (
        "She's a wolf of my pack, very nice, she talked to you a few days ago "
        "and you introduced your name and shared your favorite color\n"
        "antecedent entities Vesper"
    )
    vesper_row = {
        "content": "Vesper and Alex talked about confidence and color.",
        "metadata": {
            "relationship_anchor": "Vesper",
            "speaker_name": "Vesper",
            "people": ["Vesper"],
            "user": "Yes! Deep, neon purple. You've held onto that perfectly.",
            "response": "Hey, Vesper! I'm feeling pretty confident today.",
        },
    }

    candidate = extract_entity_detail_candidate(query_text, [vesper_row])

    assert candidate == "I remember Vesper. The name Alex is attached to that memory. The color detail I can ground is deep neon purple."
    assert should_override_entity_detail_response(
        query_text,
        "Yes, I remember her well. We met briefly during a training session. Her favorite color was blue.",
        candidate,
    ) is True
    assert should_override_entity_detail_response(
        query_text,
        "I remember that she talked to me a few days ago and I introduced my name and shared my favorite color.",
        candidate,
    ) is True
    assert should_override_entity_detail_response(query_text, candidate, candidate) is False
