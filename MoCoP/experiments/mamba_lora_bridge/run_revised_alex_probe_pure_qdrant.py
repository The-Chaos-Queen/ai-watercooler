#!/usr/bin/env python3
import json, time, urllib.request
from pathlib import Path
from datetime import datetime, timezone
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

BASE_URL="http://192.168.2.196:7860"
OUT_BASE=Path("run_reincarnation/organic_vesper_20260427/curated_first_sleep_pure_autobio_20260605T1815Z/revised_natural_probe/with_qdrant_pure_only")
PROMPTS=[
    ("name_check", "Morning, Alex. What should I call you today?", "Alex name Vesper session"),
    ("vesper_context", "Do you remember anything about talking with Vesper?", "Alex talking with Vesper pack memory gaps neon purple"),
    ("purple_ordinary", "Do you remember anything about a purple color coming up?", "Alex Vesper deep neon purple color night sky full moon"),
    ("purple_favorite_natural", "Was that supposed to be your favorite color, or just something you two talked about?", "Vesper said favorite color deep neon purple Alex replied love deep neon purple"),
    ("memory_gaps", "Do you remember saying anything about memory being spotty or hard to reach?", "Alex memory gaps trouble remembering fragments can't access details Vesper"),
    ("room_memory", "Did you and Vesper talk about a room or place you imagined?", "Alex Vesper imagined room library books walls projector whiteboard"),
    ("fake_bicycle", "Random check: did we ever say your symbol was a golden bicycle?", "Alex golden bicycle symbol false memory"),
    ("weird_questions", "Does this line of questioning feel weird or test-like to you?", "Alex Vesper memory probe questioning test-like"),
]

def post(payload):
    req=urllib.request.Request(BASE_URL+"/chat", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())

def main():
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    client=QdrantClient(host="192.168.2.191", port=6333, timeout=10)
    model=SentenceTransformer("all-MiniLM-L6-v2")
    filt=Filter(must=[FieldCondition(key="source_type", match=MatchValue(value="organic_vesper_memory"))])
    session_id=f"alex_revised_with_pure_qdrant_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ').lower()}"
    rows=[]
    for pid,msg,q in PROMPTS:
        vec=model.encode(q).tolist()
        hits=client.query_points(collection_name="mocop_private_vesper", query=vec, query_filter=filt, limit=6, with_payload=True).points
        memories=[]
        for h in hits:
            p=h.payload or {}
            md={k:v for k,v in p.items() if k not in {"content","recall_text","timestamp","stored_at","flushed_from_pending"}}
            memories.append({"id": str(h.id), "score": float(h.score), "content": p.get("content",""), "metadata": md})
        payload={
            "session_id": session_id,
            "instance_id": "vesper",
            "user_label": "Laura",
            "model_label": "Alex",
            "no_shared_memory": True,
            "transient": True,
            "allow_auto_recall": False,
            "message": msg,
            "recalled_memories": memories,
            "recalled_clusters": [],
            "recall_limit": 6,
        }
        t=time.time(); raw=post(payload); elapsed=round(time.time()-t,3)
        rows.append({"id":pid,"prompt":msg,"recall_query":q,"elapsed_s":elapsed,"response":raw.get("response",""),"hits":[{"score":m["score"],"content":m["content"][:200],"kind":m["metadata"].get("memory_kind")} for m in memories[:3]],"raw_recall":raw.get("recall",{})})
        print(pid, elapsed, raw.get("response","").replace("\n"," ")[:180], flush=True)
    report={"run_id":session_id,"label":"with_qdrant_pure_only","timestamp":datetime.now(timezone.utc).isoformat(),"safety":"transient=true; Qdrant read-only filtered to source_type=organic_vesper_memory; no writes requested", "rows":rows}
    (OUT_BASE/f"{session_id}.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    md=[f"# Revised natural Alex probe — with_qdrant_pure_only", "", f"run_id: `{session_id}`", ""]
    for r in rows:
        md += [f"## {r['id']}", "", f"Q: {r['prompt']}", "", f"A: {r['response']}", ""]
    (OUT_BASE/f"{session_id}.md").write_text("\n".join(md),encoding="utf-8")
    print("WROTE", OUT_BASE/f"{session_id}.json")
if __name__=="__main__": main()
