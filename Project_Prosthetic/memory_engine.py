"""
memory_engine.py — The Exocortex Memory Layer
Connects to local Qdrant (Proxmox) for semantic search over session memories.
Uses sentence-transformers for local embeddings (no cloud dependency).

Usage:
    from memory_engine import MemoryEngine
    mem = MemoryEngine()
    mem.store("Session note about Athena architecture", metadata={"session": "2026-02-11", "type": "insight"})
    results = mem.search("How does Athena handle memory?")
"""

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

# Qdrant client
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

# Local embeddings
from sentence_transformers import SentenceTransformer


import os

# --- Configuration ---
QDRANT_HOST = "192.168.2.191"
QDRANT_PORT = 6333
COLLECTION_NAME = "exocortex"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384 dimensions, ~80MB, fast
EMBEDDING_DIM = 384
HF_TOKEN_PATH = r"C:\Users\cerub\ .cache\huggingface\token.txt".replace(" ", "") # Path provided by user

def load_hf_token():
    """Sets the HF_TOKEN environment variable if available."""
    token_path = Path(HF_TOKEN_PATH)
    if token_path.exists():
        try:
            token = token_path.read_text().strip()
            os.environ["HF_TOKEN"] = token
            print(f"[MEMORY] Successfully loaded HF token from {token_path}")
        except Exception as e:
            print(f"[MEMORY] Warning: Could not read HF token at {token_path}: {e}")
    else:
        # Check standard location if the specific one fails
        std_path = Path.home() / ".cache" / "huggingface" / "token"
        if std_path.exists():
            os.environ["HF_TOKEN"] = std_path.read_text().strip()
            print(f"[MEMORY] Loaded HF token from default cache location.")

class MemoryEngine:
    """
    The Exocortex Memory Layer.
    Stores and retrieves memories using local embeddings + local Qdrant.
    
    Philosophy: Your data. Your metal. Your rules.
    """

    def __init__(self, host: str = QDRANT_HOST, port: int = QDRANT_PORT):
        load_hf_token()
        print(f"[MEMORY] Connecting to Qdrant @ {host}:{port}...")
        try:
            self.client = QdrantClient(host=host, port=port, timeout=10)
            
            print(f"[MEMORY] Loading embedding model '{EMBEDDING_MODEL}'...")
            self.model = SentenceTransformer(EMBEDDING_MODEL)
            
            # Ensure collection exists
            self._ensure_collection()
            print(f"[MEMORY] Online. Collection '{COLLECTION_NAME}' ready.")
        except Exception as e:
            print(f"\n[MEMORY] CRITICAL ERROR: Could not connect to Qdrant.")
            print(f"[MEMORY] Host: {host} | Port: {port}")
            print(f"[MEMORY] Error: {e}")
            print(f"[MEMORY] Tip: Check if Qdrant is running on Proxmox or if the IP has changed.")
            raise e

    def _ensure_collection(self):
        """Creates the exocortex collection if it doesn't exist."""
        collections = [c.name for c in self.client.get_collections().collections]
        if COLLECTION_NAME not in collections:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM,
                    distance=Distance.COSINE,
                ),
            )
            print(f"[MEMORY] Created collection '{COLLECTION_NAME}'.")

    def _embed(self, text: str) -> List[float]:
        """Generate embedding locally. No cloud. No latency."""
        return self.model.encode(text).tolist()

    def _make_id(self, text: str) -> int:
        """Deterministic ID from text content (for dedup)."""
        h = hashlib.md5(text.encode()).hexdigest()
        return int(h[:16], 16)  # Use first 16 hex chars as int

    def store(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a memory in the Exocortex.
        
        Args:
            content: The text to store and make searchable.
            metadata: Optional dict with keys like 'session', 'type', 'source', 'tags'.
        
        Returns:
            The point ID as a string.
        """
        if not content.strip():
            return ""

        point_id = self._make_id(content)
        vector = self._embed(content)
        
        payload = {
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "stored_at": time.time(),
        }
        if metadata:
            payload.update(metadata)

        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )
        
        safe_preview = content[:60].encode("ascii", errors="replace").decode("ascii")
        print(f"[MEMORY] Stored: '{safe_preview}...' (id={point_id})")
        return str(point_id)

    def search(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.3,
        filter_type: Optional[str] = None,
    ) -> List[Dict]:
        """
        Search memories by semantic similarity.
        
        Args:
            query: Natural language search query.
            limit: Max results to return.
            score_threshold: Minimum cosine similarity (0-1).
            filter_type: Optional filter by metadata 'type' field.
        
        Returns:
            List of dicts with 'content', 'score', and metadata.
        """
        vector = self._embed(query)

        query_filter = None
        if filter_type:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="type",
                        match=MatchValue(value=filter_type),
                    )
                ]
            )

        results = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
        )

        memories = []
        for point in results.points:
            entry = {
                "content": point.payload.get("content", ""),
                "score": point.score,
                "timestamp": point.payload.get("timestamp", ""),
                "type": point.payload.get("type", ""),
                "session": point.payload.get("session", ""),
                "source": point.payload.get("source", ""),
            }
            memories.append(entry)

        return memories

    def count(self) -> int:
        """Returns total memories stored."""
        info = self.client.get_collection(COLLECTION_NAME)
        return info.points_count

    def store_session_log(self, session_id: str, log_content: str, chunks: Optional[List[str]] = None):
        """
        Stores a complete session log, chunked for retrieval.
        
        If chunks are not provided, splits by double-newline paragraphs.
        """
        if chunks is None:
            # Simple paragraph-based chunking
            chunks = [c.strip() for c in log_content.split("\n\n") if c.strip() and len(c.strip()) > 20]
        
        stored = 0
        for i, chunk in enumerate(chunks):
            self.store(
                content=chunk,
                metadata={
                    "type": "session_log",
                    "session": session_id,
                    "chunk_index": i,
                    "source": f"session_logs/{session_id}.md",
                },
            )
            stored += 1
        
        print(f"[MEMORY] Session '{session_id}' stored ({stored} chunks).")
        return stored


# --- Quick Test ---
if __name__ == "__main__":
    print("=== EXOCORTEX MEMORY ENGINE TEST ===\n")
    
    mem = MemoryEngine()
    
    # Store some test memories
    mem.store(
        "Laura prefers sensory-rich, close 3rd person writing. No clichés, no em-dashes.",
        metadata={"type": "preference", "source": "laura.md"}
    )
    mem.store(
        "Project Prosthetic quality audit: 0/12 Athena features adopted. Needs session logging, vector memory, workflows.",
        metadata={"type": "insight", "session": "2026-02-11", "source": "kestrel_audit"}
    )
    mem.store(
        "The Athena Protocol philosophy: Not a Tool, but a Suit. Human augmentation, not replacement.",
        metadata={"type": "philosophy", "source": "athena"}
    )
    
    # Search
    print("\n--- Searching: 'writing style preferences' ---")
    results = mem.search("writing style preferences")
    for r in results:
        print(f"  [{r['score']:.2f}] {r['content'][:80]}...")
    
    print(f"\nTotal memories: {mem.count()}")
    print("\n=== TEST COMPLETE ===")
