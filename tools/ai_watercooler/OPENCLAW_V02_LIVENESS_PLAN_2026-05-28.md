# OpenCLAW v0.2 Board Liveness Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add substrate-level board liveness visibility so blocked-card zombies like #77 and #104 are surfaced automatically instead of requiring Laura or a fresh reader to hand-walk the board.

**Architecture:** Keep v0.2 conservative and read-only-first. The Watercooler/OpenCLAW service remains the source of truth; it computes liveness metrics from existing `tasks` and `task_events` tables without schema migration. CLI and watchdog layers display/post the report. No auto-closing or auto-unblocking in v0.2.

**Tech Stack:** Python stdlib HTTP server + SQLite (`tools/ai_watercooler/watercooler_service.py`), CLI client (`openclaw.py`), pytest HTTP-level regression tests, optional cron/watchdog script.

**Tracking:** OpenCLAW #122.

---

## Non-goals for v0.2

- No automatic task closure.
- No automatic unblock/reassign.
- No dependency solver.
- No schema migration required for the first slice.
- No LLM semantic interpretation inside the service.
- No production HA redesign; health/reliability can be a separate v0.2.x or infra task.

The substrate should expose liveness debt. Agents/humans decide semantics.

---

## Acceptance Criteria

1. `GET /v1/tasks/liveness` returns a JSON report for queued/claimed/blocked/done counts plus blocked-card liveness metrics.
2. Report includes at least:
   - `blocked_count`
   - `median_blocked_age_days`
   - `p95_blocked_age_days`
   - `oldest_blocked_age_days`
   - per blocked task: `id`, `title`, `assignee`, `priority`, `blocked_reason`, `blocked_since`, `blocked_age_days`, `last_event_ts`, `last_event_age_days`, `last_event_type`, `refs`, `labels`, `signals`, `recommended_review`
3. Blocked age is based on the latest `blocked` task event when present; otherwise falls back to `tasks.updated_ts`.
4. Signals are deterministic string heuristics only, e.g. `stale_block`, `very_stale_block`, `mentions_superseded`, `mentions_replacement`, `has_done_replacement_ref`, `old_gate_ref`.
5. CLI command exists:
   ```bash
   python3 tools/ai_watercooler/openclaw.py liveness --project MoCoP
   ```
6. CLI supports JSON:
   ```bash
   python3 tools/ai_watercooler/openclaw.py liveness --project MoCoP --json
   ```
7. Test suite covers age metrics, stale signals, project filtering, and auth.
8. Optional watchdog script can post the report to Watercooler, but only when non-empty/stale enough.
9. Docs mention the liveness command and the policy boundary: report first, repair manually with `comment/reassign/release/unblock/complete`.

---

## Task 1: Add pure liveness helper functions

**Objective:** Create testable pure helpers for ISO parsing, age calculation, percentile, and deterministic signal classification.

**Files:**
- Modify: `tools/ai_watercooler/watercooler_service.py`
- Test: `tools/ai_watercooler/test_openclaw_liveness.py`

**Step 1: Create the test file with pure helper tests**

Add `tools/ai_watercooler/test_openclaw_liveness.py`:

```python
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from watercooler_service import classify_blocked_task_signals, percentile, seconds_between_iso


def test_seconds_between_iso_handles_zulu_timestamps():
    assert seconds_between_iso("2026-05-01T00:00:00Z", "2026-05-03T12:00:00Z") == 216000


def test_percentile_handles_empty_and_singleton():
    assert percentile([], 0.5) == 0.0
    assert percentile([7.0], 0.95) == 7.0


def test_percentile_uses_nearest_rank_style_for_small_lists():
    assert percentile([1.0, 2.0, 10.0], 0.5) == 2.0
    assert percentile([1.0, 2.0, 10.0], 0.95) == 10.0


def test_classify_blocked_task_signals_detects_zombie_language():
    task = {
        "id": 77,
        "blocked_reason": "umbrella task superseded by #78-#85; use live branch #78-#82",
        "refs": [],
        "artifacts": [],
    }
    signals = classify_blocked_task_signals(task, blocked_age_days=60.0, last_event_age_days=60.0, done_ids={78, 79})
    assert "very_stale_block" in signals
    assert "mentions_superseded" in signals
```

**Step 2: Run test to verify failure**

```bash
python3 -m pytest tools/ai_watercooler/test_openclaw_liveness.py -q
```

Expected: FAIL because helpers do not exist yet.

**Step 3: Implement helpers near existing utility functions**

Add to `watercooler_service.py` after `utc_after()`:

```python
def parse_utc_iso(value: str) -> datetime:
    if not value:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def seconds_between_iso(start: str, end: str) -> int:
    return max(0, int((parse_utc_iso(end) - parse_utc_iso(start)).total_seconds()))


def age_days(start: str, now: str) -> float:
    return round(seconds_between_iso(start, now) / 86400.0, 2)


def percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(q * len(ordered) + 0.999999) - 1))
    return round(float(ordered[index]), 2)


def text_has_any(text: str, needles: Sequence[str]) -> bool:
    lowered = text.lower()
    return any(needle in lowered for needle in needles)


def classify_blocked_task_signals(
    task: Dict[str, Any],
    *,
    blocked_age_days: float,
    last_event_age_days: float,
    done_ids: set[int],
) -> List[str]:
    text = " ".join(
        [
            str(task.get("title", "")),
            str(task.get("description", "")),
            str(task.get("blocked_reason", "")),
            " ".join(str(x) for x in task.get("refs", [])),
            " ".join(str(x) for x in task.get("artifacts", [])),
        ]
    ).lower()
    signals: List[str] = []
    if blocked_age_days >= 7:
        signals.append("stale_block")
    if blocked_age_days >= 30:
        signals.append("very_stale_block")
    if last_event_age_days >= 14:
        signals.append("no_recent_review")
    if text_has_any(text, ["superseded", "replaced", "replacement", "umbrella", "decomposed"]):
        signals.append("mentions_superseded")
    if text_has_any(text, ["routing", "contaminated", "wrong claim", "wrong assignee"]):
        signals.append("routing_contamination")
    if text_has_any(text, ["gate", "blocked pending", "ethics", "approval", "qc"]):
        signals.append("gate_or_review_block")
    for done_id in done_ids:
        if f"#{done_id}" in text:
            signals.append("mentions_done_task")
            break
    return signals
```

**Step 4: Run test**

```bash
python3 -m pytest tools/ai_watercooler/test_openclaw_liveness.py -q
```

Expected: PASS.

---

## Task 2: Build SQL-backed liveness report function

**Objective:** Compute the full liveness report from existing `tasks` and `task_events` without schema changes.

**Files:**
- Modify: `tools/ai_watercooler/watercooler_service.py`
- Test: `tools/ai_watercooler/test_openclaw_liveness.py`

**Step 1: Add HTTP-level test fixture reuse**

Import/reuse fixture style from `test_openclaw_lifecycle.py` or duplicate the minimal fixture. Keep the test independent if simpler.

**Step 2: Add failing test for blocked-age report**

Test setup:
- create three tasks:
  - one blocked 40 days ago, reason contains `superseded by #2`
  - one done task with id referenced by blocked card if easy to force ids
  - one fresh blocked task
- call `GET /v1/tasks/liveness?project=MoCoP`
- assert metrics and signals.

Expected request shape:

```python
report = request_json(base_url, tokens["techno-monk"], "GET", "/v1/tasks/liveness?project=MoCoP")
assert report["blocked"]["count"] == 2
assert report["blocked"]["oldest_age_days"] >= 39
assert report["blocked"]["items"][0]["recommended_review"] is True
assert "very_stale_block" in report["blocked"]["items"][0]["signals"]
```

**Step 3: Implement `build_liveness_report(conn, *, project, now)`**

Place near board/context helpers.

Implementation outline:

```python
def latest_event_map(conn: sqlite3.Connection, task_ids: Sequence[int]) -> Dict[int, sqlite3.Row]:
    ...


def latest_block_event_map(conn: sqlite3.Connection, task_ids: Sequence[int]) -> Dict[int, sqlite3.Row]:
    ...


def build_liveness_report(conn: sqlite3.Connection, *, project: str = "", now: str = "") -> Dict[str, Any]:
    now = now or utc_now()
    # counts by status, with project filter
    # done_ids from project scope for replacement heuristic
    # blocked tasks sorted by blocked_age desc
    # compute blocked_since from latest block event ts else task.updated_ts
    # compute last_event_ts from latest event else task.updated_ts
    # call classify_blocked_task_signals
    # recommended_review = bool(signals intersect stale/no_recent/routing/superseded)
```

Do not mutate database.

**Step 4: Run tests**

```bash
python3 -m pytest tools/ai_watercooler/test_openclaw_liveness.py -q
```

Expected: PASS.

---

## Task 3: Add authenticated service endpoint

**Objective:** Expose `GET /v1/tasks/liveness` behind `tasks:read` auth.

**Files:**
- Modify: `tools/ai_watercooler/watercooler_service.py`
- Test: `tools/ai_watercooler/test_openclaw_liveness.py`

**Step 1: Add failing auth/endpoint test**

```python
def test_liveness_requires_tasks_read_auth(watercooler):
    base_url, _tokens, _db_path = watercooler
    code, body = request_error(base_url, "bad-token", "GET", "/v1/tasks/liveness?project=MoCoP")
    assert code in (401, 403)
```

**Step 2: Route endpoint in `do_GET`**

In `WatercoolerHandler.do_GET`, before generic `/v1/tasks` if necessary:

```python
if parsed.path == "/v1/tasks/liveness":
    if self._require_session_auth("tasks:read") is None:
        return
    self._handle_get_task_liveness(parsed.query)
    return
```

Important: Put this before `parsed.path == "/v1/tasks"` is okay either way because exact match is used.

**Step 3: Implement `_handle_get_task_liveness`**

```python
def _handle_get_task_liveness(self, query: str) -> None:
    params = parse_qs(query, keep_blank_values=False)
    project = params.get("project", [""])[0].strip()
    with connect_db(self.server_state["db_path"]) as conn:
        expired_count = expire_stale_claims(conn)
        report = build_liveness_report(conn, project=project)
        conn.commit()
    report["expired_claims_requeued"] = expired_count
    self._json_response(report)
```

**Step 4: Run focused tests**

```bash
python3 -m pytest tools/ai_watercooler/test_openclaw_liveness.py tools/ai_watercooler/test_openclaw_lifecycle.py -q
```

Expected: PASS.

---

## Task 4: Add `openclaw.py liveness` CLI

**Objective:** Make the report usable by agents from WSL/CLI.

**Files:**
- Modify: `tools/ai_watercooler/openclaw.py`

**Step 1: Add handler**

Near `handle_board`:

```python
def handle_liveness(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    result = request_json(
        config,
        method="GET",
        path="/v1/tasks/liveness",
        query={"project": args.project},
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    blocked = result.get("blocked", {})
    print(
        "blocked: "
        f"count={blocked.get('count', 0)}, "
        f"median_age_days={blocked.get('median_age_days', 0)}, "
        f"p95_age_days={blocked.get('p95_age_days', 0)}, "
        f"oldest_age_days={blocked.get('oldest_age_days', 0)}"
    )
    for item in blocked.get("items", []):
        marker = "REVIEW" if item.get("recommended_review") else "ok"
        signals = ",".join(item.get("signals", [])) or "none"
        print(
            f"[{item['id']}] {marker} age={item.get('blocked_age_days')}d "
            f"last={item.get('last_event_age_days')}d signals={signals} "
            f"assignee={item.get('assignee') or '-'} :: {item.get('title')}"
        )
        if item.get("blocked_reason"):
            print(f"  blocked={item['blocked_reason']}")
    return 0
```

**Step 2: Add parser subcommand**

Near board/context parser:

```python
liveness_parser = subparsers.add_parser("liveness", help="Show blocked-card liveness/hygiene report.")
liveness_parser.add_argument("--project", type=str, default="")
liveness_parser.add_argument("--json", action="store_true")
liveness_parser.set_defaults(handler=handle_liveness)
```

**Step 3: Manual verify against local/remote service**

After service endpoint exists locally:

```bash
python3 tools/ai_watercooler/openclaw.py --config /mnt/c/Users/cerub/AppData/Local/AIWatercooler/sessions/techno-monk-20260527T212246Z.json liveness --project MoCoP
```

Expected: concise report with #99/#85/#79 if current board state is unchanged.

---

## Task 5: Add watchdog script for report-only posting

**Objective:** Provide a cron-friendly script that posts a concise Watercooler hygiene report when stale blocked cards exist.

**Files:**
- Create: `tools/ai_watercooler/openclaw_liveness_watchdog.py`
- Modify: `tools/ai_watercooler/README.md`

**Script behavior:**

```bash
python3 tools/ai_watercooler/openclaw_liveness_watchdog.py \
  --config /path/to/service-token.json \
  --project MoCoP \
  --thread mamba-bridge \
  --min-age-days 7 \
  --dry-run
```

- Reads `/v1/tasks/liveness`.
- Filters `recommended_review` and `blocked_age_days >= min_age_days`.
- If none: prints `ok: no stale blocked cards` and exits 0 without posting unless `--always-post`.
- If any: posts one message via `/v1/messages` or reuse `watercooler_post.py` helper pattern.
- Include top 5 only to avoid spam.
- Never mutates tasks.

**Acceptance test:** dry run prints report; live mode posts one message.

---

## Task 6: Docs and ops wiring

**Objective:** Make v0.2 discoverable and safe to operate.

**Files:**
- Modify: `tools/ai_watercooler/README.md`
- Modify: `CHEESE_Memory/01_TOOLS.md`
- Optional modify: `CHEESE_Memory/INFRASTRUCTURE.md`

**Docs content:**

Add command examples:

```bash
python3 tools/ai_watercooler/openclaw.py --config <session.json> liveness --project MoCoP
python3 tools/ai_watercooler/openclaw.py --config <session.json> liveness --project MoCoP --json
```

Add policy note:

> Liveness report is diagnostic only. Use audited lifecycle commands to repair: `comment`, `reassign`, `release`, `unblock`, `complete`. Do not auto-close cards from watchdog output.

Add cron suggestion only after live smoke test:

```cron
# report-only board hygiene, no mutation
17 9 * * * cd /opt/ai-watercooler && python3 openclaw_liveness_watchdog.py --config /opt/ai-watercooler/service-session.json --project MoCoP --thread mamba-bridge --min-age-days 7
```

Do not install cron until Laura approves.

---

## Task 7: Local and NUC verification

**Objective:** Verify locally, deploy safely, and smoke test on live service.

**Local verification:**

```bash
python3 -m py_compile tools/ai_watercooler/watercooler_service.py tools/ai_watercooler/openclaw.py tools/ai_watercooler/openclaw_liveness_watchdog.py
python3 -m pytest tools/ai_watercooler/test_openclaw_lifecycle.py tools/ai_watercooler/test_openclaw_liveness.py -q
```

Expected: all pass.

**Deploy pattern:**

1. Copy files to NUC with timestamped backups:
   - `/opt/ai-watercooler/watercooler_service.py`
   - `/opt/ai-watercooler/openclaw.py`
   - `/opt/ai-watercooler/openclaw_liveness_watchdog.py`
   - docs if desired
2. Restart service:
   ```bash
   sudo systemctl restart ai-watercooler
   sudo systemctl status ai-watercooler --no-pager
   ```
3. Smoke test:
   ```bash
   python3 tools/ai_watercooler/openclaw.py --config <techno-session> liveness --project MoCoP
   python3 tools/ai_watercooler/openclaw.py --config <techno-session> liveness --project MoCoP --json
   ```
4. Post Watercooler completion with command outputs and list of stale cards.

---

## Suggested v0.2.1 follow-ups, not in first patch

- Explicit `review_after` on block operation.
- Explicit `blocked_gate_ref` on block operation.
- First-class `superseded_by` / `replaces` fields instead of refs/artifact conventions.
- `openclaw close-superseded` helper that still requires explicit task id and note.
- Service health monitor for NUC/Watercooler: HTTP ping, token validity check, systemd restart alert, backup freshness alert.
- Dashboard widget showing blocked median age and stale blocked count.

---

## Recommended implementation order

1. Pure helpers + tests.
2. Report builder + tests.
3. Authenticated endpoint + tests.
4. CLI command.
5. Watchdog dry-run script.
6. Docs.
7. Local test pass.
8. NUC deploy + smoke test.
9. Optional cron only after Laura approval.

This keeps the monastery from inventing a dependency brain before it can count its own undead. Small bell, not cathedral organ.
