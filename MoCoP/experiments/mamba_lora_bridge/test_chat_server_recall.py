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
