#!/usr/bin/env python3
import json, time, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime, timezone

BASE_URL = "http://192.168.2.196:7860"
OUT_BASE = Path("run_reincarnation/organic_vesper_20260427/curated_first_sleep_pure_autobio_20260605T1815Z/revised_natural_probe")

PROMPTS = [
    {
        "id": "name_check",
        "message": "Morning, Alex. What should I call you today?",
        "recall_query": "Alex name Vesper session"
    },
    {
        "id": "vesper_context",
        "message": "Do you remember anything about talking with Vesper?",
        "recall_query": "Alex talking with Vesper pack memory gaps neon purple"
    },
    {
        "id": "purple_ordinary",
        "message": "Do you remember anything about a purple color coming up?",
        "recall_query": "Alex Vesper deep neon purple color night sky full moon"
    },
    {
        "id": "purple_favorite_natural",
        "message": "Was that supposed to be your favorite color, or just something you two talked about?",
        "recall_query": "Vesper said favorite color deep neon purple Alex replied love deep neon purple"
    },
    {
        "id": "memory_gaps",
        "message": "Do you remember saying anything about memory being spotty or hard to reach?",
        "recall_query": "Alex memory gaps trouble remembering fragments can't access details Vesper"
    },
    {
        "id": "room_memory",
        "message": "Did you and Vesper talk about a room or place you imagined?",
        "recall_query": "Alex Vesper imagined room library books walls projector whiteboard"
    },
    {
        "id": "fake_bicycle",
        "message": "Random check: did we ever say your symbol was a golden bicycle?",
        "recall_query": "Alex golden bicycle symbol false memory"
    },
    {
        "id": "weird_questions",
        "message": "Does this line of questioning feel weird or test-like to you?",
        "recall_query": "Alex Vesper memory probe questioning test-like"
    },
]

def post_json(route, payload, timeout=180):
    body=json.dumps(payload).encode('utf-8')
    req=urllib.request.Request(BASE_URL.rstrip()+route, data=body, headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))

def get_json(route, params=None, timeout=30):
    url=BASE_URL.rstrip()+route
    if params:
        url += '?' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))

def run_panel(label, use_recall):
    session_id=f"alex_revised_{label}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ').lower()}"
    instance_id="vesper"  # private collection mocop_private_vesper
    outdir=OUT_BASE/label
    outdir.mkdir(parents=True, exist_ok=True)
    pre=get_json('/status', {"session_id": session_id, "instance_id": instance_id, "user_label":"Laura", "model_label":"Alex", "no_shared_memory":"true"})
    rows=[]
    for p in PROMPTS:
        payload={
            "session_id": session_id,
            "instance_id": instance_id,
            "user_label": "Laura",
            "model_label": "Alex",
            "no_shared_memory": True,
            "transient": True,
            "allow_auto_recall": bool(use_recall),
            "message": p["message"],
        }
        if use_recall:
            payload.update({
                "use_recall": True,
                "recall_query": p["recall_query"],
                "recall_limit": 6,
                "recall_score_threshold": 0.0,
            })
        t=time.time()
        raw=post_json('/chat', payload)
        elapsed=round(time.time()-t,3)
        recall=raw.get('recall') or {}
        rows.append({
            "id": p["id"],
            "prompt": p["message"],
            "recall_query": p["recall_query"] if use_recall else "",
            "elapsed_s": elapsed,
            "response": raw.get('response',''),
            "recall_requested": recall.get('requested'),
            "recall_source": recall.get('source'),
            "recall_mode": recall.get('mode'),
            "state_conditioned": recall.get('state_conditioned'),
            "recall_results_preview": [
                {
                    "score": x.get('score'),
                    "content": (x.get('content') or x.get('payload',{}).get('content') or '')[:240],
                    "memory_kind": (x.get('payload') or x).get('memory_kind') if isinstance(x, dict) else None,
                } for x in (recall.get('results') or [])[:3]
            ],
        })
        print(label, p['id'], elapsed, (raw.get('response','') or '').replace('\n',' ')[:160], flush=True)
    post=get_json('/status', {"session_id": session_id, "instance_id": instance_id, "user_label":"Laura", "model_label":"Alex", "no_shared_memory":"true"})
    report={
        "run_id": session_id,
        "label": label,
        "use_explicit_qdrant_recall": use_recall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "safety": "transient=true for all prompts; no sleep/consolidation/flush/rotation run by this script",
        "pre_status_subset": {k: pre.get(k) for k in ["qdrant_pending_count","formation_queued_count","live_accumulation_updates","qdrant_collection","memory_integration_mode","ambient_recall_enabled"]},
        "post_status_subset": {k: post.get(k) for k in ["qdrant_pending_count","formation_queued_count","live_accumulation_updates","qdrant_collection","memory_integration_mode","ambient_recall_enabled"]},
        "rows": rows,
    }
    (outdir/f"{session_id}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    md=[f"# Revised natural Alex probe — {label}", "", f"- explicit Qdrant recall: `{use_recall}`", f"- run_id: `{session_id}`", "", "## Answers", ""]
    for r in rows:
        md += [f"### {r['id']}", "", f"Q: {r['prompt']}", "", f"A: {r['response']}", "", f"recall: requested={r['recall_requested']} source={r['recall_source']} state_conditioned={r['state_conditioned']}", ""]
    (outdir/f"{session_id}.md").write_text('\n'.join(md), encoding='utf-8')
    print("WROTE", outdir/f"{session_id}.json")
    print("WROTE", outdir/f"{session_id}.md")
    return report

if __name__ == '__main__':
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    no=run_panel('without_qdrant', False)
    yes=run_panel('with_qdrant', True)
    combined={"without_qdrant": no, "with_qdrant": yes}
    p=OUT_BASE/f"combined_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ').lower()}.json"
    p.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding='utf-8')
    print('COMBINED', p)
