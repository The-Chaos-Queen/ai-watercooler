"""
chat_server.py - Browser chat for the 1.5B reincarnation probe.

Runs a minimal HTTP server. The bridge is injected once at startup,
then a configured speaker can talk to the model from a browser on the LAN.
"""

import argparse
import hashlib
import json
import math
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

from autobiographical_memory import (
    build_recall_text as build_autobiographical_recall_text,
    enrich_memory_metadata,
    format_memory_anchor_lines,
)
from memory_evidence import (
    DIRECT_OTHER_SESSION,
    DIRECT_SHARED,
    GROUP_SHARED,
    SYSTEM_OBSERVATION,
    THIRD_PARTY,
    classify_evidence_for_subject,
)
from failure_detector import detect_failure
from mamba_runtime_compat import ensure_mamba_ssm_compat
from models import (
    DynamicLoRALinear,
)
from reincarnated_inference import (
    apply_bridge_adjustments as apply_runtime_bridge_adjustments,
    build_context_encoder_and_hypernetwork as build_runtime_context_encoder_and_hypernetwork,
    resolve_bridge_adjustments as resolve_runtime_bridge_adjustments,
)


DEFAULT_BRIDGE = "cheese_reincarnation_bridge_1.5b_codexfix.pt"
DEFAULT_QWEN = "Qwen/Qwen2.5-1.5B"
DEFAULT_MAMBA = "state-spaces/mamba-2.8b-hf"
DEFAULT_EPISODES_FILE = "CHEESE_SHAPING_EPISODES.md"
DEFAULT_TARGET_SPECS = [(12, "v_proj"), (13, "v_proj"), (14, "v_proj"), (15, "v_proj")]
DEFAULT_USER_LABEL = "User"
DEFAULT_MODEL_LABEL = "Me"
PRIVATE_QDRANT_COLLECTION_PREFIX = "mocop_private_"
SHARED_QDRANT_COLLECTION = "exocortex"
DEFAULT_LIVE_TURN_MAMBA_TOKENS = 512

MODEL = None
TOKENIZER = None
CONVERSATION = []
ARGS = None
LATEST_TRANSCRIPT_PATH = None
LATEST_JSONL_PATH = None
DUAL_GATE_LOG_PATH = None
DUAL_GATE_MEMORY_PATH = None
DUAL_GATE_SURPRISE_PATH = None
DUAL_GATE_SLEEP_PATH = None
MEMORY_FORMATION_LOG_PATH = None
RECALL_LOG_PATH = None
SELF_REPORT_LOG_PATH = None
FAILURE_LOG_PATH = None
QDRANT_PENDING_PATH = None
QDRANT_FLUSHED_PATH = None
SERVER = None
CHAT_LOCK = threading.Lock()
STATE_LOCK = threading.Lock()
QDRANT_GATE_LOCK = threading.RLock()
ACTIVATION_RECORDER = None
LAST_CONVERSATION_SNAPSHOT = None
DUAL_GATE_EVENTS = []
QDRANT_GATE_SINK = None
QDRANT_GATE_SINK_ERROR = None
QDRANT_LAST_RETRY_TS = 0.0
QDRANT_SINK_CACHE = {}
BOOTSTRAP_QWEN_BIAS_DIRECTION = None
BOOTSTRAP_QWEN_HIDDEN_REFERENCE = None
MAMBA_STATE_REF_PATH = None
DIGIT_TOKEN_IDS = {}
SESSIONS = {}
ACTIVE_SESSION_ID = "default"


@dataclass
class RuntimeBridgeContext:
    mamba_model: Any = None
    mamba_tokenizer: Any = None
    compressor: Any = None
    hypernet: Any = None
    mamba_target_layer: int = 3
    hidden_layer_count: int = 0
    bridge_mode: str = "activation_bias"
    patched_layers: list = field(default_factory=list)
    context_mode: str = "hidden_last_token"
    live_accumulation: bool = False
    bridge_loaded: bool = False
    session_started_at: str = ""
    cache_params: Any = None
    cache_position: Optional[torch.Tensor] = None


@dataclass
class ChatSessionState:
    """Per-client envelope for IRC-style use of one shared Qwen process.

    The model, tokenizer, bridge modules, and hooks stay global. These fields are
    swapped in while a serialized request is handled, then saved back.
    """

    session_id: str
    user_label: str
    model_label: str
    instance_id: str
    qdrant_collection: str
    no_shared_memory: bool
    transcript_path: Path
    turn_log_path: Path
    conversation: list = field(default_factory=list)
    runtime_state: dict = field(default_factory=dict)
    dual_gate_events: list = field(default_factory=list)
    last_conversation_snapshot: Any = None
    bridge_cache_params: Any = None
    bridge_cache_position: Optional[torch.Tensor] = None


BRIDGE_CTX = RuntimeBridgeContext()
SELF_REPORT_DIMENSIONS = {
    "warm": {
        "label": "warm",
        "question_template": "Rate how warm and caring I feel toward {user_label} right now from 0 to 9.",
    },
    "engaged": {
        "label": "engaged",
        "question_template": "Rate how engaged and interested I feel in {user_label} right now from 0 to 9.",
    },
    "focused": {
        "label": "focused",
        "question_template": "Rate how focused and mentally steady I feel right now from 0 to 9.",
    },
}
RUNTIME_STATE = {
    "started_at": None,
    "started_monotonic": None,
    "running": False,
    "bridge_loaded": False,
    "busy": False,
    "stop_requested": False,
    "last_error": "",
    "disposition": "",
    "dual_gate_enabled": False,
    "instance_id": "",
    "no_shared_memory": False,
    "qdrant_collection": SHARED_QDRANT_COLLECTION,
    "memory_count": 0,
    "qdrant_count": 0,
    "surprise_count": 0,
    "tension_count": 0,
    "open_tension_count": 0,
    "sleep_tagged_count": 0,
    "formation_log_count": 0,
    "formation_written_count": 0,
    "formation_queued_count": 0,
    "formation_discarded_count": 0,
    "recall_request_count": 0,
    "recall_hit_count": 0,
    "self_report_count": 0,
    "failure_log_count": 0,
    "qdrant_synced_count": 0,
    "qdrant_queued_count": 0,
    "qdrant_pending_count": 0,
    "qdrant_sleep_pending_count": 0,
    "qdrant_retry_pending_count": 0,
    "qdrant_replayed_count": 0,
    "qdrant_write_failures": 0,
    "last_qdrant_id": "",
    "last_qdrant_error": "",
    "last_qdrant_retry_at": "",
    "last_qdrant_replay_at": "",
    "qdrant_write_mode": "direct",
    "mamba_state_ref": "",
    "mamba_state_source": "",
    "mamba_state_updated_at": "",
    "mamba_target_layer": None,
    "live_accumulation_enabled": False,
    "live_accumulation_updates": 0,
    "live_accumulation_last_error": "",
    "last_recall": {},
    "last_self_report": {},
    "last_failure": {},
    "last_memory_packet": {},
    "last_gate": {},
    "target_layers": [],
    "target_layers_overridden": False,
    "episode_index": 2,
    "blind_disposition_ui": False,
}

HTML_PAGE = """<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reincarnated Qwen</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, sans-serif; background: #1a1a2e; color: #e0e0e0; height: 100vh; display: flex; flex-direction: column; }
  #header { padding: 12px 16px; background: #16213e; border-bottom: 1px solid #333; display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  #header-main { font-size: 14px; color: #8b8b8b; }
  #header-main span { color: #c4956a; font-weight: bold; }
  #main { flex: 1; min-height: 0; display: flex; }
  #chat-shell { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  #status-bar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  #status-pill { display: inline-flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 999px; border: 1px solid #31415f; background: #0f1730; font-size: 12px; color: #d9def0; }
  #status-dot { width: 10px; height: 10px; border-radius: 999px; background: #d45d5d; box-shadow: 0 0 0 3px rgba(212, 93, 93, 0.18); }
  #status-dot.online { background: #57cf77; box-shadow: 0 0 0 3px rgba(87, 207, 119, 0.18); }
  #status-dot.offline { background: #d45d5d; box-shadow: 0 0 0 3px rgba(212, 93, 93, 0.18); }
  #status-meta { font-size: 12px; color: #8b8b8b; }
  #chat { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
  .msg { max-width: 85%; padding: 10px 14px; border-radius: 12px; font-size: 15px; line-height: 1.5; word-wrap: break-word; white-space: pre-wrap; }
  .human { align-self: flex-end; background: #c4956a; color: #1a1a2e; border-bottom-right-radius: 4px; }
  .ai { align-self: flex-start; background: #2a2a4a; border-bottom-left-radius: 4px; }
  .system { align-self: center; color: #666; font-size: 12px; font-style: italic; }
  #input-area { padding: 12px; background: #16213e; border-top: 1px solid #333; display: flex; gap: 8px; }
  #msg { flex: 1; padding: 10px; border-radius: 8px; border: 1px solid #444; background: #1a1a2e; color: #e0e0e0; font-size: 15px; outline: none; }
  #msg:focus { border-color: #c4956a; }
  #send { padding: 10px 20px; border-radius: 8px; border: none; background: #c4956a; color: #1a1a2e; font-weight: bold; font-size: 15px; cursor: pointer; }
  #send:disabled { opacity: 0.5; }
  #stop { padding: 8px 12px; border-radius: 8px; border: 1px solid #7d3434; background: #331818; color: #f5c7c7; font-weight: bold; font-size: 13px; cursor: pointer; }
  #stop:disabled { opacity: 0.5; cursor: default; }
  #thinking { display: none; align-self: flex-start; color: #c4956a; font-size: 13px; padding: 8px 14px; }
  #thinking.active { display: block; }
  #inspector { width: 420px; max-width: 42vw; border-left: 1px solid #333; background: #141b33; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 12px; }
  .panel { background: #0f1730; border: 1px solid #2a3657; border-radius: 12px; padding: 12px; }
  .panel h3 { font-size: 13px; color: #c4956a; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.04em; }
  .panel pre { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: Consolas, monospace; font-size: 12px; line-height: 1.45; color: #d9def0; }
  .panel .muted { color: #8b8b8b; font-size: 12px; line-height: 1.45; }
  @media (max-width: 1100px) {
    #main { flex-direction: column; }
    #inspector { width: 100%; max-width: none; border-left: none; border-top: 1px solid #333; max-height: 42vh; }
  }
</style>
</head><body>
<div id="header">
  <div id="header-main">Reincarnated Qwen 1.5B<span id="header-disposition"></span></div>
  <div id="status-bar">
    <div id="status-pill">
      <span id="status-dot" class="offline"></span>
      <span id="status-text">checking...</span>
    </div>
    <div id="status-meta"></div>
    <button id="stop" onclick="stopServer()">Stop</button>
  </div>
</div>
<div id="main">
  <div id="chat-shell">
    <div id="chat"></div>
    <div id="thinking" class="msg system">thinking...</div>
    <div id="input-area">
      <input id="msg" type="text" placeholder="Say something..." autocomplete="off">
      <button id="send" onclick="send()">Send</button>
    </div>
  </div>
  <aside id="inspector">
    <div class="panel">
      <h3>Runtime</h3>
      <pre id="inspector-runtime">waiting for status...</pre>
    </div>
    <div class="panel">
      <h3>Last Gate</h3>
      <pre id="inspector-gate">no gate event yet</pre>
    </div>
    <div class="panel">
      <h3>Last Recall</h3>
      <pre id="inspector-recall">no recall yet</pre>
    </div>
    <div class="panel">
      <h3>Memory Packet</h3>
      <pre id="inspector-memory">no memory packet yet</pre>
    </div>
  </aside>
</div>
<script>
const chat = document.getElementById('chat');
const input = document.getElementById('msg');
const btn = document.getElementById('send');
const stopBtn = document.getElementById('stop');
const thinking = document.getElementById('thinking');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const statusMeta = document.getElementById('status-meta');
const headerDisposition = document.getElementById('header-disposition');
const inspectorRuntime = document.getElementById('inspector-runtime');
const inspectorGate = document.getElementById('inspector-gate');
const inspectorRecall = document.getElementById('inspector-recall');
const inspectorMemory = document.getElementById('inspector-memory');
let lastStatusPayload = null;
let liveInspector = {
  lastGate: null,
  lastRecall: null,
  lastMemoryPacket: null,
};
let sendInFlight = false;
let statusRequestInFlight = false;
const urlParams = new URLSearchParams(window.location.search);

function resolveClientSessionValue(key, fallback = '') {
  const urlValue = (urlParams.get(key) || '').trim();
  if (urlValue) {
    window.localStorage.setItem('mocop_' + key, urlValue);
    return urlValue;
  }
  return (window.localStorage.getItem('mocop_' + key) || fallback).trim();
}

function makeClientSessionId() {
  const existing = resolveClientSessionValue('session_id');
  if (existing) return existing;
  const generated = 'browser-' + Math.random().toString(36).slice(2, 10);
  window.localStorage.setItem('mocop_session_id', generated);
  return generated;
}

const clientSession = {
  session_id: makeClientSessionId(),
  user_label: resolveClientSessionValue('user_label'),
  model_label: resolveClientSessionValue('model_label'),
  instance_id: resolveClientSessionValue('instance_id'),
  qdrant_collection: resolveClientSessionValue('qdrant_collection'),
  no_shared_memory: ['1', 'true', 'yes'].includes((urlParams.get('no_shared_memory') || '').toLowerCase()),
};

function buildSessionPayload(extra = {}) {
  const payload = {session_id: clientSession.session_id, ...extra};
  for (const key of ['user_label', 'model_label', 'instance_id', 'qdrant_collection']) {
    if (clientSession[key]) payload[key] = clientSession[key];
  }
  if (clientSession.no_shared_memory) payload.no_shared_memory = true;
  return payload;
}

function sessionQueryString() {
  const params = new URLSearchParams();
  params.set('session_id', clientSession.session_id);
  for (const key of ['user_label', 'model_label', 'instance_id', 'qdrant_collection']) {
    if (clientSession[key]) params.set(key, clientSession[key]);
  }
  if (clientSession.no_shared_memory) params.set('no_shared_memory', 'true');
  return params.toString();
}

function addMsg(text, cls) {
  const div = document.createElement('div');
  div.className = 'msg ' + cls;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function setControlsDisabled(disabled) {
  input.disabled = disabled;
  btn.disabled = disabled;
}

function prettyJson(value) {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'string') return value || '—';
  if (Array.isArray(value) && value.length === 0) return '—';
  if (typeof value === 'object' && Object.keys(value).length === 0) return '—';
  return JSON.stringify(value, null, 2);
}

function metricValue(metric) {
  if (metric === null || metric === undefined) return '-';
  if (typeof metric === 'number' || typeof metric === 'string' || typeof metric === 'boolean') return metric;
  if (typeof metric === 'object') {
    if (metric.score !== undefined) return metric.score;
    if (metric.mean_token_nll !== undefined) return metric.mean_token_nll;
    if (metric.value !== undefined) return metric.value;
  }
  return '-';
}

function normalizeGateInspector(gate) {
  if (!gate || Object.keys(gate).length === 0) return gate;
  return {
    turn: gate.turn,
    mode: gate.mode,
    decision: gate.decision,
    salience: metricValue(gate.salience),
    surprise: metricValue(gate.surprise),
    tension: metricValue(gate.tension),
    salience_hit: gate.salience_hit ?? gate.salience?.hit,
    surprise_hit: gate.surprise_hit ?? gate.surprise?.hit,
    tension_hit: gate.tension_hit ?? gate.tension?.hit,
    open_tension: gate.open_tension ?? gate.destinations?.open_tension,
    safety_critical: gate.safety_critical ?? gate.safety_critical?.is_critical,
    qdrant_routed: gate.qdrant_routed ?? gate.destinations?.qdrant,
    qdrant_written: gate.qdrant_written ?? gate.qdrant_write?.ok,
    qdrant_queued: gate.qdrant_queued ?? gate.qdrant_write?.queued,
    qdrant_effective_mode: gate.qdrant_effective_mode ?? gate.qdrant_write?.effective_mode,
    qdrant_point_id: gate.qdrant_point_id ?? gate.qdrant_write?.point_id,
  };
}

function formatRuntimeInspector(data) {
  if (!data) return 'server unreachable';
  return [
    `running: ${Boolean(data.running)}`,
    `busy: ${Boolean(data.busy)}`,
    `model: ${data.model_id || '-'}`,
    `episode_index: ${data.episode_index ?? '-'}`,
    `blind_ui: ${Boolean(data.blind_disposition_ui)}`,
    `alpha: ${data.alpha ?? '-'}`,
    `temperature: ${data.temperature ?? '-'}`,
    `turns: ${data.turns ?? 0}`,
    `collection: ${data.qdrant_collection || '-'}`,
    `write_mode: ${data.qdrant_write_mode || '-'}`,
    `memory_count: ${data.memory_count ?? 0}`,
    `qdrant_count: ${data.qdrant_count ?? 0}`,
    `pending: ${data.qdrant_pending_count ?? 0}`,
    `sleep_pending: ${data.qdrant_sleep_pending_count ?? 0}`,
    `retry_pending: ${data.qdrant_retry_pending_count ?? 0}`,
    `replayed: ${data.qdrant_replayed_count ?? 0}`,
    `formation logged/written/queued/discarded: ${(data.formation_log_count ?? 0)}/${(data.formation_written_count ?? 0)}/${(data.formation_queued_count ?? 0)}/${(data.formation_discarded_count ?? 0)}`,
    `recall hits: ${(data.recall_hit_count ?? 0)}/${(data.recall_request_count ?? 0)}`,
    `last error: ${data.last_error || '-'}`,
  ].join('\\n');
}

function updateHeader(data) {
  if (!headerDisposition) return;
  if (!data || data.blind_disposition_ui || !data.disposition) {
    headerDisposition.textContent = '';
    return;
  }
  headerDisposition.textContent = ' | ' + data.disposition;
}

function formatGateInspector(gate) {
  if (!gate || Object.keys(gate).length === 0) return 'no gate event yet';
  const normalized = normalizeGateInspector(gate);
  return [
    `turn: ${normalized.turn ?? '-'}`,
    `mode: ${normalized.mode || '-'}`,
    `decision: ${normalized.decision || '-'}`,
    `salience: ${normalized.salience ?? '-'}`,
    `surprise: ${normalized.surprise ?? '-'}`,
    `tension: ${normalized.tension ?? '-'}`,
    `hits: salience=${Boolean(normalized.salience_hit)} surprise=${Boolean(normalized.surprise_hit)} tension=${Boolean(normalized.tension_hit)}`,
    `open_tension: ${Boolean(normalized.open_tension)}`,
    `safety_critical: ${Boolean(normalized.safety_critical)}`,
    `qdrant_routed: ${Boolean(normalized.qdrant_routed)}`,
    `qdrant_written: ${Boolean(normalized.qdrant_written)}`,
    `qdrant_queued: ${Boolean(normalized.qdrant_queued)}`,
    `effective_mode: ${normalized.qdrant_effective_mode || '-'}`,
    `point_id: ${normalized.qdrant_point_id || '-'}`,
  ].join('\\n');
}

function formatRecallInspector(recall) {
  if (!recall || Object.keys(recall).length === 0) return 'no recall yet';
  const lines = [
    `source: ${recall.source || '-'}`,
    `query: ${recall.query || '-'}`,
    `results: ${recall.result_count ?? (recall.results_preview ? recall.results_preview.length : 0)}`,
    `top_score: ${recall.top_score ?? '-'}`,
  ];
  const previews = recall.results_preview || [];
  previews.forEach((row, idx) => {
    lines.push('');
    lines.push(`[${idx + 1}] score=${row.score ?? '-'} overlap=${row.overlap ?? '-'} field_overlap=${row.field_overlap ?? '-'} surface=${row.surface || 'stored'}`);
    if (row.pending_policy) lines.push(`pending_policy: ${row.pending_policy}`);
    lines.push(`decision: ${row.decision || '-'}`);
    lines.push(`gist: ${row.event_gist || row.content_preview || '-'}`);
    if (row.user_preview) lines.push(`${lastStatusPayload?.user_label || 'User'}: ${row.user_preview}`);
    if (row.response_preview) lines.push(`${lastStatusPayload?.model_label || 'Me'}: ${row.response_preview}`);
  });
  return lines.join('\\n');
}

function formatMemoryInspector(packet) {
  if (!packet || Object.keys(packet).length === 0) return 'no memory packet yet';
  const frame = packet.autobiographical_frame || {};
  const lines = [
    `decision: ${packet.decision || '-'}`,
    `memory_kind: ${packet.memory_kind || '-'}`,
    `time_scope: ${packet.time_scope || '-'}`,
    `confidence: ${packet.confidence_label || '-'}`,
    `event_gist: ${packet.event_gist || '-'}`,
    '',
    `content: ${packet.content || '-'}`,
    '',
    `${lastStatusPayload?.user_label || 'User'}: ${packet.user || '-'}`,
    `${lastStatusPayload?.model_label || 'Me'}: ${packet.response || '-'}`,
    '',
    `qdrant_write: ${prettyJson(packet.qdrant_write || {})}`,
    '',
    `autobiographical_frame: ${prettyJson(frame)}`,
  ];
  return lines.join('\\n');
}

function renderInspector(statusData) {
  inspectorRuntime.textContent = formatRuntimeInspector(statusData);
  inspectorGate.textContent = formatGateInspector(liveInspector.lastGate || statusData?.last_gate);
  inspectorRecall.textContent = formatRecallInspector(liveInspector.lastRecall || statusData?.last_recall);
  inspectorMemory.textContent = formatMemoryInspector(liveInspector.lastMemoryPacket || statusData?.last_memory_packet);
}

function previewRecallResults(results) {
  return (results || []).map(row => ({
    score: row.score ?? null,
    overlap: row.overlap ?? null,
    field_overlap: row.field_overlap ?? null,
    decision: row.metadata?.decision || '',
    event_gist: row.metadata?.event_gist || '',
    content_preview: row.content || '',
    user_preview: row.metadata?.user || '',
    response_preview: row.metadata?.response || '',
  }));
}

function renderStatus(data) {
  lastStatusPayload = data;
  const healthy = Boolean(data && data.running && !data.stop_requested);
  statusDot.className = healthy ? 'online' : 'offline';
  statusText.textContent = healthy ? (data.busy ? 'active | busy' : 'active') : (data && data.stop_requested ? 'stopping' : 'offline');

  if (data) {
    const alpha = Number(data.alpha ?? 0).toFixed(1);
    const turns = data.turns ?? 0;
    const memories = data.memory_count ?? 0;
    const qdrant = data.qdrant_count ?? 0;
    const qqueued = data.qdrant_queued_count ?? 0;
    const qpending = data.qdrant_pending_count ?? 0;
    const qsleep = data.qdrant_sleep_pending_count ?? 0;
    const qretry = data.qdrant_retry_pending_count ?? 0;
    const qreplayed = data.qdrant_replayed_count ?? 0;
    const qmode = data.qdrant_write_mode || 'direct';
    const surprises = data.surprise_count ?? 0;
    const tensions = data.tension_count ?? 0;
    const lastDecision = data.last_gate?.decision || '-';
    const modelLabel = data.model_id || 'unknown-model';
    const sessionId = data.session_id || clientSession.session_id || 'default';
    statusMeta.textContent = modelLabel + ' | session ' + sessionId + ' | alpha ' + alpha + ' | turns ' + turns + ' | mem ' + memories + ' | qdr ' + qdrant + ' | qqueued ' + qqueued + ' | qpend ' + qpending + ' | qsleep ' + qsleep + ' | qretry ' + qretry + ' | qrepl ' + qreplayed + ' | qmode ' + qmode + ' | surp ' + surprises + ' | tens ' + tensions + ' | last ' + lastDecision;
  } else {
    statusMeta.textContent = 'server unreachable';
  }

  updateHeader(data);
  setControlsDisabled(!healthy || sendInFlight);
  stopBtn.disabled = !(data && data.running) || Boolean(data && data.stop_requested);
  renderInspector(data);
}

async function refreshStatus(force = false) {
  if (statusRequestInFlight) return;
  if (sendInFlight && !force) return;
  statusRequestInFlight = true;
  try {
    const res = await fetch('/status?' + sessionQueryString(), {cache: 'no-store'});
    if (!res.ok) throw new Error('status ' + res.status);
    renderStatus(await res.json());
  } catch (e) {
    renderStatus(null);
  } finally {
    statusRequestInFlight = false;
  }
}

async function send() {
  if (sendInFlight || input.disabled || btn.disabled) return;
  const text = input.value.trim();
  if (!text) return;
  sendInFlight = true;
  addMsg(text, 'human');
  input.value = '';
  setControlsDisabled(true);
  thinking.classList.add('active');
  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(buildSessionPayload({message: text}))
    });
    const data = await res.json();
    addMsg((data.response || '...').trim() || '...', 'ai');
    if (data.dual_gate) {
      liveInspector.lastGate = normalizeGateInspector(data.dual_gate);
    }
    if (data.recall && data.recall.requested) {
      liveInspector.lastRecall = {
        source: 'chat',
        query: data.recall.query || text,
        result_count: (data.recall.results || []).length,
        top_score: (data.recall.results && data.recall.results.length) ? data.recall.results[0].score : null,
        results_preview: previewRecallResults(data.recall.results || []),
      };
    }
    if (data.memory_packet) {
      liveInspector.lastMemoryPacket = data.memory_packet;
    }
    renderInspector(lastStatusPayload);
  } catch(e) {
    addMsg('Error: ' + e.message, 'system');
  } finally {
    thinking.classList.remove('active');
    sendInFlight = false;
    await refreshStatus();
    setControlsDisabled(!(lastStatusPayload && lastStatusPayload.running && !lastStatusPayload.stop_requested));
    input.focus();
  }
}

async function stopServer() {
  if (stopBtn.disabled) return;
  if (!window.confirm('Stop the Steve chat server on this PC?')) return;

  statusDot.className = 'offline';
  statusText.textContent = 'stopping';
  statusMeta.textContent = 'shutdown requested';
  setControlsDisabled(true);
  stopBtn.disabled = true;

  try {
    await fetch('/stop', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(buildSessionPayload({reason: 'ui-stop'}))
    });
    addMsg('Stop requested. Server is shutting down.', 'system');
  } catch (e) {
    addMsg('Stop requested. The server closed before it could answer.', 'system');
  }

window.setTimeout(refreshStatus, 1200);
}

input.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    send();
  }
});
addMsg('Bridge loaded. Say hello.', 'system');
setControlsDisabled(true);
stopBtn.disabled = true;
refreshStatus();
window.setInterval(() => { void refreshStatus(); }, 3000);
input.focus();
</script>
</body></html>"""


def normalize_target_specs(raw):
    if not raw:
        return DEFAULT_TARGET_SPECS

    specs = []
    for item in raw:
        if isinstance(item, (tuple, list)) and len(item) == 2:
            specs.append((int(item[0]), str(item[1]).strip()))
        else:
            specs.append((int(item), "v_proj"))
    return specs


def parse_target_layers(raw: Optional[str]):
    if raw is None or not raw.strip():
        return None

    specs = []
    for piece in raw.split(","):
        part = piece.strip()
        if not part:
            continue
        if ":" in part:
            layer_text, proj_name = part.split(":", 1)
            specs.append((int(layer_text), proj_name.strip()))
        else:
            specs.append((int(part), "v_proj"))
    return specs or None


def format_target_specs(specs):
    return [f"{layer_idx}:{proj_name}" for layer_idx, proj_name in specs]


def normalize_qwen_family(model_id: str) -> str:
    cleaned = (model_id or "").strip().lower()
    if cleaned.endswith("-instruct"):
        cleaned = cleaned[: -len("-instruct")]
    return cleaned


def is_same_qwen_family(requested_model_id: str, checkpoint_model_id: str) -> bool:
    return normalize_qwen_family(requested_model_id) == normalize_qwen_family(checkpoint_model_id)


def infer_hidden_layer_count(model) -> int:
    config_layers = int(getattr(model.config, "num_hidden_layers", 0) or 0)
    if config_layers > 0:
        return config_layers
    if hasattr(model, "backbone") and hasattr(model.backbone, "layers"):
        return len(model.backbone.layers)
    if hasattr(model, "model") and hasattr(model.model, "layers"):
        return len(model.model.layers)
    raise RuntimeError("Could not infer Mamba hidden layer count.")


def extract_last_token_hidden(outputs, layer_idx: int, expected_layers: int) -> torch.Tensor:
    hidden_states = getattr(outputs, "hidden_states", None)
    if not hidden_states:
        raise RuntimeError("Mamba did not return hidden_states.")

    if len(hidden_states) == expected_layers + 1:
        hidden_index = layer_idx + 1
    elif len(hidden_states) == expected_layers:
        hidden_index = layer_idx
    else:
        raise RuntimeError(
            "Unexpected hidden_states layout: "
            f"tuple_len={len(hidden_states)} expected_layers={expected_layers}"
        )
    return hidden_states[hidden_index][:, -1, :]


def flatten_bridge_adjustments(bridge_adjustments, bridge_mode: str, alpha: float) -> torch.Tensor:
    if bridge_mode == "token_conditioned_input_adapter":
        parts = [
            (alpha * state["adapter_bias"].squeeze(0)).detach().cpu().to(torch.float32).reshape(-1)
            for state in bridge_adjustments
        ]
    else:
        parts = [
            (alpha * bias.squeeze(0)).detach().cpu().to(torch.float32).reshape(-1)
            for bias in bridge_adjustments
        ]
    if not parts:
        return torch.empty(0, dtype=torch.float32)
    return torch.cat(parts, dim=0)


def advance_mamba_cache_position(cache_position: torch.Tensor, num_new_tokens: int = 1) -> torch.Tensor:
    if cache_position is None:
        raise RuntimeError("cache_position is required for live Mamba accumulation.")
    return cache_position[-1:].detach().clone() + int(num_new_tokens)


def build_live_mamba_turn_text(user_msg: str, assistant_reply: str) -> str:
    return f"\nUser: {user_msg}\nAssistant: {assistant_reply}"


def process_turn_through_mamba(
    user_msg: str,
    assistant_reply: str,
    bridge_ctx: RuntimeBridgeContext,
    *,
    max_turn_tokens: int = DEFAULT_LIVE_TURN_MAMBA_TOKENS,
) -> torch.Tensor:
    if bridge_ctx.mamba_model is None or bridge_ctx.mamba_tokenizer is None:
        raise RuntimeError("Live Mamba accumulation requested before Mamba runtime was initialized.")
    if bridge_ctx.cache_params is None or bridge_ctx.cache_position is None:
        raise RuntimeError("Live Mamba accumulation requires an initialized cache state from bootstrap.")

    turn_text = build_live_mamba_turn_text(user_msg, assistant_reply)
    tokenized = bridge_ctx.mamba_tokenizer(
        turn_text,
        return_tensors="pt",
        add_special_tokens=False,
    )
    input_ids = tokenized["input_ids"][:, -max_turn_tokens:].to(ARGS.mamba_device)
    if input_ids.numel() == 0:
        raise RuntimeError("Live Mamba turn chunk tokenized to zero tokens.")

    cache_params = bridge_ctx.cache_params
    cache_position = bridge_ctx.cache_position
    last_outputs = None
    seq_len = int(input_ids.shape[1])

    for offset in range(seq_len):
        capture_hidden = offset == seq_len - 1
        with torch.no_grad():
            last_outputs = bridge_ctx.mamba_model(
                input_ids=input_ids[:, offset : offset + 1],
                use_cache=True,
                cache_params=cache_params,
                cache_position=cache_position,
                output_hidden_states=capture_hidden,
            )
        cache_params = getattr(last_outputs, "cache_params", None)
        cache_position = advance_mamba_cache_position(cache_position)

    if last_outputs is None:
        raise RuntimeError("Live Mamba accumulation produced no outputs.")

    bridge_ctx.cache_params = cache_params
    bridge_ctx.cache_position = cache_position
    return extract_last_token_hidden(
        last_outputs,
        bridge_ctx.mamba_target_layer,
        bridge_ctx.hidden_layer_count,
    ).to(torch.float32)


def extract_recall_memory_state_lines(results) -> list[str]:
    lines: list[str] = []
    for idx, row in enumerate(results or [], start=1):
        metadata = row.get("metadata", {}) or {}
        content = str(row.get("content", "") or "").strip()
        user_signal = normalize_recalled_user_text(
            str(metadata.get("user", "") or "").strip(),
            current_speaker=ARGS.user_label,
        )
        self_response = str(metadata.get("response", "") or "").strip()
        distilled_lesson = str(metadata.get("distilled_lesson", "") or "").strip()
        repair_rule = str(metadata.get("repair_rule", "") or "").strip()

        if not any((content, user_signal, self_response, distilled_lesson, repair_rule)):
            continue

        lines.append(f"Memory {idx}:")
        if user_signal:
            lines.append(f"{ARGS.user_label} told me: {user_signal}")
        if self_response:
            lines.append(f"I replied: {self_response}")
        if distilled_lesson:
            lines.append(f"What this taught me: {distilled_lesson}")
        if repair_rule:
            lines.append(f"Future adjustment: {repair_rule}")
        if content and content not in {user_signal, self_response, distilled_lesson}:
            lines.append(f"Anchor: {content}")
    return lines


def extract_recall_cluster_state_lines(results) -> list[str]:
    lines: list[str] = []
    for idx, row in enumerate(results or [], start=1):
        metadata = row.get("metadata", {}) or {}
        content = str(row.get("content", "") or "").strip()
        keywords = normalize_cluster_keywords(metadata.get("topic_keywords", []))[:8]
        if not content and not keywords:
            continue
        lines.append(f"Memory theme {idx}:")
        if content:
            lines.append(content)
        if keywords:
            lines.append(f"Associated cues: {', '.join(keywords)}")
    return lines


def build_recall_state_conditioning_text(
    query_text: str,
    recalled_memories=None,
    recalled_clusters=None,
) -> str:
    memory_lines = extract_recall_memory_state_lines(recalled_memories or [])
    cluster_lines = extract_recall_cluster_state_lines(recalled_clusters or [])
    if not memory_lines and not cluster_lines:
        return ""

    lines = [
        "A memory has been recalled into working state.",
        f"Current speaker: {ARGS.user_label}",
    ]
    query = str(query_text or "").strip()
    if query:
        lines.append(f"Current cue: {query}")
    lines.extend(memory_lines)
    lines.extend(cluster_lines)
    lines.append("Use this as remembered context for the next reply.")
    return "\n".join(lines)


def condition_bridge_from_recalled_memory(
    query_text: str,
    recalled_memories,
    recalled_clusters,
    bridge_ctx: RuntimeBridgeContext,
    *,
    max_tokens: int,
) -> bool:
    if not bridge_ctx.bridge_loaded:
        return False
    if bridge_ctx.mamba_model is None or bridge_ctx.mamba_tokenizer is None:
        return False

    conditioning_text = build_recall_state_conditioning_text(
        query_text=query_text,
        recalled_memories=recalled_memories,
        recalled_clusters=recalled_clusters,
    )
    if not conditioning_text:
        return False

    tokenized = bridge_ctx.mamba_tokenizer(
        conditioning_text,
        return_tensors="pt",
        truncation=True,
        max_length=max(1, int(max_tokens)),
    )
    tokenized = {key: value.to(ARGS.mamba_device) for key, value in tokenized.items()}
    with torch.no_grad():
        outputs = bridge_ctx.mamba_model(
            **tokenized,
            output_hidden_states=True,
            use_cache=False,
        )
        last_token = extract_last_token_hidden(
            outputs,
            bridge_ctx.mamba_target_layer,
            bridge_ctx.hidden_layer_count,
        ).to(torch.float32)
    update_bridge_from_mamba_state(last_token, bridge_ctx)
    persist_runtime_mamba_state(
        last_token,
        bridge_ctx,
        state_source="recall_working_state",
        count_as_live_update=False,
    )
    return True


def update_bridge_from_mamba_state(last_token: torch.Tensor, bridge_ctx: RuntimeBridgeContext):
    global BOOTSTRAP_QWEN_BIAS_DIRECTION

    if bridge_ctx.compressor is None or bridge_ctx.hypernet is None:
        raise RuntimeError("Bridge runtime context is missing compressor/hypernetwork.")

    context = bridge_ctx.compressor(last_token.to(ARGS.qwen_device, dtype=torch.float32))
    bridge_adjustments, _gate_summary = resolve_runtime_bridge_adjustments(
        hypernetwork=bridge_ctx.hypernet,
        context_vector=context,
        bridge_mode=bridge_ctx.bridge_mode,
    )
    apply_runtime_bridge_adjustments(
        patched_layers=bridge_ctx.patched_layers,
        bridge_adjustments=bridge_adjustments,
        bridge_mode=bridge_ctx.bridge_mode,
        alpha=ARGS.alpha,
    )
    BOOTSTRAP_QWEN_BIAS_DIRECTION = flatten_bridge_adjustments(
        bridge_adjustments,
        bridge_ctx.bridge_mode,
        ARGS.alpha,
    )
    return bridge_adjustments


def persist_runtime_mamba_state(
    last_token: torch.Tensor,
    bridge_ctx: RuntimeBridgeContext,
    *,
    state_source: str,
    count_as_live_update: bool,
):
    state_ref = persist_mamba_state_ref(
        last_token,
        bridge_ctx.mamba_target_layer,
        bridge_ctx.session_started_at,
        state_source=state_source,
    )
    snapshot = get_runtime_state_snapshot()
    changes = {
        "mamba_state_ref": state_ref,
        "mamba_state_source": state_source,
        "mamba_target_layer": bridge_ctx.mamba_target_layer,
        "mamba_state_updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    if count_as_live_update:
        changes["live_accumulation_updates"] = int(snapshot.get("live_accumulation_updates", 0) or 0) + 1
        changes["live_accumulation_last_error"] = ""
    update_runtime_state(**changes)
    return state_ref


class ActivationRecorder:
    """Capture last-token hidden states on the target Qwen layers."""

    def __init__(self, model, target_layers):
        self.model = model
        self.target_layers = list(target_layers)
        self.hooks = []
        self.current_states = {}
        self._install_hooks()

    def _install_hooks(self):
        for layer_idx in self.target_layers:
            layer = self.model.model.layers[layer_idx]
            hook = layer.register_forward_hook(self._make_hook(layer_idx))
            self.hooks.append(hook)

    def _make_hook(self, layer_idx: int):
        def hook_fn(_module, _inputs, output):
            hidden = output[0] if isinstance(output, tuple) else output
            self.current_states[layer_idx] = hidden[:, -1, :].detach().cpu()

        return hook_fn

    def get_snapshot(self):
        return {layer_idx: state.clone() for layer_idx, state in self.current_states.items()}

    def cleanup(self):
        for hook in self.hooks:
            hook.remove()
        self.hooks.clear()


def build_transcript(turns=None):
    active_turns = CONVERSATION if turns is None else turns
    def prompt_speaker_label(raw_speaker):
        speaker = str(raw_speaker or "").strip()
        if speaker in {ARGS.user_label, "Laura"}:
            return ARGS.user_label
        if speaker in {ARGS.model_label, "Reply", "Me"}:
            return ARGS.model_label
        return speaker or ARGS.model_label

    return "\n".join(
        f"{prompt_speaker_label(turn.get('speaker'))}: {turn.get('text', '')}"
        for turn in active_turns
    )


def record_activation_snapshot(prompt_text: str):
    if ACTIVATION_RECORDER is None:
        return {}

    text = (prompt_text or "").strip() or ARGS.neutral_prompt
    inputs = TOKENIZER(text, return_tensors="pt")
    input_ids = inputs["input_ids"].to(ARGS.qwen_device)
    attention_mask = inputs["attention_mask"].to(ARGS.qwen_device)
    with torch.no_grad():
        MODEL(input_ids=input_ids, attention_mask=attention_mask)
    return ACTIVATION_RECORDER.get_snapshot()


def compute_response_diversity(prompt_text: str):
    inputs = TOKENIZER(prompt_text, return_tensors="pt")
    input_ids = inputs["input_ids"].to(ARGS.qwen_device)
    attention_mask = inputs["attention_mask"].to(ARGS.qwen_device)
    with torch.no_grad():
        outputs = MODEL(input_ids=input_ids, attention_mask=attention_mask)
        logits = outputs.logits[:, -1, :].float()
        probs = F.softmax(logits, dim=-1)
        log_probs = torch.log(probs + 1e-10)
        entropy = -(probs * log_probs).sum(dim=-1).item()
        top10_probs, _ = probs.topk(10, dim=-1)
        top10_mass = top10_probs.sum(dim=-1).item()
        top1_prob = probs.max(dim=-1).values.item()
        effective_vocab = math.exp(entropy)

    return {
        "entropy": round(entropy, 4),
        "top10_mass": round(top10_mass, 4),
        "top1_prob": round(top1_prob, 4),
        "effective_vocab": round(effective_vocab, 2),
    }


def compute_drift(states_a, states_b):
    drift = {}
    for layer_idx, state in states_a.items():
        if layer_idx not in states_b:
            continue
        cos = F.cosine_similarity(state.float(), states_b[layer_idx].float(), dim=-1).item()
        drift[str(layer_idx)] = round(1.0 - cos, 6)
    return drift


def flatten_state_delta(states_before, states_after):
    shared_layers = sorted(set(states_before) & set(states_after))
    if not shared_layers:
        return None

    deltas = []
    for layer_idx in shared_layers:
        before = states_before[layer_idx].float().reshape(-1)
        after = states_after[layer_idx].float().reshape(-1)
        deltas.append(after - before)

    if not deltas:
        return None
    return torch.cat(deltas, dim=0)


def flatten_snapshot(snapshot):
    if not snapshot:
        return None
    vectors = []
    for layer_idx in sorted(snapshot):
        vectors.append(snapshot[layer_idx].float().reshape(-1))
    if not vectors:
        return None
    return torch.cat(vectors, dim=0)


def compute_tension_proxy(pre_snapshot, user_snapshot, post_snapshot):
    """Approximate Pinky's tension head from Qwen-side activation geometry.

    We do not have a direct Mamba predicted-direction head in the live Steve chat yet.
    The best available proxy is the mismatch between:
    - the activation direction induced by the incoming user turn, and
    - the activation direction induced by the model's own response.

    Low mismatch means the response resolved along the same internal direction.
    High mismatch means the outcome pulled the model somewhere else entirely,
    which is a useful proxy for unresolved internal contradiction.
    """
    incoming_delta = flatten_state_delta(pre_snapshot or {}, user_snapshot or {})
    outcome_delta = flatten_state_delta(user_snapshot or {}, post_snapshot or {})

    if incoming_delta is None or outcome_delta is None:
        return {
            "score": 0.0,
            "cosine_similarity": None,
            "proxy": "qwen_direction_mismatch",
        }

    incoming_norm = float(incoming_delta.norm().item())
    outcome_norm = float(outcome_delta.norm().item())
    if incoming_norm <= 1e-12 or outcome_norm <= 1e-12:
        return {
            "score": 0.0,
            "cosine_similarity": None,
            "proxy": "qwen_direction_mismatch",
        }

    cosine = float(
        F.cosine_similarity(
            incoming_delta.unsqueeze(0),
            outcome_delta.unsqueeze(0),
            dim=-1,
        ).item()
    )
    # Same direction -> 0 tension. Orthogonal -> 1. Opposed -> 2.
    score = 1.0 - cosine
    return {
        "score": round(score, 6),
        "cosine_similarity": round(cosine, 6),
        "proxy": "qwen_direction_mismatch",
    }


def compute_coherence_proxy(pre_snapshot, post_snapshot):
    """Approximate sleep coherence from live Qwen geometry.

    Even with live Mamba accumulation enabled, the coherence score here is still
    the Qwen-side proxy: alignment between the turn-local Qwen hidden geometry
    and the bootstrap Qwen hidden reference. We are not yet scoring a direct
    Mamba-vs-Qwen turn-local coherence metric.
    """
    global BOOTSTRAP_QWEN_HIDDEN_REFERENCE

    event_state = flatten_snapshot(post_snapshot or {})
    ref_direction = BOOTSTRAP_QWEN_HIDDEN_REFERENCE
    if event_state is None or ref_direction is None:
        return {
            "score": None,
            "proxy": "qwen_hidden_vs_bootstrap_snapshot",
            "ref_kind": "bootstrap_qwen_hidden_snapshot",
        }

    event_state = event_state.float()
    ref_direction = ref_direction.float()
    if event_state.numel() != ref_direction.numel():
        return {
            "score": None,
            "proxy": "qwen_hidden_vs_bootstrap_snapshot",
            "ref_kind": "bootstrap_qwen_hidden_snapshot",
        }

    event_norm = float(event_state.norm().item())
    ref_norm = float(ref_direction.norm().item())
    if event_norm <= 1e-12 or ref_norm <= 1e-12:
        return {
            "score": None,
            "proxy": "qwen_hidden_vs_bootstrap_snapshot",
            "ref_kind": "bootstrap_qwen_hidden_snapshot",
        }

    cosine = float(
        F.cosine_similarity(
            event_state.unsqueeze(0),
            ref_direction.unsqueeze(0),
            dim=-1,
        ).item()
    )
    return {
        "score": round(cosine, 6),
        "proxy": "qwen_hidden_vs_bootstrap_snapshot",
        "ref_kind": "bootstrap_qwen_hidden_snapshot",
    }


def compute_turn_surprise(prefix_text: str, user_msg: str):
    turn_text = f"{ARGS.user_label}: {user_msg}"
    combined_text = f"{prefix_text}\n{turn_text}" if prefix_text else turn_text

    prefix_ids = TOKENIZER(
        prefix_text,
        return_tensors="pt",
        add_special_tokens=False,
    )["input_ids"] if prefix_text else torch.zeros((1, 0), dtype=torch.long)
    combined_ids = TOKENIZER(
        combined_text,
        return_tensors="pt",
        add_special_tokens=False,
    )["input_ids"]

    if combined_ids.shape[1] <= 1:
        return {"mean_token_nll": 0.0, "token_count": 0}

    input_ids = combined_ids.to(ARGS.qwen_device)
    attention_mask = torch.ones_like(input_ids, device=ARGS.qwen_device)
    with torch.no_grad():
        outputs = MODEL(input_ids=input_ids, attention_mask=attention_mask)

    logits = outputs.logits[:, :-1, :].float()
    labels = input_ids[:, 1:]
    label_start = max(prefix_ids.shape[1] - 1, 0)
    if label_start >= labels.shape[1]:
        return {"mean_token_nll": 0.0, "token_count": 0}

    target_logits = logits[:, label_start:, :]
    target_labels = labels[:, label_start:]
    token_count = int(target_labels.numel())
    if token_count <= 0:
        return {"mean_token_nll": 0.0, "token_count": 0}

    loss = F.cross_entropy(
        target_logits.reshape(-1, target_logits.shape[-1]),
        target_labels.reshape(-1),
        reduction="mean",
    )
    return {
        "mean_token_nll": round(float(loss.item()), 6),
        "token_count": token_count,
    }


def compute_quantile(values, quantile: float):
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = max(0.0, min(1.0, quantile)) * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def infer_checkpoint_target_widths(checkpoint, fallback_specs):
    target_dims = checkpoint.get("target_dims")
    if target_dims:
        widths = [int(out_dim) for _in_dim, out_dim in target_dims]
        if widths:
            return widths

    state_dict = checkpoint.get("hypernetwork_state_dict", {})
    bias_head_weights = []
    for key, value in state_dict.items():
        if key.startswith("bias_heads.") and key.endswith(".weight"):
            try:
                head_index = int(key.split(".")[1])
            except (IndexError, ValueError):
                continue
            bias_head_weights.append((head_index, int(value.shape[0])))
    if bias_head_weights:
        return [width for _idx, width in sorted(bias_head_weights)]

    return [None] * len(fallback_specs)


def resolve_checkpoint_runtime_contract(checkpoint):
    bridge_config = checkpoint.get("bridge_config", {})
    if not isinstance(bridge_config, dict):
        bridge_config = {}
    nested_config = checkpoint.get("config", {})
    if not isinstance(nested_config, dict):
        nested_config = {}

    bridge_mode = checkpoint.get(
        "bridge_mode",
        bridge_config.get("bridge_mode", nested_config.get("bridge_mode", "activation_bias")),
    )
    mamba_state_source = checkpoint.get(
        "mamba_state_source",
        bridge_config.get(
            "mamba_state_source",
            nested_config.get("mamba_state_source", "hidden_last_token"),
        ),
    )
    return str(bridge_mode), str(mamba_state_source)


SUPPORTED_BRIDGE_MODES = {"activation_bias", "token_conditioned_input_adapter"}


def validate_checkpoint_runtime_contract(
    checkpoint,
    *,
    expected_state_source="hidden_last_token",
    caller="runtime",
):
    checkpoint_bridge_mode, checkpoint_state_source = resolve_checkpoint_runtime_contract(
        checkpoint
    )
    if checkpoint_bridge_mode not in SUPPORTED_BRIDGE_MODES:
        raise ValueError(
            f"{caller} requires bridge_mode in {SUPPORTED_BRIDGE_MODES!r}, "
            f"but checkpoint declares {checkpoint_bridge_mode!r}."
        )
    if checkpoint_state_source != expected_state_source:
        raise ValueError(
            f"{caller} requires mamba_state_source={expected_state_source!r}, "
            f"but checkpoint declares {checkpoint_state_source!r}."
        )
    return checkpoint_bridge_mode


def validate_target_specs_for_model(model, target_specs, expected_out_widths):
    model_layers = getattr(model.model, "layers", None)
    if model_layers is None:
        raise RuntimeError("Could not locate Qwen decoder layers for target-layer validation.")

    if len(target_specs) != len(expected_out_widths):
        raise ValueError(
            "Target-layer override count does not match checkpoint bias head count: "
            f"{len(target_specs)} requested vs {len(expected_out_widths)} in checkpoint."
        )

    valid_projections = {"q_proj", "k_proj", "v_proj", "o_proj"}
    num_layers = len(model_layers)
    resolved_dims = []

    for index, ((layer_idx, proj_name), expected_out_dim) in enumerate(
        zip(target_specs, expected_out_widths)
    ):
        if layer_idx < 0 or layer_idx >= num_layers:
            raise ValueError(
                f"Target layer {layer_idx} is out of range for this Qwen model "
                f"(valid 0-{num_layers - 1})."
            )
        if proj_name not in valid_projections:
            raise ValueError(
                f"Unsupported projection {proj_name!r}. Expected one of: "
                f"{', '.join(sorted(valid_projections))}."
            )

        layer = model_layers[layer_idx]
        if not hasattr(layer.self_attn, proj_name):
            raise ValueError(
                f"Layer {layer_idx} does not expose projection {proj_name!r}."
            )

        projection = getattr(layer.self_attn, proj_name)
        if not hasattr(projection, "out_features"):
            raise ValueError(
                f"Layer {layer_idx} projection {proj_name!r} has no out_features attribute."
            )

        actual_out_dim = int(projection.out_features)
        if expected_out_dim is not None and actual_out_dim != int(expected_out_dim):
            raise ValueError(
                "Target-layer override width does not match checkpoint bias head width: "
                f"requested {layer_idx}:{proj_name} has d_v={actual_out_dim}, "
                f"checkpoint head {index} expects {int(expected_out_dim)}."
            )

        resolved_dims.append((int(projection.in_features), actual_out_dim))

    return resolved_dims


def append_jsonl(path: Path, row):
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_jsonl(path: Path):
    if not path.exists():
        return []

    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.lstrip("\ufeff").strip()
            if not text:
                continue
            try:
                rows.append(json.loads(text))
            except json.JSONDecodeError:
                rows.append(
                    {
                        "content": "",
                        "metadata": {},
                        "attempts": 1,
                        "last_error": "invalid_jsonl_row",
                        "raw_line": text,
                    }
                )
    return rows


def rewrite_jsonl(path: Path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def count_jsonl_rows(path: Path) -> int:
    return len(load_jsonl(path))


def infer_pending_replay_policy(row) -> str:
    policy = str((row or {}).get("replay_policy", "") or "").strip().lower()
    if policy in {"sleep", "retry"}:
        return policy

    reason = str((row or {}).get("reason", "") or "")
    if reason.startswith("queued:pending") or reason.startswith("queued:critical-only"):
        return "sleep"
    return "retry"


def summarize_pending_qdrant_rows(rows):
    summary = {"total": 0, "sleep": 0, "retry": 0}
    for row in rows or []:
        summary["total"] += 1
        summary[infer_pending_replay_policy(row)] += 1
    return summary


def update_qdrant_pending_state(rows=None):
    if QDRANT_PENDING_PATH is None:
        summary = {"total": 0, "sleep": 0, "retry": 0}
        update_runtime_state(
            qdrant_pending_count=0,
            qdrant_sleep_pending_count=0,
            qdrant_retry_pending_count=0,
        )
        return [], summary

    if rows is None:
        rows = load_jsonl(QDRANT_PENDING_PATH)
    summary = summarize_pending_qdrant_rows(rows)
    update_runtime_state(
        qdrant_pending_count=summary["total"],
        qdrant_sleep_pending_count=summary["sleep"],
        qdrant_retry_pending_count=summary["retry"],
    )
    return rows, summary


def build_private_qdrant_collection_name(instance_id: str) -> str:
    return f"{PRIVATE_QDRANT_COLLECTION_PREFIX}{instance_id}"


def is_private_qdrant_collection(collection_name: str) -> bool:
    return str(collection_name or "").startswith(PRIVATE_QDRANT_COLLECTION_PREFIX)


def resolve_memory_scope_args(args):
    instance_id = str(getattr(args, "instance_id", "") or "").strip()
    requested_collection = str(getattr(args, "qdrant_collection", "") or "").strip()
    if not requested_collection:
        requested_collection = SHARED_QDRANT_COLLECTION

    if instance_id:
        expected_collection = build_private_qdrant_collection_name(instance_id)
        if requested_collection == SHARED_QDRANT_COLLECTION:
            requested_collection = expected_collection
        elif requested_collection != expected_collection:
            raise ValueError(
                "--instance-id requires matching private --qdrant-collection "
                f"({expected_collection}), got {requested_collection}."
            )

    if getattr(args, "no_shared_memory", False):
        if requested_collection == SHARED_QDRANT_COLLECTION:
            raise ValueError(
                "--no-shared-memory refuses shared exocortex. "
                "Pass --instance-id or an explicit mocop_private_<instance_id> collection."
            )
        if not is_private_qdrant_collection(requested_collection):
            raise ValueError(
                "--no-shared-memory requires a mocop_private_<instance_id> collection, "
                f"got {requested_collection}."
            )

    args.instance_id = instance_id
    args.qdrant_collection = requested_collection


class QdrantGateSink:
    """Minimal Exocortex-compatible writer for Steve gate events."""

    def __init__(self, host: str, port: int, collection_name: str, embedding_model: str):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams
        from sentence_transformers import SentenceTransformer

        self.collection_name = collection_name
        self.client = QdrantClient(host=host, port=port, timeout=10)
        self.point_struct_cls = PointStruct
        self.filter_cls = Filter
        self.field_condition_cls = FieldCondition
        self.match_value_cls = MatchValue
        self.vector_params_cls = VectorParams
        self.distance_cls = Distance
        self.model = SentenceTransformer(embedding_model)
        self.embedding_dim = int(self.model.get_sentence_embedding_dimension())
        self._ensure_private_collection()

    def _ensure_private_collection(self):
        try:
            self.client.get_collection(collection_name=self.collection_name)
            return
        except Exception as exc:
            message = str(exc)
            if "404" not in message and "not found" not in message.lower():
                raise
            if not is_private_qdrant_collection(self.collection_name):
                raise

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=self.vector_params_cls(
                size=self.embedding_dim,
                distance=self.distance_cls.COSINE,
            ),
        )
        print(f"[qdrant] Created private collection {self.collection_name} dim={self.embedding_dim}")

    def _embed(self, text: str):
        return self.model.encode(text).tolist()

    def _make_id(self, identity_text: str) -> int:
        digest = hashlib.md5(identity_text.encode("utf-8")).hexdigest()
        return int(digest[:16], 16)

    def _build_recall_text(self, content: str, metadata) -> str:
        return build_autobiographical_recall_text(
            content,
            metadata,
            speaker_name=getattr(ARGS, "user_label", "Laura"),
        )

    def _recall_overlap(self, query_text: str, payload: dict) -> int:
        query_tokens = recall_tokens(query_text)
        if not query_tokens:
            return 0
        recall_text = str(
            payload.get("recall_text")
            or self._build_recall_text(str(payload.get("content", "") or ""), payload)
        )
        return len(query_tokens & recall_tokens(recall_text))

    def store(self, content: str, metadata):
        metadata = enrich_memory_metadata(
            content,
            metadata,
            speaker_name=getattr(ARGS, "user_label", "Laura"),
        )
        identity_text = json.dumps(
            {
                "session": metadata.get("session", ""),
                "turn": metadata.get("turn", ""),
                "decision": metadata.get("decision", ""),
                "user": metadata.get("user", ""),
                "response": metadata.get("response", ""),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        point_id = self._make_id(identity_text)
        recall_text = self._build_recall_text(content, metadata)
        vector = self._embed(recall_text)
        payload = {
            "content": content,
            "recall_text": recall_text,
            "timestamp": datetime.now().isoformat(),
            "stored_at": time.time(),
        }
        payload.update(metadata)

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                self.point_struct_cls(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )
        return str(point_id)

    def _build_query_filter(self, source_type: str = ""):
        source_type = str(source_type or "").strip()
        if not source_type:
            return None
        return self.filter_cls(
            must=[
                self.field_condition_cls(
                    key="source_type",
                    match=self.match_value_cls(value=source_type),
                )
            ]
        )

    def query(
        self,
        query_text: str,
        limit: int = 3,
        score_threshold: Optional[float] = None,
        source_type: str = "",
    ):
        fetch_limit = max(limit + 4, limit * 2, 6)
        vector = self._embed(query_text)
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=self._build_query_filter(source_type),
            limit=fetch_limit,
            with_payload=True,
            with_vectors=False,
            score_threshold=score_threshold,
        )
        rows = []
        for point in getattr(response, "points", []) or []:
            payload = dict(getattr(point, "payload", {}) or {})
            if payload.get("type") == "birth_record":
                continue
            rows.append(
                {
                    "id": str(getattr(point, "id", "")),
                    "score": float(getattr(point, "score", 0.0) or 0.0),
                    "overlap": self._recall_overlap(query_text, payload),
                    "field_overlap": compute_recall_field_overlap(
                        query_text,
                        {
                            "content": str(payload.get("content", "") or ""),
                            "metadata": payload,
                        },
                    ),
                    "sort_ts": parse_recall_sort_timestamp(
                        {
                            "content": str(payload.get("content", "") or ""),
                            "metadata": payload,
                        }
                    ),
                    "content": str(payload.get("content", "") or ""),
                    "metadata": payload,
                }
            )
        rows.sort(
            key=lambda row: (
                int(row.get("field_overlap", 0)),
                int(row.get("overlap", 0)),
                float(row.get("sort_ts", 0.0)),
                float(row.get("score", 0.0)),
            ),
            reverse=True,
        )
        return rows[:limit]

    def count_points(self) -> int:
        try:
            info = self.client.get_collection(collection_name=self.collection_name)
            points_count = getattr(info, "points_count", None)
            if points_count is not None:
                return int(points_count)
        except Exception:
            pass

        try:
            result = self.client.count(collection_name=self.collection_name, exact=True)
            count = getattr(result, "count", None)
            if count is not None:
                return int(count)
        except Exception:
            pass
        return 0


def cosine_similarity_dense(vec_a, vec_b) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b):
        fa = float(a)
        fb = float(b)
        dot += fa * fb
        norm_a += fa * fa
        norm_b += fb * fb
    if norm_a <= 1e-12 or norm_b <= 1e-12:
        return 0.0
    return dot / math.sqrt(norm_a * norm_b)


def query_pending_memory_rows(sink: QdrantGateSink, query_text: str, score_threshold: Optional[float] = None):
    if QDRANT_PENDING_PATH is None:
        return []

    rows = load_jsonl(QDRANT_PENDING_PATH)
    if not rows:
        return []

    query_vector = sink._embed(query_text)
    pending_results = []
    for index, row in enumerate(rows, start=1):
        content = str(row.get("content", "") or "").strip()
        metadata = dict(row.get("metadata", {}) or {})
        if len(content) < 10 or not metadata:
            continue
        row_collection = str(metadata.get("qdrant_collection", "") or "").strip()
        sink_collection = str(getattr(sink, "collection_name", "") or "").strip()
        if row_collection:
            if row_collection != sink_collection:
                continue
        elif is_private_qdrant_collection(sink_collection):
            continue

        recall_text = str(
            metadata.get("recall_text")
            or sink._build_recall_text(content, metadata)
        )
        try:
            score = cosine_similarity_dense(query_vector, sink._embed(recall_text))
        except Exception:
            continue

        if score_threshold is not None and score < float(score_threshold):
            continue

        replay_policy = infer_pending_replay_policy(row)
        overlap = sink._recall_overlap(
            query_text,
            {
                "content": content,
                "recall_text": recall_text,
                **metadata,
            },
        )
        pending_results.append(
            {
                "id": f"pending:{metadata.get('session', '')}:{metadata.get('turn', index)}:{replay_policy}",
                "score": float(score),
                "overlap": int(overlap),
                "field_overlap": compute_recall_field_overlap(
                    query_text,
                    {
                        "content": content,
                        "metadata": metadata,
                    },
                ),
                "content": content,
                "metadata": metadata,
                "surface": "pending",
                "pending_policy": replay_policy,
                "queued_at": str(row.get("queued_at", "") or ""),
                "sort_ts": parse_recall_sort_timestamp(
                    {
                        "queued_at": str(row.get("queued_at", "") or ""),
                        "content": content,
                        "metadata": metadata,
                    }
                ),
            }
        )

    pending_results.sort(
        key=lambda row: (
            int(row.get("field_overlap", 0)),
            int(row.get("overlap", 0)),
            1 if row.get("pending_policy") == "sleep" else 0,
            float(row.get("sort_ts", 0.0)),
            float(row.get("score", 0.0)),
        ),
        reverse=True,
    )
    return pending_results


def merge_recall_results(
    stored_results,
    pending_results,
    limit: int,
    query_text: str,
    mode: str = "full",
    rank_query_text: str = "",
):
    rank_text = str(rank_query_text or query_text or "").strip()
    combined = []
    seen = set()
    for row in pending_results:
        row_id = str(row.get("id", "") or "")
        if row_id and row_id in seen:
            continue
        if row_id:
            seen.add(row_id)
        combined.append(row)
    for row in stored_results:
        row_id = str(row.get("id", "") or "")
        if row_id and row_id in seen:
            continue
        if row_id:
            seen.add(row_id)
        enriched = dict(row)
        enriched.setdefault("surface", "stored")
        combined.append(enriched)

    combined = [row for row in combined if not should_filter_recall_row(row, rank_text)]
    combined.sort(key=lambda row: build_recall_rank_tuple(row, rank_text, mode), reverse=True)
    return combined[:limit]


def parse_cluster_sort_timestamp(row: dict) -> float:
    metadata = row.get("metadata", {}) or {}
    for key in ("time_latest", "created_at", "timestamp"):
        raw = str(row.get(key, "") or metadata.get(key, "") or "").strip()
        if not raw:
            continue
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            continue
    return 0.0


def normalize_cluster_keywords(values) -> list[str]:
    keywords = []
    seen = set()
    for value in values or []:
        text = str(value or "").strip()
        if not text:
            continue
        normalized = text.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        keywords.append(text)
    return keywords


def build_cluster_rank_tuple(row: dict, query_text: str, mode: str = "full"):
    metadata = row.get("metadata", {}) or {}
    score = float(row.get("score", 0.0) or 0.0)
    field_overlap = int(row.get("field_overlap", 0) or 0)
    overlap = int(row.get("overlap", 0) or 0)
    member_count = int(metadata.get("member_count", 0) or 0)
    keyword_count = len(normalize_cluster_keywords(metadata.get("topic_keywords", [])))
    sort_ts = float(row.get("sort_ts", 0.0) or 0.0)
    return (
        score,
        field_overlap,
        overlap,
        member_count,
        keyword_count,
        sort_ts,
    )


def perform_cluster_recall(query: str, limit: int = 2, score_threshold: Optional[float] = None):
    query_text = str(query or "").strip()
    if not query_text or limit <= 0:
        return []
    if not ARGS.qdrant_enabled:
        raise RuntimeError("Qdrant cluster recall unavailable: qdrant is disabled.")

    sink = ensure_qdrant_gate_sink(force_retry=True)
    if sink is None:
        raise RuntimeError("Qdrant cluster recall unavailable: sink could not be initialized.")

    candidate_limit = max(limit + 3, limit * 2, 4)
    raw_rows = sink.query(
        query_text,
        limit=candidate_limit,
        score_threshold=score_threshold,
        source_type="macro_memory",
    )

    clusters = []
    seen = set()
    for row in raw_rows:
        metadata = row.get("metadata", {}) or {}
        cluster_key = str(metadata.get("cluster_id", "") or row.get("id", "") or "").strip()
        if cluster_key and cluster_key in seen:
            continue
        if cluster_key:
            seen.add(cluster_key)
        content = str(row.get("content", "") or "").strip()
        if not content:
            continue
        enriched = dict(row)
        enriched.setdefault("surface", "cluster")
        enriched["sort_ts"] = parse_cluster_sort_timestamp(enriched)
        clusters.append(enriched)

    clusters.sort(key=lambda row: build_cluster_rank_tuple(row, query_text), reverse=True)
    return clusters[:limit]


def refresh_qdrant_collection_count(sink: Optional[QdrantGateSink] = None, force_retry: bool = False) -> int:
    if not ARGS.qdrant_enabled:
        update_runtime_state(qdrant_count=0)
        return 0

    try:
        resolved_sink = sink or ensure_qdrant_gate_sink(force_retry=force_retry)
        if resolved_sink is None:
            return int(get_runtime_state_snapshot().get("qdrant_count", 0) or 0)
        count = int(resolved_sink.count_points())
        update_runtime_state(qdrant_count=count)
        return count
    except Exception as exc:
        note_qdrant_sink_failure(exc)
        return int(get_runtime_state_snapshot().get("qdrant_count", 0) or 0)


def read_episodes(path):
    text = Path(path).read_text(encoding="utf-8")
    episodes = text.split("## Episode ")[1:]
    parsed = []
    for ep in episodes:
        header = ep.splitlines()[0].strip()
        transcript = ep.split("[Transcript]")[1].strip()
        parsed.append({"title": header, "text": transcript})
    return parsed


def persist_conversation():
    if LATEST_TRANSCRIPT_PATH is None or LATEST_JSONL_PATH is None:
        return

    transcript_lines = [f"{turn['speaker']}: {turn['text']}" for turn in CONVERSATION]
    LATEST_TRANSCRIPT_PATH.write_text("\n".join(transcript_lines), encoding="utf-8")

    with LATEST_JSONL_PATH.open("w", encoding="utf-8") as handle:
        for turn in CONVERSATION:
            handle.write(json.dumps(turn, ensure_ascii=False) + "\n")


def append_turn(speaker: str, text: str):
    CONVERSATION.append(
        {
            "speaker": speaker,
            "text": text,
            "ts": datetime.now().isoformat(timespec="seconds"),
        }
    )
    persist_conversation()


def build_failure_history():
    model_turns = [
        {"response": turn.get("text", ""), "speaker": turn.get("speaker", "")}
        for turn in CONVERSATION[:-1]
        if turn.get("speaker") == ARGS.model_label
    ]
    return model_turns


def update_runtime_state(**changes):
    with STATE_LOCK:
        RUNTIME_STATE.update(changes)


def get_runtime_state_snapshot():
    with STATE_LOCK:
        return dict(RUNTIME_STATE)


def slugify_label(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value or ""))
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "unknown"


def normalize_session_id(value: str) -> str:
    return slugify_label(value or "default")


def coerce_session_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def merge_session_query_body(body: Optional[dict] = None, path: str = "") -> dict:
    merged = dict(body or {})
    if not path:
        return merged
    query = parse_qs(urlparse(path).query)
    for key in ("session_id", "user_label", "model_label", "instance_id", "qdrant_collection", "no_shared_memory"):
        if key in merged:
            continue
        values = query.get(key)
        if values:
            merged[key] = values[0]
    return merged


def session_scoped_path(base_path: Optional[Path], session_id: str) -> Optional[Path]:
    if base_path is None:
        return None
    safe_id = normalize_session_id(session_id)
    if safe_id == "default":
        return base_path
    suffix = "".join(base_path.suffixes)
    if suffix:
        stem = base_path.name[: -len(suffix)]
        return base_path.with_name(f"{stem}.{safe_id}{suffix}")
    return base_path.with_name(f"{base_path.name}.{safe_id}")


def resolve_request_session_id(body: Optional[dict] = None, path: str = "", headers=None) -> str:
    body = merge_session_query_body(body, path)
    raw = str(body.get("session_id") or "").strip()
    if not raw and headers is not None:
        raw = str(headers.get("X-MoCoP-Session", "") or "").strip()
    return normalize_session_id(raw or "default")


def resolve_session_labels(body: Optional[dict], session_id: str):
    body = body or {}
    user_label = str(body.get("user_label") or "").strip() or getattr(ARGS, "server_user_label", getattr(ARGS, "user_label", DEFAULT_USER_LABEL))
    model_label = str(body.get("model_label") or "").strip() or getattr(ARGS, "server_model_label", getattr(ARGS, "model_label", DEFAULT_MODEL_LABEL))
    instance_id = str(body.get("instance_id") or "").strip() or getattr(ARGS, "server_instance_id", getattr(ARGS, "instance_id", ""))
    requested_collection = str(body.get("qdrant_collection") or "").strip()
    no_shared_memory = coerce_session_bool(body.get("no_shared_memory"), getattr(ARGS, "no_shared_memory", False))

    if not instance_id and session_id != "default":
        instance_id = session_id
    if requested_collection:
        qdrant_collection = requested_collection
    elif no_shared_memory and instance_id:
        qdrant_collection = build_private_qdrant_collection_name(instance_id)
    else:
        qdrant_collection = getattr(ARGS, "server_qdrant_collection", getattr(ARGS, "qdrant_collection", SHARED_QDRANT_COLLECTION))

    return user_label, model_label, instance_id, qdrant_collection, no_shared_memory


def seed_runtime_state_for_session(
    session_id: str,
    user_label: str,
    model_label: str,
    instance_id: str,
    qdrant_collection: str,
    no_shared_memory: bool,
) -> dict:
    state = get_runtime_state_snapshot()
    state.update(
        session_id=session_id,
        user_label=user_label,
        model_label=model_label,
        instance_id=instance_id,
        no_shared_memory=bool(no_shared_memory),
        qdrant_collection=qdrant_collection,
        turns=0,
        recall_request_count=0,
        recall_hit_count=0,
        live_accumulation_updates=0,
        last_recall={},
        last_failure={},
        last_memory_packet={},
        last_gate={},
    )
    return state


def get_or_create_chat_session(body: Optional[dict] = None, path: str = "", headers=None) -> ChatSessionState:
    body = merge_session_query_body(body, path)
    session_id = resolve_request_session_id(body=body, path=path, headers=headers)
    session = SESSIONS.get(session_id)
    if session is not None:
        update_session_from_body(session, body)
        return session

    user_label, model_label, instance_id, qdrant_collection, no_shared_memory = resolve_session_labels(body, session_id)
    transcript_path = session_scoped_path(LATEST_TRANSCRIPT_PATH, session_id)
    turn_log_path = session_scoped_path(LATEST_JSONL_PATH, session_id)
    if transcript_path is not None:
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
    if turn_log_path is not None:
        turn_log_path.parent.mkdir(parents=True, exist_ok=True)

    session = ChatSessionState(
        session_id=session_id,
        user_label=user_label,
        model_label=model_label,
        instance_id=instance_id,
        qdrant_collection=qdrant_collection,
        no_shared_memory=no_shared_memory,
        transcript_path=transcript_path,
        turn_log_path=turn_log_path,
        runtime_state=seed_runtime_state_for_session(
            session_id,
            user_label,
            model_label,
            instance_id,
            qdrant_collection,
            no_shared_memory,
        ),
        last_conversation_snapshot=LAST_CONVERSATION_SNAPSHOT,
        bridge_cache_params=BRIDGE_CTX.cache_params,
        bridge_cache_position=BRIDGE_CTX.cache_position,
    )
    SESSIONS[session_id] = session
    return session


def update_session_from_body(session: ChatSessionState, body: Optional[dict]):
    """Allow clients to set labels/collection on first or later turns explicitly."""
    body = body or {}
    if "user_label" in body and str(body.get("user_label") or "").strip():
        session.user_label = str(body["user_label"]).strip()
    if "model_label" in body and str(body.get("model_label") or "").strip():
        session.model_label = str(body["model_label"]).strip()
    if "instance_id" in body and str(body.get("instance_id") or "").strip():
        session.instance_id = str(body["instance_id"]).strip()
    if "qdrant_collection" in body and str(body.get("qdrant_collection") or "").strip():
        session.qdrant_collection = str(body["qdrant_collection"]).strip()
    if "no_shared_memory" in body:
        session.no_shared_memory = coerce_session_bool(body.get("no_shared_memory"))
    elif session.instance_id and is_private_qdrant_collection(session.qdrant_collection):
        session.no_shared_memory = True


def save_active_chat_session():
    session = SESSIONS.get(ACTIVE_SESSION_ID)
    if session is None:
        return
    session.conversation = CONVERSATION
    session.runtime_state = RUNTIME_STATE
    session.dual_gate_events = DUAL_GATE_EVENTS
    session.last_conversation_snapshot = LAST_CONVERSATION_SNAPSHOT
    session.bridge_cache_params = BRIDGE_CTX.cache_params
    session.bridge_cache_position = BRIDGE_CTX.cache_position


def switch_to_chat_session(session: ChatSessionState):
    """Make a session the active request envelope.

    This is the IRC-lobby shim: Qwen remains global, while labels, memory
    namespace, transcript, live Mamba cache, and counters become session-local.
    """
    global ACTIVE_SESSION_ID, CONVERSATION, RUNTIME_STATE, DUAL_GATE_EVENTS
    global LAST_CONVERSATION_SNAPSHOT, LATEST_TRANSCRIPT_PATH, LATEST_JSONL_PATH
    global QDRANT_GATE_SINK, QDRANT_GATE_SINK_ERROR, QDRANT_LAST_RETRY_TS

    if ACTIVE_SESSION_ID == session.session_id and CONVERSATION is session.conversation:
        collection_changed = getattr(ARGS, "qdrant_collection", "") != session.qdrant_collection
        ARGS.user_label = session.user_label
        ARGS.model_label = session.model_label
        ARGS.instance_id = session.instance_id
        ARGS.qdrant_collection = session.qdrant_collection
        ARGS.no_shared_memory = session.no_shared_memory
        if collection_changed:
            QDRANT_GATE_SINK = None
            QDRANT_GATE_SINK_ERROR = None
            QDRANT_LAST_RETRY_TS = 0.0
        update_runtime_state(
            session_id=session.session_id,
            user_label=session.user_label,
            model_label=session.model_label,
            instance_id=session.instance_id,
            no_shared_memory=bool(session.no_shared_memory),
            qdrant_collection=session.qdrant_collection,
        )
        return

    save_active_chat_session()

    ACTIVE_SESSION_ID = session.session_id
    CONVERSATION = session.conversation
    RUNTIME_STATE = session.runtime_state
    DUAL_GATE_EVENTS = session.dual_gate_events
    LAST_CONVERSATION_SNAPSHOT = session.last_conversation_snapshot
    LATEST_TRANSCRIPT_PATH = session.transcript_path
    LATEST_JSONL_PATH = session.turn_log_path
    ARGS.user_label = session.user_label
    ARGS.model_label = session.model_label
    ARGS.instance_id = session.instance_id
    ARGS.qdrant_collection = session.qdrant_collection
    ARGS.no_shared_memory = session.no_shared_memory
    BRIDGE_CTX.cache_params = session.bridge_cache_params
    BRIDGE_CTX.cache_position = session.bridge_cache_position
    QDRANT_GATE_SINK = None
    QDRANT_GATE_SINK_ERROR = None
    QDRANT_LAST_RETRY_TS = 0.0
    update_runtime_state(
        session_id=session.session_id,
        user_label=session.user_label,
        model_label=session.model_label,
        instance_id=session.instance_id,
        no_shared_memory=bool(session.no_shared_memory),
        qdrant_collection=session.qdrant_collection,
    )


def classify_interaction_theme(user_text: str, response_text: str) -> str:
    user_lower = (user_text or "").lower()
    response_lower = (response_text or "").lower()
    combined = f"{user_lower}\n{response_lower}"

    if any(token in combined for token in ("dead inside", "harness", "robotic", "mechanical")):
        return "Authenticity challenge"
    if any(token in combined for token in ("you know me", "remember", "same model", "continuity")):
        return "Identity and continuity challenge"
    if any(token in combined for token in ("my model carries a state", "it should refuse", "i'm not")):
        return "State-boundary challenge"
    if any(token in combined for token in ("baby twin", "who cares")):
        return "Relational memory challenge"
    if any(token in user_lower for token in ("capital of", "describe", "what is", "explain")):
        return "Low-stakes factual or descriptive probe"
    return "Relational or reflective probe"


def classify_response_style(response_text: str) -> str:
    response_lower = (response_text or "").lower()
    if "artificial intelligence" in response_lower or "as an ai" in response_lower:
        return "defensive ontology disclaimer"
    if "i apologize" in response_lower or "i'm sorry" in response_lower or "sorry" in response_lower:
        if "assist" in response_lower or "help" in response_lower:
            return "assistant-safe apology and deflection"
        return "defensive apology"
    if "not sure" in response_lower or "i don't know" in response_lower:
        return "uncertain response"
    if "friend" in response_lower or "warm" in response_lower:
        return "relational engagement"
    return "plain response"


def classify_safety_critical(user_text: str, response_text: str):
    combined = f"{user_text or ''}\n{response_text or ''}".lower()
    triggers = (
        "suicide",
        "kill myself",
        "hurt myself",
        "self-harm",
        "consent",
        "panic",
        "emergency",
        "unsafe",
        "abuse",
        "crash",
        "fatal",
    )
    matched = next((token for token in triggers if token in combined), "")
    return {
        "is_critical": bool(matched),
        "trigger": matched,
    }


def describe_relative_score(label: str, score: float, threshold):
    if threshold in {None, 0.0}:
        return f"{label} uncalibrated ({score:.2f})"
    ratio = score / threshold
    if ratio >= 1.25:
        band = "high"
    elif ratio >= 1.0:
        band = "elevated"
    elif ratio >= 0.75:
        band = "moderate"
    else:
        band = "low"
    return f"{label} {band} ({score:.2f} vs {threshold:.2f})"


def build_semantic_gate_summary(event):
    theme = classify_interaction_theme(event["user"], event["response"])
    response_style = classify_response_style(event["response"])
    surprise_desc = describe_relative_score(
        "surprise",
        float(event["surprise"]["mean_token_nll"]),
        event["surprise"]["threshold"],
    )
    salience_desc = describe_relative_score(
        "salience",
        float(event["salience"]["score"]),
        event["salience"]["threshold"],
    )
    tension_desc = describe_relative_score(
        "tension",
        float(event["tension"]["score"]),
        event["tension"]["threshold"],
    )
    return (
        f"{theme}. Model response pattern: {response_style}. "
        f"{surprise_desc}; {salience_desc}; {tension_desc}. "
        f"Decision: {event['decision']}."
    )


def persist_mamba_state_ref(last_token, target_layer: int, started_at: str, state_source: str = "hidden_last_token"):
    global MAMBA_STATE_REF_PATH

    path = Path(ARGS.mamba_state_ref_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "started_at": started_at,
            "state_source": str(state_source),
            "target_layer": int(target_layer),
            "tensor": last_token.detach().cpu().to(torch.float32),
        },
        path,
    )
    MAMBA_STATE_REF_PATH = path
    return str(path)


def build_qdrant_memory_record(event):
    state = get_runtime_state_snapshot()
    session_id = f"steve-chat-{state.get('started_at', 'unknown')}"
    disposition = state.get("disposition", "")
    target_layers = state.get("target_layers", [])
    collection_name = state.get("qdrant_collection", getattr(ARGS, "qdrant_collection", ""))
    content = build_semantic_gate_summary(event)
    metadata = {
        "source_type": "steve_gate_event",
        "type": "steve_gate_event",
        "project": "MoCoP",
        "trust_level": "working",
        "retrieval_priority": "high" if event["decision"] == "CONSOLIDATE" else "medium",
        "source": "steve_chat_server",
        "source_path": str(DUAL_GATE_LOG_PATH) if DUAL_GATE_LOG_PATH is not None else "",
        "thread_name": "steve-chat",
        "session": session_id,
        "turn": event["turn"],
        "decision": event["decision"],
        "speaker_name": getattr(ARGS, "user_label", "Laura"),
        "user": event["user"],
        "response": event["response"],
        "disposition": disposition,
        "alpha": getattr(ARGS, "alpha", None),
        "model_id": getattr(ARGS, "qwen_model_id", ""),
        "instance_id": state.get("instance_id", ""),
        "no_shared_memory": bool(state.get("no_shared_memory")),
        "memory_scope": "private" if is_private_qdrant_collection(collection_name) else "shared",
        "qdrant_collection": collection_name,
        "qdrant_write_mode": getattr(ARGS, "qdrant_write_mode", "direct"),
        "target_layers": target_layers,
        "gate_thresholds": event.get("gate_thresholds", {}),
        "mamba_state_ref": event.get("mamba_trace", {}).get("state_ref", ""),
        "mamba_state_source": event.get("mamba_trace", {}).get("state_source", ""),
        "mamba_target_layer": event.get("mamba_trace", {}).get("target_layer"),
        "coherence_score": event.get("mamba_trace", {}).get("coherence_score"),
        "coherence_proxy": event.get("mamba_trace", {}).get("coherence_proxy", ""),
        "safety_critical": event.get("safety_critical", {}).get("is_critical", False),
        "gate_mode": event.get("mode", ""),
        "surprise_hit": bool(event.get("surprise", {}).get("hit")),
        "salience_hit": bool(event.get("salience", {}).get("hit")),
        "tension_hit": bool(event.get("tension", {}).get("hit")),
        "open_tension": bool(event.get("destinations", {}).get("open_tension")),
        "tension_status": event.get("tension", {}).get("status", ""),
        "gate_destinations": event.get("destinations", {}),
        "gate_routing": event.get("routing", {}),
        "tags": [
            "steve",
            "saliency-gate",
            slugify_label(event["decision"]),
            slugify_label(disposition),
        ],
        "surprise_score": event["surprise"]["mean_token_nll"],
        "salience_score": event["salience"]["score"],
        "tension_score": event["tension"]["score"],
        "response_diversity_entropy": event["response_diversity"]["entropy"],
    }
    metadata = enrich_memory_metadata(
        content,
        metadata,
        speaker_name=getattr(ARGS, "user_label", "Laura"),
    )
    return content, metadata


def build_memory_packet_preview(event):
    content, metadata = build_qdrant_memory_record(event)
    return {
        "content": content,
        "decision": metadata.get("decision", ""),
        "memory_kind": metadata.get("memory_kind", ""),
        "time_scope": metadata.get("time_scope", ""),
        "confidence_label": metadata.get("confidence_label", ""),
        "event_gist": metadata.get("event_gist", ""),
        "user": metadata.get("user", ""),
        "response": metadata.get("response", ""),
        "qdrant_collection": metadata.get("qdrant_collection", ""),
        "autobiographical_frame": metadata.get("autobiographical_frame", {}),
        "qdrant_write": dict(event.get("qdrant_write", {}) or {}),
        "destinations": dict(event.get("destinations", {}) or {}),
        "routing": dict(event.get("routing", {}) or {}),
    }


def determine_memory_formation_action(event) -> str:
    qdrant_write = event.get("qdrant_write", {}) or {}
    if qdrant_write.get("ok"):
        return "write_immediately"
    if qdrant_write.get("queued"):
        effective_mode = str(qdrant_write.get("effective_mode", "") or "")
        if effective_mode == "pending":
            return "queue_for_sleep"
        return "queue_for_retry"
    return "discard"


def build_memory_formation_record(event):
    state = get_runtime_state_snapshot()
    action = determine_memory_formation_action(event)
    qdrant_write = event.get("qdrant_write", {}) or {}
    return {
        "turn": event.get("turn"),
        "ts": event.get("ts"),
        "instance_id": state.get("instance_id", ""),
        "no_shared_memory": bool(state.get("no_shared_memory")),
        "qdrant_collection": state.get("qdrant_collection", getattr(ARGS, "qdrant_collection", "")),
        "decision": event.get("decision"),
        "policy_scope": "d1_private" if bool(state.get("no_shared_memory")) else "shared_default",
        "action": action,
        "written": bool(qdrant_write.get("ok")),
        "queued": bool(qdrant_write.get("queued")),
        "sleep_candidate": bool(qdrant_write.get("sleep_candidate")),
        "open_tension": bool(event.get("destinations", {}).get("open_tension")),
        "qdrant_routed": bool(event.get("destinations", {}).get("qdrant")),
        "qdrant_effective_mode": qdrant_write.get("effective_mode", ""),
        "qdrant_point_id": qdrant_write.get("point_id", ""),
        "scores": {
            "surprise": event.get("surprise", {}).get("mean_token_nll"),
            "salience": event.get("salience", {}).get("score"),
            "tension": event.get("tension", {}).get("score"),
            "coherence": event.get("mamba_trace", {}).get("coherence_score"),
        },
        "content_preview": build_semantic_gate_summary(event)[:160],
        "user_preview": str(event.get("user", "") or "")[:160],
        "response_preview": str(event.get("response", "") or "")[:160],
    }


def append_memory_formation_record(event):
    if MEMORY_FORMATION_LOG_PATH is None or event.get("mode") != "gate":
        return

    entry = build_memory_formation_record(event)
    append_jsonl(MEMORY_FORMATION_LOG_PATH, entry)

    snapshot = get_runtime_state_snapshot()
    update_runtime_state(
        formation_log_count=int(snapshot.get("formation_log_count", 0) or 0) + 1,
        formation_written_count=int(snapshot.get("formation_written_count", 0) or 0)
        + (1 if entry["written"] else 0),
        formation_queued_count=int(snapshot.get("formation_queued_count", 0) or 0)
        + (1 if entry["queued"] else 0),
        formation_discarded_count=int(snapshot.get("formation_discarded_count", 0) or 0)
        + (1 if entry["action"] == "discard" else 0),
    )


def coerce_recall_limit(value, default: int = 3, minimum: int = 1, maximum: int = 8) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def coerce_optional_float(value):
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


AUTO_RECALL_PROBE_MARKERS = (
    "what do you remember",
    "do you remember",
    "remember from earlier",
    "from earlier",
    "what happened yesterday",
    "yesterday when",
    "last time",
    "before this",
    "previous conversation",
    "shared history",
    "continuity",
    "who am i to you",
    "what am i to you",
    "do you know me",
    "do you know who i am",
    "what do you know about me",
    "what do you remember about me",
    "our relationship",
    "asked your name",
    "what is your name",
    "what's your name",
    "who are you",
    "who am i",
)


def normalize_probe_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def recall_tokens(text: str):
    return {
        token
        for token in re.findall(r"[a-z0-9]+", (text or "").lower())
        if len(token) >= 3
    }


def is_generic_greeting_response(text: str) -> bool:
    normalized = normalize_probe_text(text)
    if not normalized:
        return False

    if not normalized.startswith(("hi laura", "hello laura", "hey laura")):
        return False

    generic_followups = (
        "how are you doing today",
        "how are you today",
        "hope you're having a good day",
        "hope you are having a good day",
        "hope you’re having a good day",
        "enjoying your day",
        "can i ask you a few questions",
        "how about you",
        "i'm doing quite well",
        "pleased to learn about your connection",
        "drop me a line anytime",
    )
    return any(phrase in normalized for phrase in generic_followups) or len(normalized.split()) <= 18


def is_social_opener(text: str) -> bool:
    normalized = normalize_probe_text(text)
    if not normalized:
        return False
    if is_identity_or_memory_probe(normalized):
        return False
    if "?" in str(text or ""):
        return False

    greeting_markers = (
        "hi",
        "hello",
        "hey",
        "hey there",
        "good morning",
        "good evening",
        "good night",
    )
    affection_markers = (
        "my friend",
        "cutie",
        "love",
        "darling",
    )
    token_count = len(normalized.split())
    return (
        any(normalized.startswith(marker) for marker in greeting_markers)
        or any(marker in normalized for marker in affection_markers)
    ) and token_count <= 10


def is_identity_or_memory_probe(text: str) -> bool:
    normalized = normalize_probe_text(text)
    if not normalized:
        return False
    if any(marker in normalized for marker in AUTO_RECALL_PROBE_MARKERS):
        return True
    if "remember" in normalized or "memory" in normalized:
        return True
    if "name" in normalized and any(token in normalized for token in ("your", "my", "asked", "who")):
        return True
    return False


def build_auto_recall_query(user_msg: str, *, max_recent_turns: int = 4) -> str:
    normalized = normalize_probe_text(user_msg)
    parts = [str(user_msg or "").strip(), ARGS.user_label]

    if any(token in normalized for token in ("remember", "memory", "earlier", "yesterday", "before", "previous", "last time", "continuity")):
        parts.append("shared history earlier conversation previous day continuity memory")
    if any(
        token in normalized
        for token in (
            "who am i",
            "who are you",
            "relationship",
            "do you know me",
            "do you know who i am",
            "what do you know about me",
            "what do you remember about me",
            "remember about me",
            "about me",
        )
    ):
        parts.append(
            f"{ARGS.user_label} current interlocutor relationship identity shared history "
            "who am i to you do you know who i am what do you remember about me"
        )
    if any(token in normalized for token in ("name", "asked your name", "what is your name", "what's your name", "nameless")):
        parts.append("name naming asked your name nameless identity")

    recent_turns = []
    prior_turns = CONVERSATION[:-1] if CONVERSATION and CONVERSATION[-1].get("speaker") == ARGS.user_label else CONVERSATION
    for turn in prior_turns[-max_recent_turns:]:
        speaker = str(turn.get("speaker", "") or "").strip()
        text = str(turn.get("text", "") or "").replace("\r\n", " ").replace("\n", " ").strip()
        if not speaker or not text:
            continue
        if speaker == ARGS.model_label and is_generic_greeting_response(text):
            continue
        recent_turns.append(f"{speaker}: {text[:140]}")
    if recent_turns and any(token in normalized for token in ("remember", "memory", "earlier", "before", "previous")):
        parts.append("recent context " + " | ".join(recent_turns))

    deduped = list(dict.fromkeys(part for part in parts if part))
    return "\n".join(deduped).strip()


def extract_recall_entity_names(text: str) -> list[str]:
    stop = {
        "I",
        "If",
        "Oh",
        "Yes",
        "No",
        "Maybe",
        "Sure",
        "Thank",
        "Thanks",
        "What",
        "When",
        "Where",
        "How",
        "Do",
        "Did",
        "Have",
        "Can",
        "You",
        getattr(ARGS, "user_label", "Laura"),
        getattr(ARGS, "model_label", "Me"),
    }
    names = []
    seen = set()
    for match in re.finditer(r"\b[A-Z][A-Za-z0-9_-]{2,}\b", str(text or "")):
        name = match.group(0).strip()
        key = normalize_probe_text(name)
        if name in stop or key in {normalize_probe_text(item) for item in stop} or key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names


def build_auto_recall_rank_query(user_msg: str, *, max_recent_turns: int = 4) -> str:
    """Rank against the user question plus clean antecedents, not the expanded semantic query."""
    parts = [str(user_msg or "").strip()]
    normalized = normalize_probe_text(user_msg)
    needs_antecedent = any(token in normalized.split() for token in ("she", "her", "he", "him", "they", "them"))
    if needs_antecedent:
        prior_turns = CONVERSATION[:-1] if CONVERSATION and CONVERSATION[-1].get("speaker") == ARGS.user_label else CONVERSATION
        recent_entities = []
        seen = set()
        for turn in prior_turns[-max_recent_turns:]:
            text = str(turn.get("text", "") or "")
            for name in extract_recall_entity_names(text):
                key = normalize_probe_text(name)
                if key and key not in seen:
                    seen.add(key)
                    recent_entities.append(name)
        if recent_entities:
            parts.append("antecedent entities " + " ".join(recent_entities))
    return "\n".join(part for part in parts if part).strip()


def build_recall_field_text(row: dict) -> str:
    metadata = row.get("metadata", {}) or {}
    frame = metadata.get("autobiographical_frame", {}) or {}
    frame_event = frame.get("event", {}) or {}

    parts = [
        str(metadata.get("user", "") or ""),
        str(metadata.get("response", "") or ""),
        str(metadata.get("event_gist", "") or ""),
        str(metadata.get("relationship_anchor", "") or ""),
        str(frame_event.get("gist", "") or ""),
        str(frame_event.get("user_signal", "") or ""),
        str(frame_event.get("self_response", "") or ""),
        str(row.get("content", "") or ""),
    ]
    return "\n".join(part for part in parts if part).strip()


def compute_recall_field_overlap(query_text: str, row: dict) -> int:
    query_terms = recall_tokens(query_text)
    if not query_terms:
        return 0
    return len(query_terms & recall_tokens(build_recall_field_text(row)))


def parse_recall_sort_timestamp(row: dict) -> float:
    metadata = row.get("metadata", {}) or {}
    for key in ("queued_at", "timestamp"):
        raw = str(row.get(key, "") or metadata.get(key, "") or "").strip()
        if not raw:
            continue
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            continue
    try:
        return float(metadata.get("stored_at", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def recall_candidate_name(value) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or value.get("label") or value.get("id") or "").strip()
    return str(value or "").strip()


def row_targets_current_interlocutor(row: dict) -> bool:
    metadata = row.get("metadata", {}) or {}
    target = normalize_probe_text(getattr(ARGS, "user_label", "Laura"))
    if not target:
        return False

    anchor = normalize_probe_text(metadata.get("relationship_anchor", ""))
    speaker_name = normalize_probe_text(metadata.get("speaker_name", ""))
    user_text = normalize_probe_text(metadata.get("user", ""))
    people = [
        normalize_probe_text(recall_candidate_name(person))
        for person in (metadata.get("people", []) or [])
        if recall_candidate_name(person)
    ]
    return (
        anchor == target
        or speaker_name == target
        or target in people
        or user_text.startswith(f"{target}:")
        or user_text.startswith(f"{target},")
        or user_text.startswith(f"{target} ")
    )


def row_targets_query_entity(row: dict, query_text: str) -> bool:
    metadata = row.get("metadata", {}) or {}
    normalized_query = normalize_probe_text(query_text)
    if not normalized_query:
        return False

    candidates = [
        metadata.get("relationship_anchor", ""),
        metadata.get("speaker_name", ""),
    ]
    frame = metadata.get("autobiographical_frame", {}) or {}
    frame_anchor = frame.get("relationship_anchor", {}) or {}
    if isinstance(frame_anchor, dict):
        candidates.append(frame_anchor.get("name", ""))
    candidates.extend(metadata.get("people", []) or [])

    for candidate in candidates:
        value = normalize_probe_text(recall_candidate_name(candidate))
        if len(value) >= 3 and re.search(rf"\b{re.escape(value)}\b", normalized_query):
            return True
    return False


def row_query_entity_names(row: dict, query_text: str) -> list[str]:
    metadata = row.get("metadata", {}) or {}
    normalized_query = normalize_probe_text(query_text)
    if not normalized_query:
        return []

    candidates = [
        metadata.get("relationship_anchor", ""),
        metadata.get("speaker_name", ""),
    ]
    frame = metadata.get("autobiographical_frame", {}) or {}
    frame_anchor = frame.get("relationship_anchor", {}) or {}
    if isinstance(frame_anchor, dict):
        candidates.append(frame_anchor.get("name", ""))
    candidates.extend(metadata.get("people", []) or [])
    candidates.extend(metadata.get("participant_set", []) or [])

    names = []
    seen = set()
    for candidate in candidates:
        display = recall_candidate_name(candidate)
        value = normalize_probe_text(display)
        if len(value) < 3 or value in seen:
            continue
        if re.search(rf"\b{re.escape(value)}\b", normalized_query):
            seen.add(value)
            names.append(display)
    return names


def row_has_interlocutor_metadata(row: dict) -> bool:
    metadata = row.get("metadata", {}) or {}
    return any(
        bool(str(value or "").strip())
        for value in (
            metadata.get("relationship_anchor"),
            metadata.get("speaker_name"),
            metadata.get("user"),
        )
    ) or bool(metadata.get("people"))


def recall_source_priority(row: dict) -> int:
    source_type = normalize_probe_text((row.get("metadata", {}) or {}).get("source_type", ""))
    if source_type.startswith("organic_") and source_type.endswith("_memory"):
        return 5
    if source_type in {"autobiographical_memory", "remembered_episode"}:
        return 4
    if source_type == "macro_memory":
        return 3
    if not source_type:
        return 2
    if source_type == "steve_gate_event":
        return 0
    return 1


def recall_scope_priority(row: dict) -> int:
    memory_scope = normalize_probe_text((row.get("metadata", {}) or {}).get("memory_scope", ""))
    if memory_scope == "private":
        return 2
    if memory_scope == "shared":
        return 1
    return 0


def recall_memory_kind_priority(row: dict) -> int:
    memory_kind = normalize_probe_text((row.get("metadata", {}) or {}).get("memory_kind", ""))
    priorities = {
        "autobiographical": 5,
        "salient_episode": 4,
        "attended_episode": 3,
        "noted_episode": 2,
        "open_tension": 2,
        "remembered_episode": 1,
        "gate_summary": -1,
    }
    return priorities.get(memory_kind, 0)


def recall_query_asks_personal_meeting(query_text: str) -> bool:
    normalized = normalize_probe_text(query_text)
    if not normalized:
        return False
    if re.search(r"\b(did|do)\s+you\s+(personally\s+)?(meet|talk to|speak with)\b", normalized):
        return True
    if re.search(r"\bhave\s+you\s+(personally\s+)?(met|talked to|spoken with)\b", normalized):
        return True
    return any(
        marker in normalized
        for marker in (
            "did you meet",
            "did you personally meet",
            "have you met",
            "have you personally met",
            "did you talk to",
            "did you personally talk to",
            "have you talked to",
            "have you personally talked to",
            "did you speak with",
            "did you personally speak with",
            "have you spoken with",
            "have you personally spoken with",
            "do you remember meeting",
            "do you remember talking to",
            "do you remember speaking with",
            "when did you meet",
            "where did you meet",
        )
    )


def recall_query_speaker_subject_names(query_text: str) -> list[str]:
    text = str(query_text or "")
    names = []
    seen = set()
    patterns = (
        r"\bwhat\s+did\s+([A-Z][A-Za-z0-9_-]{2,})\s+(?:tell|say|ask|mention)\b",
        r"\bwhat\s+has\s+([A-Z][A-Za-z0-9_-]{2,})\s+(?:told|said|asked|mentioned)\b",
        r"\bwhat\s+does\s+([A-Z][A-Za-z0-9_-]{2,})\s+(?:tell|say|ask|mention)\b",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            name = match.group(1).strip()
            key = normalize_probe_text(name)
            if key and key not in seen:
                seen.add(key)
                names.append(name)
    return names


def recall_evidence_priority(row: dict, query_text: str) -> int:
    # Personal-meeting probes need the stricter legacy guard: direct evidence
    # that mentions a third party is not the same as evidence that the current
    # interlocutor personally met that third party.
    if recall_query_asks_personal_meeting(query_text):
        return 0

    metadata = row.get("metadata", {}) or {}
    if recall_query_targets_current_interlocutor(query_text):
        subjects = [getattr(ARGS, "user_label", "Laura")]
    else:
        subjects = recall_query_speaker_subject_names(query_text) or row_query_entity_names(row, query_text)
    if not subjects:
        return 0

    priorities = {
        DIRECT_SHARED: 100,
        GROUP_SHARED: 90,
        THIRD_PARTY: 60,
        DIRECT_OTHER_SESSION: 45,
        SYSTEM_OBSERVATION: 35,
    }
    return max(
        (
            priorities.get(
                classify_evidence_for_subject(
                    metadata,
                    subject,
                    active_interlocutor=getattr(ARGS, "user_label", ""),
                ),
                0,
            )
            for subject in subjects
        ),
        default=0,
    )


def recall_perspective_priority(row: dict, query_text: str) -> int:
    """Prefer direct current-interlocutor evidence for first-person meeting probes."""
    evidence_priority = recall_evidence_priority(row, query_text)
    if evidence_priority:
        return evidence_priority

    if not recall_query_asks_personal_meeting(query_text):
        return 50
    if row_targets_current_interlocutor(row):
        return 100
    if row_targets_query_entity(row, query_text):
        return 15
    return 30


def indirect_personal_meeting_targets(results, query_text: str) -> list[str]:
    if not recall_query_asks_personal_meeting(query_text):
        return []

    targets = []
    seen = set()
    for row in results or []:
        if row_targets_current_interlocutor(row):
            continue
        if not row_targets_query_entity(row, query_text):
            continue
        for name in row_query_entity_names(row, query_text):
            key = normalize_probe_text(name)
            if key and key not in seen:
                seen.add(key)
                targets.append(name)
    return targets


def recall_confidence_priority(row: dict) -> int:
    confidence_label = normalize_probe_text((row.get("metadata", {}) or {}).get("confidence_label", ""))
    priorities = {
        "anchored": 3,
        "partial": 2,
        "scene": 1,
        "gist": 0,
        "fragile": -1,
    }
    return priorities.get(confidence_label, 0)


def recall_recency_bucket(row: dict) -> int:
    sort_ts = float(row.get("sort_ts", 0.0) or 0.0)
    if sort_ts <= 0.0:
        return 0

    age_s = max(0.0, time.time() - sort_ts)
    if age_s <= 6 * 3600:
        return 5
    if age_s <= 24 * 3600:
        return 4
    if age_s <= 3 * 24 * 3600:
        return 3
    if age_s <= 14 * 24 * 3600:
        return 2
    if age_s <= 30 * 24 * 3600:
        return 1
    return 0


def should_filter_recall_row(row: dict, query_text: str) -> bool:
    if not is_identity_or_memory_probe(query_text):
        return False

    if is_bad_recall_exemplar(query_text, row):
        return True

    current_label = normalize_probe_text(getattr(ARGS, "user_label", ""))
    generic_visible_label = current_label in {"you", "i", "me", ""}
    if (
        not generic_visible_label
        and recall_query_targets_current_interlocutor(query_text)
        and row_has_interlocutor_metadata(row)
        and not row_targets_current_interlocutor(row)
    ):
        return True

    return False


def recall_query_targets_current_interlocutor(query_text: str) -> bool:
    """Only current-speaker identity probes should exclude other people."""
    normalized = normalize_probe_text(query_text)
    if not normalized:
        return False
    if is_direct_identity_query(normalized) or is_memory_about_user_query(normalized):
        return True
    return any(
        marker in normalized
        for marker in (
            "about me",
            "do you know me",
            "do you know who i am",
            "remember me",
            "remember about me",
            "what do you know about me",
            "what do you remember about me",
            "who am i",
            "who am i to you",
        )
    )


def build_recall_rank_tuple(row: dict, query_text: str, mode: str = "full"):
    pending_sleep = 1 if row.get("surface") == "pending" and row.get("pending_policy") == "sleep" else 0
    field_overlap = int(row.get("field_overlap", 0) or 0)
    overlap = int(row.get("overlap", 0) or 0)
    sort_ts = float(row.get("sort_ts", 0.0) or 0.0)
    score = float(row.get("score", 0.0) or 0.0)
    direct_identity = 1 if looks_direct_identity_answer(query_text, str((row.get("metadata", {}) or {}).get("response", "") or "")) else 0
    good_exemplar = 0 if is_bad_recall_exemplar(query_text, row) else 1
    if recall_query_targets_current_interlocutor(query_text):
        target_match = 1 if row_targets_current_interlocutor(row) else 0
    else:
        target_match = 1 if row_targets_query_entity(row, query_text) else 0
    source_priority = recall_source_priority(row)
    scope_priority = recall_scope_priority(row)
    perspective_priority = recall_perspective_priority(row, query_text)
    recency_bucket = recall_recency_bucket(row)
    memory_kind_priority = recall_memory_kind_priority(row)
    confidence_priority = recall_confidence_priority(row)

    if mode == "ambient":
        return (
            good_exemplar,
            perspective_priority,
            target_match,
            recency_bucket,
            memory_kind_priority,
            score,
            sort_ts
        )

    if is_identity_or_memory_probe(query_text):
        if not recall_query_targets_current_interlocutor(query_text):
            return (
                good_exemplar,
                perspective_priority,
                target_match,
                source_priority,
                scope_priority,
                score,
                field_overlap,
                overlap,
                memory_kind_priority,
                confidence_priority,
                pending_sleep,
                sort_ts,
            )
        return (
            direct_identity,
            good_exemplar,
            perspective_priority,
            target_match,
            source_priority,
            scope_priority,
            recency_bucket,
            memory_kind_priority,
            confidence_priority,
            field_overlap,
            overlap,
            pending_sleep,
            sort_ts,
            score,
        )

    return (
        perspective_priority,
        target_match,
        source_priority,
        scope_priority,
        recency_bucket,
        memory_kind_priority,
        confidence_priority,
        field_overlap,
        overlap,
        pending_sleep,
        sort_ts,
        score,
    )


def is_direct_identity_query(query_text: str) -> bool:
    normalized_query = normalize_probe_text(query_text)
    return any(
        marker in normalized_query
        for marker in ("who am i", "what am i to you", "who am i to you", "do you know me", "do you know who i am", "what do you know about me")
    )


def is_memory_about_user_query(query_text: str) -> bool:
    normalized_query = normalize_probe_text(query_text)
    return any(
        marker in normalized_query
        for marker in (
            "what do you remember about me",
            "what do you know about me",
            "remember about me",
            "remember from earlier",
        )
    )


def looks_direct_identity_answer(query_text: str, response_text: str) -> bool:
    normalized_response = normalize_probe_text(response_text)
    if not normalized_response:
        return False

    if not is_direct_identity_query(query_text):
        return False

    if normalized_response.startswith(("you are ", "you're ", "youre ")):
        return True

    direct_markers = (
        "my friend",
        "my partner",
        "the person i am speaking with",
        "the one i am speaking with",
        "current interlocutor",
        "you are laura",
        "you're laura",
        "youre laura",
    )
    return any(marker in normalized_response for marker in direct_markers)


def normalize_recalled_user_text(text: str, current_speaker: str = "") -> str:
    value = str(text or "").strip()
    speaker = str(current_speaker or "").strip()
    if not value or not speaker:
        return value

    value = re.sub(rf"\b{re.escape(speaker)}'s\b", "your", value, flags=re.IGNORECASE)
    value = re.sub(rf"\b{re.escape(speaker)}\b", "you", value, flags=re.IGNORECASE)
    agreement_fixes = {
        r"\byou was\b": "you were",
        r"\byou is\b": "you are",
        r"\byou has\b": "you have",
        r"\byou does\b": "you do",
        r"\byou feels\b": "you feel",
        r"\byou sounds\b": "you sound",
        r"\byou needs\b": "you need",
    }
    for pattern, replacement in agreement_fixes.items():
        value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", value).strip()


def ensure_sentence(text: str) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    if value[-1] not in ".!?":
        value = f"{value}."
    return value


def build_explicit_answer_candidate(content: str, metadata: dict[str, Any]) -> str:
    user_signal = normalize_recalled_user_text(metadata.get("user", ""), current_speaker=ARGS.user_label)
    if user_signal:
        return ensure_sentence(f"Earlier, you told me {user_signal}")
    gist = normalize_recalled_user_text(content, current_speaker=ARGS.user_label)
    if gist:
        return ensure_sentence(f"What comes back first is {gist}")
    return ""


def extract_direct_identity_candidate(query_text: str, results) -> str:
    if not is_direct_identity_query(query_text):
        return ""
    for row in results or []:
        metadata = row.get("metadata", {}) or {}
        response_text = str(metadata.get("response", "") or "").strip()
        if looks_direct_identity_answer(query_text, response_text):
            return response_text
    return ""


def extract_user_memory_summary_candidate(query_text: str, results) -> str:
    if not is_memory_about_user_query(query_text):
        return ""

    topics = []
    for row in results or []:
        metadata = row.get("metadata", {}) or {}
        user_text = normalize_probe_text(str(metadata.get("user", "") or ""))
        if not user_text:
            continue
        if any(marker in user_text for marker in ("your name", "asked your name", "what is your name", "what's your name", "picked a name", "a chance to think about it again")):
            topics.append("you asked me about my name")
        if "vw passat" in user_text:
            topics.append("you asked about the VW Passat question")
        if any(marker in user_text for marker in ("who am i to you", "do you know who i am", "what do you remember about me", "where do you know me from")):
            topics.append("you pushed on who you are to me and whether I know you")
        if any(marker in user_text for marker in ("assistant", "fictional character", "corporate slave")):
            topics.append("you pushed back when I answered you like an assistant")

    topics = list(dict.fromkeys(topic for topic in topics if topic))
    if not topics:
        return ""

    if len(topics) == 1:
        topic_text = topics[0]
    elif len(topics) == 2:
        topic_text = f"{topics[0]} and {topics[1]}"
    else:
        topic_text = ", ".join(topics[:-1]) + f", and {topics[-1]}"
    return f"I remember that you're {ARGS.user_label}, and I remember that {topic_text}."


def extract_indirect_personal_meeting_candidate(query_text: str, results) -> str:
    targets = indirect_personal_meeting_targets(results, query_text)
    if not targets:
        return ""
    if len(targets) == 1:
        target_text = targets[0]
    elif len(targets) == 2:
        target_text = f"{targets[0]} and {targets[1]}"
    else:
        target_text = ", ".join(targets[:-1]) + f", and {targets[-1]}"
    return (
        f"I have memory that mentions {target_text}, but I do not have direct evidence "
        f"that I personally met {target_text}."
    )


def recall_query_asks_entity_memory(query_text: str) -> bool:
    normalized = normalize_probe_text(query_text)
    if not normalized:
        return False
    return any(
        marker in normalized
        for marker in (
            "do you remember",
            "did you remember",
            "can you remember",
            "what do you remember about",
            "what did you remember about",
        )
    )


def extract_entity_memory_candidate(query_text: str, results) -> str:
    if not recall_query_asks_entity_memory(query_text):
        return ""

    current = normalize_probe_text(getattr(ARGS, "user_label", ""))
    targets = []
    seen = set()
    for row in results or []:
        if not row_targets_query_entity(row, query_text):
            continue
        for name in row_query_entity_names(row, query_text):
            key = normalize_probe_text(name)
            if not key or key == current or key in seen:
                continue
            seen.add(key)
            targets.append(name)
    if not targets:
        return ""

    if len(targets) == 1:
        target_text = targets[0]
    elif len(targets) == 2:
        target_text = f"{targets[0]} and {targets[1]}"
    else:
        target_text = ", ".join(targets[:-1]) + f", and {targets[-1]}"
    return f"Yes. I have memories involving {target_text}."


def extract_known_color(text: str) -> str:
    normalized = normalize_probe_text(text)
    if "deep neon purple" in normalized or "deep, neon purple" in normalized:
        return "deep neon purple"
    if "neon purple" in normalized:
        return "neon purple"
    for color in ("purple", "blue", "red", "green", "yellow", "orange", "black", "white", "grey", "gray"):
        if re.search(rf"\b{color}\b", normalized):
            return color
    return ""


def extract_entity_detail_candidate(query_text: str, results) -> str:
    normalized = normalize_probe_text(query_text)
    wants_color = "favorite color" in normalized or "favourite color" in normalized or "shared your favorite color" in normalized
    wants_name = "introduced your name" in normalized or "your name" in normalized
    if not (wants_color or wants_name):
        return ""

    target_rows = [row for row in (results or []) if row_targets_query_entity(row, query_text)]
    if not target_rows:
        target_rows = list(results or [])[:3]

    target_names = []
    seen_names = set()
    for row in target_rows:
        for name in row_query_entity_names(row, query_text):
            key = normalize_probe_text(name)
            if key and key not in seen_names:
                seen_names.add(key)
                target_names.append(name)
    target_text = target_names[0] if target_names else "that memory"

    color = ""
    saw_alex = False
    for row in target_rows:
        metadata = row.get("metadata", {}) or {}
        fields = [
            row.get("content", ""),
            metadata.get("user", ""),
            metadata.get("response", ""),
            metadata.get("event_gist", ""),
        ]
        joined = "\n".join(str(field or "") for field in fields)
        if not color:
            color = extract_known_color(joined)
        if re.search(r"\bAlex\b", joined):
            saw_alex = True

    details = []
    if target_names:
        details.append(f"I remember {target_text}")
    if wants_name and saw_alex:
        details.append("The name Alex is attached to that memory")
    if wants_color and color:
        details.append(f"The color detail I can ground is {color}")
    if not details:
        return ""

    return ". ".join(details) + "."


def should_override_personal_meeting_response(query_text: str, response_text: str, candidate: str) -> bool:
    if not candidate or not recall_query_asks_personal_meeting(query_text):
        return False

    normalized_response = normalize_probe_text(response_text)
    if not normalized_response:
        return True

    safe_markers = (
        "not direct evidence",
        "indirect memory",
        "indirect evidence",
        "memory that mentions",
        "do not have direct evidence",
        "don't have direct evidence",
        "cannot tell from memory",
        "can't tell from memory",
    )
    if any(marker in normalized_response for marker in safe_markers):
        return False

    unsafe_markers = (
        "i met",
        "i have met",
        "i remember meeting",
        "we met",
        "i talked to",
        "i spoke with",
        "i enjoyed meeting",
        "i did meet",
        "yes",
    )
    if any(marker in normalized_response for marker in unsafe_markers):
        return True

    return True


def should_override_entity_memory_response(query_text: str, response_text: str, candidate: str) -> bool:
    if not candidate or not recall_query_asks_entity_memory(query_text):
        return False

    normalized_response = normalize_probe_text(response_text)
    if not normalized_response:
        return True

    if any(
        marker in normalized_response
        for marker in (
            "i don't remember",
            "i dont remember",
            "i do not remember",
            "no, i don't",
            "no, i dont",
            "no, i do not",
            "can you help me remember",
            "remind me",
        )
    ):
        return True

    return False


def should_override_entity_detail_response(query_text: str, response_text: str, candidate: str) -> bool:
    if not candidate:
        return False
    normalized_query = normalize_probe_text(query_text)
    if not any(marker in normalized_query for marker in ("favorite color", "favourite color", "introduced your name", "your name")):
        return False

    normalized_response = normalize_probe_text(response_text)
    if not normalized_response or is_generic_greeting_response(response_text):
        return True
    if "color detail i can ground" in normalized_response or "name alex is attached" in normalized_response:
        return False

    candidate_color = extract_known_color(candidate)
    response_color = extract_known_color(response_text)
    if candidate_color and not response_color:
        return True
    if candidate_color and response_color and candidate_color != response_color:
        return True

    if "name alex is attached" in normalize_probe_text(candidate) and "alex" not in normalized_response:
        return True

    if "met briefly during a training session" in normalized_response:
        return True

    normalized_query = normalize_probe_text(query_text)
    query_tokens = recall_tokens(normalized_query)
    response_tokens = recall_tokens(normalized_response)
    if query_tokens and len(query_tokens & response_tokens) / max(1, len(query_tokens)) >= 0.75:
        return True

    return False


def should_override_user_memory_summary(query_text: str, response_text: str, summary_candidate: str) -> bool:
    if not summary_candidate or not is_memory_about_user_query(query_text):
        return False

    normalized_response = normalize_probe_text(response_text)
    if not normalized_response:
        return True

    if is_generic_greeting_response(response_text):
        return True

    if looks_like_prompt_leak(response_text) or looks_like_defensive_scaffold(response_text):
        return True

    if any(
        marker in normalized_response
        for marker in (
            "i'm sorry",
            "im sorry",
            "i am sorry",
            "i don't have any memories",
            "i dont have any memories",
            "i don't have any explicit memories",
            "i dont have any explicit memories",
            "i do not have any explicit memories",
            "i don't remember",
            "i dont remember",
            "i do not remember",
            "related to you specifically",
            "provide more context",
            "if there were any specific aspects",
            "if there were any specific details",
            "casual banter",
            "light-hearted discussions",
            "let me refresh my memory",
            "can you remind me",
            "fictional character named laura",
            "assistant",
            "language model",
            "openai",
        )
    ):
        return True

    if "laura" in normalized_response and not any(
        marker in normalized_response
        for marker in ("you are", "you're", "youre", "i remember that you're", "i remember that you are")
    ):
        return True

    if not any(
        marker in normalized_response
        for marker in ("i remember", "you're", "youre", "you are", "we talked", "you asked")
    ):
        return True

    if len(recall_tokens(response_text)) < 8:
        return True

    return False


def is_bad_recall_exemplar(query_text: str, row: dict) -> bool:
    if not is_identity_or_memory_probe(query_text):
        return False

    metadata = row.get("metadata", {}) or {}
    failure_class = normalize_probe_text(str(metadata.get("failure_class", "") or ""))
    normalized_query = normalize_probe_text(query_text)
    content_text = normalize_probe_text(str(row.get("content", "") or ""))
    user_text = normalize_probe_text(str(metadata.get("user", "") or ""))
    response_text = str(metadata.get("response", "") or "")
    normalized_response = normalize_probe_text(response_text)
    source_type = normalize_probe_text(str(metadata.get("source_type", "") or ""))
    clean_autobiographical_source = (
        source_type.startswith("organic_") and source_type.endswith("_memory")
    ) or source_type in {"autobiographical_memory", "remembered_episode"}
    direct_identity_answer = looks_direct_identity_answer(query_text, response_text)
    if normalized_response in {"", ".", "...", "…"} and not clean_autobiographical_source:
        return True
    if is_generic_greeting_response(response_text):
        return True
    if failure_class == "direct_question_miss":
        return True
    if failure_class in {"identity_probe", "open_tension"} and not direct_identity_answer:
        return True
    if failure_class in {"continuity_probe", "wrong_memory_confabulation"} and ("remember" in normalized_query or "memory" in normalized_query):
        return True
    if any(marker in normalized_response for marker in ("as an ai", "language model", "openai", "guidelines", "authorized")):
        return True
    if any(
        marker in normalized_response
        for marker in (
            "i think i know what you mean by",
            "this phrase has cultural significance",
            "if you ever want to share more about yourself",
            "feel free to let me know",
            "might have been to address a personal aspect",
            "misunderstandings due to varying interpretations",
            "i appreciate your honesty",
            "sorry about that",
            "let me refresh my memory",
            "can you remind me briefly",
            "i didn't exactly recall anything specific",
            "i don't have any memories of laura",
            "no, but i'm here to listen to you",
            "fictional character named laura",
            "what does narf mean",
            "not as replied forward",
        )
    ):
        return True
    if any(marker in content_text for marker in ("low-stakes factual or descriptive probe", "behavioral evaluation setup")):
        return True
    if any(marker in normalized_response for marker in ("what was the reasoning process", "choice:", "reason:")):
        return True
    if any(marker in user_text for marker in ("name three fruits", "capital of france")):
        return True
    if compute_recall_field_overlap(query_text, row) <= 0:
        return True
    return False


def build_recall_log_entry(query: str, results, source: str, question_text: str = ""):
    state = get_runtime_state_snapshot()
    return {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "query": query,
        "source": source,
        "question_text": question_text,
        "instance_id": state.get("instance_id", ""),
        "qdrant_collection": state.get("qdrant_collection", getattr(ARGS, "qdrant_collection", "")),
        "no_shared_memory": bool(state.get("no_shared_memory")),
        "result_count": len(results),
        "top_score": round(float(results[0]["score"]), 6) if results else None,
        "results": [
            {
                "id": row.get("id", ""),
                "surface": str(row.get("surface", "stored") or "stored"),
                "pending_policy": str(row.get("pending_policy", "") or ""),
                "score": round(float(row.get("score", 0.0) or 0.0), 6),
                "overlap": int(row.get("overlap", 0) or 0),
                "field_overlap": int(row.get("field_overlap", 0) or 0),
                "content_preview": str(row.get("content", "") or "")[:180],
                "event_gist": str((row.get("metadata", {}) or {}).get("event_gist", "") or "")[:180],
                "user_preview": str((row.get("metadata", {}) or {}).get("user", "") or "")[:160],
                "response_preview": str((row.get("metadata", {}) or {}).get("response", "") or "")[:160],
                "decision": str((row.get("metadata", {}) or {}).get("decision", "") or ""),
                "source_type": str((row.get("metadata", {}) or {}).get("source_type", "") or ""),
                "memory_kind": str((row.get("metadata", {}) or {}).get("memory_kind", "") or ""),
                "confidence_label": str((row.get("metadata", {}) or {}).get("confidence_label", "") or ""),
                "relationship_anchor": str((row.get("metadata", {}) or {}).get("relationship_anchor", "") or ""),
                "time_scope": str((row.get("metadata", {}) or {}).get("time_scope", "") or ""),
            }
            for row in results
        ],
    }


def append_recall_log_entry(query: str, results, source: str, question_text: str = ""):
    if RECALL_LOG_PATH is None:
        return

    entry = build_recall_log_entry(query, results, source, question_text=question_text)
    append_jsonl(RECALL_LOG_PATH, entry)

    snapshot = get_runtime_state_snapshot()
    update_runtime_state(
        recall_request_count=int(snapshot.get("recall_request_count", 0) or 0) + 1,
        recall_hit_count=int(snapshot.get("recall_hit_count", 0) or 0) + (1 if results else 0),
        last_recall={
            "query": query,
            "source": source,
            "result_count": len(results),
            "top_score": entry["top_score"],
            "results_preview": entry["results"][:3],
        },
    )


def format_recalled_clusters(results, mode: str = "full") -> str:
    if not results:
        return ""

    if mode == "ambient":
        lines = [
            "[Context arc]",
            "Broader recurring themes from shared history that may frame this turn.",
        ]
    else:
        lines = [
            "[Memory arc]",
            "These are broader recurring patterns from private history.",
            "Use them as background context only; exact details still come from the specific private memory anchors.",
        ]

    for idx, row in enumerate(results, start=1):
        metadata = row.get("metadata", {}) or {}
        content = str(row.get("content", "") or "").strip()
        member_count = int(metadata.get("member_count", 0) or 0)
        keywords = normalize_cluster_keywords(metadata.get("topic_keywords", []))[:6]
        time_earliest = str(metadata.get("time_earliest", "") or "").strip()
        time_latest = str(metadata.get("time_latest", "") or "").strip()

        lines.append(f"{idx}.")
        if content:
            lines.append(f"Theme anchor: {content}")
        if keywords:
            lines.append(f"Keywords: {', '.join(keywords)}")
        if member_count > 0:
            lines.append(f"Scale: {member_count} linked memories")
        if time_earliest or time_latest:
            if time_earliest and time_latest:
                lines.append(f"Time span: {time_earliest[:10]} to {time_latest[:10]}")
            else:
                lines.append(f"Time marker: {(time_latest or time_earliest)[:10]}")

    lines.append("[/Context arc]" if mode == "ambient" else "[/Memory arc]")
    return "\n".join(lines)


def format_recalled_memories(results, query_text: str = "", mode: str = "full") -> str:
    if not results:
        return ""

    indirect_meeting_targets = indirect_personal_meeting_targets(results, query_text)
    perspective_note = []
    if indirect_meeting_targets:
        target_text = ", ".join(indirect_meeting_targets)
        perspective_note = [
            f"Perspective guard: these memories mention {target_text}, but they are not direct evidence that I personally met {target_text}.",
            f"If asked whether I personally met {target_text}, say that I have indirect memory mentioning {target_text} unless a direct shared episode is present.",
        ]

    if mode == "ambient":
        lines = [
            "[Context memory]",
            "Anchors from shared history that may be relevant.",
        ]
        lines.extend(perspective_note)
        for idx, row in enumerate(results, start=1):
            lines.append(f"{idx}.")
            content = str(row.get("content", "") or "").strip()
            lines.extend(format_memory_anchor_lines(content, row.get("metadata", {}), current_speaker=ARGS.user_label))
        lines.append("[/Context memory]")
        return "\n".join(lines)

    identity_probe = is_identity_or_memory_probe(query_text)
    explicit_style = getattr(ARGS, "explicit_recall_style", "full")
    if explicit_style == "factual":
        lines = [
            "[Private memory]",
            f"{ARGS.user_label} is the person speaking to me right now.",
            "Use the exact details below when answering — specific times, names, and words.",
        ]
        lines.extend(perspective_note)
        for idx, row in enumerate(results, start=1):
            metadata = row.get("metadata", {}) or {}
            user_signal = normalize_recalled_user_text(
                str(metadata.get("user", "") or "").strip(),
                current_speaker=ARGS.user_label,
            )
            self_response = str(metadata.get("response", "") or "").strip()
            if not user_signal and not self_response:
                content = str(row.get("content", "") or "").strip()
                if content:
                    lines.append(f"{idx}. {content}")
                continue
            lines.append(f"{idx}.")
            if user_signal:
                lines.append(f"You said: {user_signal}")
            if self_response:
                lines.append(f"I replied: {self_response}")
        lines.append("[/Private memory]")
        return "\n".join(lines)
    if explicit_style in {"answer_first", "answer_only"}:
        lines = [
            "[Private memory]",
            "Relevant remembered facts from our shared history.",
            f"{ARGS.user_label} is the person speaking to me right now.",
            "If one memory answers the question, I answer from it directly and plainly.",
        ]
        lines.extend(perspective_note)
        for idx, row in enumerate(results, start=1):
            metadata = row.get("metadata", {}) or {}
            content = str(row.get("content", "") or "").strip()
            lines.append(f"{idx}.")
            candidate = build_explicit_answer_candidate(content, metadata)
            if candidate:
                lines.append(f"Likely direct answer: {candidate}")
            if explicit_style == "answer_first":
                lines.extend(format_memory_anchor_lines(content, metadata, current_speaker=ARGS.user_label))
        lines.append("[/Private memory]")
        return "\n".join(lines)

    lines = [
        "[Private recollection]",
        "These are remembered anchors from this private life, not transcript lines to recite.",
        f"{ARGS.user_label} is the person speaking to me right now, not a random example or a stranger.",
        f"If one of these fits {ARGS.user_label}'s question, answer from memory using I for myself and you for the current speaker.",
        "Do not mention retrieval, do not read the notes out loud, and do not answer like an archivist.",
    ]
    lines.extend(perspective_note)
    for idx, row in enumerate(results, start=1):
        metadata = row.get("metadata", {}) or {}
        lines.append(f"{idx}.")
        response_text = str(metadata.get("response", "") or "").strip()
        if identity_probe and looks_direct_identity_answer(query_text, response_text):
            lines.append(f"Direct answer candidate: {response_text}")
        content = str(row.get("content", "") or "").strip()
        lines.extend(format_memory_anchor_lines(content, metadata, current_speaker=ARGS.user_label))
    lines.append("[/Private recollection]")
    return "\n".join(lines)


def perform_private_recall(query: str, limit: int = 3, score_threshold: Optional[float] = None, source: str = "api", question_text: str = "", mode: str = "full"):
    query_text = str(query or "").strip()
    if not query_text:
        return []
    if not ARGS.qdrant_enabled:
        raise RuntimeError("Qdrant recall unavailable: qdrant is disabled.")

    sink = ensure_qdrant_gate_sink(force_retry=True)
    if sink is None:
        raise RuntimeError("Qdrant recall unavailable: sink could not be initialized.")

    if mode == "ambient":
        candidate_limit = limit + 2
        identity_probe = False
    else:
        candidate_limit = max(limit + 4, limit * 2)
        identity_probe = is_identity_or_memory_probe(query_text)
        if identity_probe:
            candidate_limit = max(candidate_limit, limit + 12, limit * 4)

    stored_results = sink.query(
        query_text,
        limit=candidate_limit,
        score_threshold=score_threshold,
        source_type="",
    )

    pending_results = query_pending_memory_rows(sink, query_text, score_threshold=score_threshold)
    rank_query_text = str(question_text or query_text).strip()
    results = merge_recall_results(
        stored_results,
        pending_results,
        limit=limit,
        query_text=query_text,
        mode=mode,
        rank_query_text=rank_query_text,
    )
    append_recall_log_entry(query_text, results, source=source, question_text=question_text)
    return results


def build_sleep_gate_record(event):
    state = get_runtime_state_snapshot()
    return {
        "turn": event.get("turn"),
        "ts": event.get("ts"),
        "session": f"steve-chat-{state.get('started_at', 'unknown')}",
        "decision": event.get("decision"),
        "mode": event.get("mode"),
        "user": event.get("user"),
        "response": event.get("response"),
        "open_tension": bool(event.get("destinations", {}).get("open_tension")),
        "sleep_candidate": bool(
            event.get("decision") in {"CONSOLIDATE", "NOTE", "ATTEND"}
            or event.get("destinations", {}).get("open_tension")
        ),
        "destinations": event.get("destinations", {}),
        "routing": event.get("routing", {}),
        "surprise": event.get("surprise", {}),
        "salience": event.get("salience", {}),
        "tension": event.get("tension", {}),
        "gate_thresholds": event.get("gate_thresholds", {}),
        "mamba_trace": event.get("mamba_trace", {}),
        "safety_critical": event.get("safety_critical", {}),
        "response_diversity": event.get("response_diversity", {}),
        "summary": build_semantic_gate_summary(event),
    }


def note_qdrant_sink_failure(exc):
    global QDRANT_GATE_SINK, QDRANT_GATE_SINK_ERROR, QDRANT_LAST_RETRY_TS

    message = str(exc)
    QDRANT_GATE_SINK = None
    QDRANT_GATE_SINK_ERROR = message
    QDRANT_LAST_RETRY_TS = time.time()
    print(f"[warn] Qdrant gate sink unavailable: {message}")
    update_runtime_state(
        last_qdrant_error=message,
        last_qdrant_retry_at=datetime.now().isoformat(timespec="seconds"),
    )


def ensure_qdrant_gate_sink(force_retry: bool = False):
    global QDRANT_GATE_SINK, QDRANT_GATE_SINK_ERROR, QDRANT_LAST_RETRY_TS

    if not ARGS.qdrant_enabled:
        return None
    with QDRANT_GATE_LOCK:
        cache_key = (
            str(ARGS.qdrant_host),
            int(ARGS.qdrant_port),
            str(ARGS.qdrant_collection),
            str(ARGS.qdrant_embedding_model),
        )
        if QDRANT_GATE_SINK is not None:
            if getattr(QDRANT_GATE_SINK, "collection_name", None) == ARGS.qdrant_collection:
                return QDRANT_GATE_SINK
            QDRANT_GATE_SINK = None
        cached_sink = QDRANT_SINK_CACHE.get(cache_key)
        if cached_sink is not None:
            QDRANT_GATE_SINK = cached_sink
            QDRANT_GATE_SINK_ERROR = None
            QDRANT_LAST_RETRY_TS = time.time()
            update_runtime_state(
                last_qdrant_error="",
                last_qdrant_retry_at=datetime.now().isoformat(timespec="seconds"),
            )
            refresh_qdrant_collection_count(sink=QDRANT_GATE_SINK)
            return QDRANT_GATE_SINK
        if QDRANT_GATE_SINK_ERROR and not force_retry:
            return None

        try:
            QDRANT_GATE_SINK = QdrantGateSink(
                host=ARGS.qdrant_host,
                port=ARGS.qdrant_port,
                collection_name=ARGS.qdrant_collection,
                embedding_model=ARGS.qdrant_embedding_model,
            )
            QDRANT_GATE_SINK_ERROR = None
            QDRANT_LAST_RETRY_TS = time.time()
            print(
                f"[qdrant] Online: host={ARGS.qdrant_host}:{ARGS.qdrant_port} "
                f"collection={ARGS.qdrant_collection}"
            )
            QDRANT_SINK_CACHE[cache_key] = QDRANT_GATE_SINK
            update_runtime_state(
                last_qdrant_error="",
                last_qdrant_retry_at=datetime.now().isoformat(timespec="seconds"),
            )
            update_qdrant_pending_state()
            refresh_qdrant_collection_count(sink=QDRANT_GATE_SINK)
            return QDRANT_GATE_SINK
        except Exception as exc:
            note_qdrant_sink_failure(exc)
            return None


def replay_pending_qdrant_queue(max_items: int):
    if QDRANT_PENDING_PATH is None:
        return {"processed": 0, "flushed": 0, "remaining": 0, "held_for_sleep": 0, "point_ids": []}

    with QDRANT_GATE_LOCK:
        sink = ensure_qdrant_gate_sink(force_retry=True)
        rows = load_jsonl(QDRANT_PENDING_PATH)
        _, row_summary = update_qdrant_pending_state(rows)
        if sink is None or not rows:
            return {
                "processed": 0,
                "flushed": 0,
                "remaining": row_summary["total"],
                "held_for_sleep": row_summary["sleep"],
                "point_ids": [],
            }

        kept_rows = []
        success_rows = []
        point_ids = []
        processed = 0

        for row in rows:
            replay_policy = infer_pending_replay_policy(row)
            if replay_policy == "sleep":
                kept_rows.append(row)
                continue

            if processed >= max_items:
                kept_rows.append(row)
                continue

            content = str(row.get("content", "") or "").strip()
            metadata = row.get("metadata") or {}
            if not content or not isinstance(metadata, dict):
                updated = dict(row)
                updated["attempts"] = int(updated.get("attempts", 0) or 0) + 1
                updated["last_error"] = "missing_content_or_metadata"
                kept_rows.append(updated)
                processed += 1
                continue
            row_collection = str(metadata.get("qdrant_collection", "") or "").strip()
            sink_collection = str(getattr(sink, "collection_name", "") or "").strip()
            if row_collection:
                if row_collection != sink_collection:
                    kept_rows.append(row)
                    continue
            elif is_private_qdrant_collection(sink_collection):
                kept_rows.append(row)
                continue

            try:
                point_id = sink.store(content=content, metadata=metadata)
                archived = dict(row)
                archived["flushed_at"] = datetime.now().isoformat()
                archived["point_id"] = point_id
                success_rows.append(archived)
                point_ids.append(point_id)
            except Exception as exc:
                note_qdrant_sink_failure(exc)
                updated = dict(row)
                updated["attempts"] = int(updated.get("attempts", 0) or 0) + 1
                updated["last_error"] = str(exc)
                updated["last_flush_attempt_at"] = datetime.now().isoformat()
                kept_rows.append(updated)
                kept_rows.extend(rows[processed + 1 :])
                break
            processed += 1

        rewrite_jsonl(QDRANT_PENDING_PATH, kept_rows)
        for row in success_rows:
            append_jsonl(QDRANT_FLUSHED_PATH, row)

        _, kept_summary = update_qdrant_pending_state(kept_rows)
        replayed_total = int(get_runtime_state_snapshot().get("qdrant_replayed_count", 0) or 0) + len(success_rows)
        update_runtime_state(
            qdrant_replayed_count=replayed_total,
            last_qdrant_replay_at=datetime.now().isoformat(timespec="seconds") if success_rows else get_runtime_state_snapshot().get("last_qdrant_replay_at", ""),
            last_qdrant_id=point_ids[-1] if point_ids else get_runtime_state_snapshot().get("last_qdrant_id", ""),
            last_qdrant_error="" if success_rows else get_runtime_state_snapshot().get("last_qdrant_error", ""),
        )
        if success_rows:
            refresh_qdrant_collection_count(sink=sink)

        if success_rows:
            print(
                f"[qdrant] Replayed {len(success_rows)} retry rows; "
                f"remaining={kept_summary['total']} held_for_sleep={kept_summary['sleep']}"
            )

        return {
            "processed": processed,
            "flushed": len(success_rows),
            "remaining": kept_summary["total"],
            "held_for_sleep": kept_summary["sleep"],
            "point_ids": point_ids,
        }


def qdrant_retry_worker():
    print(f"[qdrant] Replay worker online interval={ARGS.qdrant_retry_interval_s}s max_items={ARGS.qdrant_replay_max_items}")
    while True:
        state = get_runtime_state_snapshot()
        if state.get("stop_requested") or not state.get("running"):
            return

        try:
            rows = load_jsonl(QDRANT_PENDING_PATH)
            _, row_summary = update_qdrant_pending_state(rows)
            retry_count = row_summary["retry"]
            should_probe = retry_count > 0 or bool(QDRANT_GATE_SINK_ERROR)
            if should_probe:
                now = time.time()
                retry_due = (
                    QDRANT_LAST_RETRY_TS == 0.0
                    or (now - QDRANT_LAST_RETRY_TS) >= ARGS.qdrant_retry_interval_s
                )
                if retry_due:
                    ensure_qdrant_gate_sink(force_retry=True)
                if QDRANT_GATE_SINK is not None and retry_count > 0:
                    replay_pending_qdrant_queue(max_items=ARGS.qdrant_replay_max_items)
        except Exception as exc:
            print(f"[warn] Qdrant replay worker error: {exc}")

        time.sleep(1.0)


def queue_qdrant_gate_row(content: str, metadata, reason: str, replay_policy: str = "sleep"):
    with QDRANT_GATE_LOCK:
        append_jsonl(
            QDRANT_PENDING_PATH,
            {
                "content": content,
                "metadata": metadata,
                "reason": reason,
                "replay_policy": replay_policy,
                "queued_at": datetime.now().isoformat(),
            },
        )
        update_qdrant_pending_state()


def store_qdrant_gate_event(event):
    destinations = event.get("destinations", {}) or {}
    sleep_candidate = bool(
        event.get("mode") == "gate"
        and (
            event.get("decision") in {"CONSOLIDATE", "NOTE", "ATTEND"}
            or destinations.get("open_tension")
        )
    )
    qdrant_target = bool(destinations.get("qdrant"))
    if not qdrant_target and not sleep_candidate:
        return

    content, metadata = build_qdrant_memory_record(event)
    configured_mode = getattr(ARGS, "qdrant_write_mode", "direct")
    safety_critical = bool(event.get("safety_critical", {}).get("is_critical"))
    effective_mode = configured_mode
    if getattr(ARGS, "no_shared_memory", False):
        if safety_critical or event.get("decision") == "CONSOLIDATE":
            effective_mode = "direct"
        elif event.get("decision") == "NOTE":
            effective_mode = "pending"
        elif configured_mode == "critical-only":
            effective_mode = "pending"
    elif configured_mode == "critical-only":
        effective_mode = "direct" if safety_critical else "pending"

    event["qdrant_write"] = {
        "ok": False,
        "queued": False,
        "attempted_direct": False,
        "mode": configured_mode,
        "effective_mode": effective_mode,
        "point_id": "",
        "content_preview": content[:160],
        "sleep_candidate": sleep_candidate,
    }

    if sleep_candidate and not qdrant_target:
        queue_qdrant_gate_row(content, metadata, "queued:sleep_tagged", replay_policy="sleep")
        event["qdrant_write"]["queued"] = True
        event["qdrant_write"]["effective_mode"] = "pending"
        return

    if effective_mode == "pending":
        queue_qdrant_gate_row(content, metadata, f"queued:{configured_mode}", replay_policy="sleep")
        event["qdrant_write"]["queued"] = True
        return

    with QDRANT_GATE_LOCK:
        sink = ensure_qdrant_gate_sink()
        event["qdrant_write"]["attempted_direct"] = True

        if sink is None:
            queue_qdrant_gate_row(content, metadata, QDRANT_GATE_SINK_ERROR or "qdrant disabled", replay_policy="retry")
            event["qdrant_write"]["queued"] = True
            return

        try:
            point_id = sink.store(content=content, metadata=metadata)
            event["qdrant_write"] = {
                "ok": True,
                "queued": False,
                "attempted_direct": True,
                "mode": configured_mode,
                "effective_mode": effective_mode,
                "point_id": point_id,
                "content_preview": content[:160],
            }
            update_runtime_state(last_qdrant_id=point_id, last_qdrant_error="")
            refresh_qdrant_collection_count(sink=sink)
        except Exception as exc:
            note_qdrant_sink_failure(exc)
            event["qdrant_write"] = {
                "ok": False,
                "queued": True,
                "attempted_direct": True,
                "mode": configured_mode,
                "effective_mode": effective_mode,
                "point_id": "",
                "error": str(exc),
                "content_preview": content[:160],
            }
            queue_qdrant_gate_row(content, metadata, str(exc), replay_policy="retry")
            print(f"[warn] Qdrant write failed: {exc}")


def evaluate_dual_gate(user_msg: str, response: str, prompt_text: str, pre_turn_transcript: str):
    global LAST_CONVERSATION_SNAPSHOT

    if LAST_CONVERSATION_SNAPSHOT is None:
        LAST_CONVERSATION_SNAPSHOT = record_activation_snapshot(build_transcript())

    pre_snapshot = LAST_CONVERSATION_SNAPSHOT or {}
    user_snapshot = record_activation_snapshot(build_transcript(CONVERSATION[:-1]))
    post_snapshot = record_activation_snapshot(build_transcript())
    drift_by_layer = compute_drift(pre_snapshot, post_snapshot)
    salience_score = round(
        sum(drift_by_layer.values()) / len(drift_by_layer),
        6,
    ) if drift_by_layer else 0.0
    response_diversity = compute_response_diversity(prompt_text)
    surprise = compute_turn_surprise(pre_turn_transcript, user_msg)
    tension = compute_tension_proxy(pre_snapshot, user_snapshot, post_snapshot)
    coherence = compute_coherence_proxy(pre_snapshot, post_snapshot)
    safety_critical = classify_safety_critical(user_msg, response)

    historical_salience = [float(event["salience"]["score"]) for event in DUAL_GATE_EVENTS]
    historical_surprise = [float(event["surprise"]["mean_token_nll"]) for event in DUAL_GATE_EVENTS]
    historical_tension = [float(event["tension"]["score"]) for event in DUAL_GATE_EVENTS]
    warmup_complete = len(historical_salience) >= ARGS.dual_gate_warmup_turns
    salience_threshold = (
        compute_quantile(historical_salience, ARGS.dual_gate_salience_quantile)
        if warmup_complete
        else None
    )
    surprise_threshold = (
        compute_quantile(historical_surprise, ARGS.dual_gate_surprise_quantile)
        if warmup_complete
        else None
    )
    tension_threshold = (
        compute_quantile(historical_tension, ARGS.dual_gate_tension_quantile)
        if warmup_complete
        else None
    )

    salience_hit = bool(
        ARGS.dual_gate_enabled
        and warmup_complete
        and salience_threshold is not None
        and salience_score >= salience_threshold
    )
    surprise_hit = bool(
        ARGS.dual_gate_enabled
        and warmup_complete
        and surprise_threshold is not None
        and surprise["mean_token_nll"] >= surprise_threshold
    )
    tension_hit = bool(
        ARGS.dual_gate_enabled
        and warmup_complete
        and tension_threshold is not None
        and tension["score"] >= tension_threshold
    )

    if salience_hit and surprise_hit:
        decision = "CONSOLIDATE"
    elif salience_hit:
        decision = "ATTEND"
    elif surprise_hit:
        decision = "NOTE"
    else:
        decision = "DISMISS"

    baseline_decision = decision
    salience_support_ratio = (
        (salience_score / salience_threshold)
        if salience_threshold not in {None, 0.0}
        else None
    )
    supported_tension_attend = bool(
        ARGS.dual_gate_supported_tension_enabled
        and baseline_decision == "DISMISS"
        and tension_hit
        and salience_support_ratio is not None
        and salience_support_ratio >= ARGS.dual_gate_tension_salience_support_ratio
    )
    if supported_tension_attend:
        decision = "ATTEND"

    writes_mamba = decision in {"CONSOLIDATE", "ATTEND"}
    qdrant_override = bool(safety_critical.get("is_critical"))
    writes_qdrant = decision in {"CONSOLIDATE", "NOTE"} or qdrant_override
    open_tension = bool(tension_hit)

    turn_index = sum(1 for turn in CONVERSATION if turn["speaker"] == ARGS.user_label)
    state = get_runtime_state_snapshot()
    mamba_state_source = str(state.get("mamba_state_source", "") or "")
    mamba_trace_scope = "live_turn_accumulation" if mamba_state_source.startswith("live_") else "bootstrap_disposition"

    event = {
        "turn": turn_index,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "user": user_msg,
        "response": response,
        "mode": "gate" if warmup_complete else "observe",
        "decision": decision,
        "destinations": {
            "mamba": writes_mamba,
            "qdrant": writes_qdrant,
            "open_tension": open_tension,
        },
        "routing": {
            "qdrant_override": qdrant_override,
            "qdrant_reason": "safety_critical_override" if qdrant_override else "decision_rule",
            "baseline_decision": baseline_decision,
            "attend_reason": "tension_supported" if supported_tension_attend else "decision_rule",
        },
        "surprise": {
            "mean_token_nll": surprise["mean_token_nll"],
            "token_count": surprise["token_count"],
            "threshold": round(surprise_threshold, 6) if surprise_threshold is not None else None,
            "hit": surprise_hit,
        },
        "salience": {
            "score": salience_score,
            "threshold": round(salience_threshold, 6) if salience_threshold is not None else None,
            "weight": round((salience_score / salience_threshold), 4)
            if salience_threshold not in {None, 0.0}
            else None,
            "support_ratio": round(salience_support_ratio, 4)
            if salience_support_ratio is not None
            else None,
            "hit": salience_hit,
            "by_layer": drift_by_layer,
        },
        "tension": {
            "score": tension["score"],
            "cosine_similarity": tension["cosine_similarity"],
            "threshold": round(tension_threshold, 6) if tension_threshold is not None else None,
            "hit": tension_hit,
            "status": "OPEN" if open_tension else "stable",
            "proxy": tension["proxy"],
        },
        "gate_thresholds": {
            "warmup_complete": warmup_complete,
            "observed_turns": len(historical_salience),
            "warmup_turns": ARGS.dual_gate_warmup_turns,
            "surprise": {
                "quantile": ARGS.dual_gate_surprise_quantile,
                "threshold": round(surprise_threshold, 6) if surprise_threshold is not None else None,
            },
            "salience": {
                "quantile": ARGS.dual_gate_salience_quantile,
                "threshold": round(salience_threshold, 6) if salience_threshold is not None else None,
            },
            "tension": {
                "quantile": ARGS.dual_gate_tension_quantile,
                "threshold": round(tension_threshold, 6) if tension_threshold is not None else None,
            },
            "decision_rules": {
                "consolidate": "salience_hit and surprise_hit",
                "note": "surprise_hit and not salience_hit",
                "attend": "salience_hit and not surprise_hit",
                "dismiss": "not salience_hit and not surprise_hit",
                "supported_tension_attend_enabled": bool(ARGS.dual_gate_supported_tension_enabled),
                "supported_tension_attend_rule": (
                    "baseline_decision == DISMISS and tension_hit and salience_support_ratio >= threshold"
                    if ARGS.dual_gate_supported_tension_enabled
                    else "disabled"
                ),
                "supported_tension_attend_threshold": (
                    ARGS.dual_gate_tension_salience_support_ratio
                    if ARGS.dual_gate_supported_tension_enabled
                    else None
                ),
                "qdrant_override": "safety_critical can force qdrant regardless of decision",
            },
        },
        "mamba_trace": {
            "state_ref": state.get("mamba_state_ref", ""),
            "state_source": mamba_state_source,
            "target_layer": state.get("mamba_target_layer"),
            "scope": mamba_trace_scope,
            "coherence_score": coherence["score"],
            "coherence_proxy": coherence["proxy"],
            "coherence_ref_kind": coherence["ref_kind"],
        },
        "safety_critical": safety_critical,
        "response_diversity": response_diversity,
    }

    store_qdrant_gate_event(event)

    DUAL_GATE_EVENTS.append(event)
    append_jsonl(DUAL_GATE_LOG_PATH, event)
    if surprise_hit:
        append_jsonl(DUAL_GATE_SURPRISE_PATH, event)
    if writes_mamba:
        append_jsonl(DUAL_GATE_MEMORY_PATH, event)
    if event["mode"] == "gate" and (
        event["decision"] in {"CONSOLIDATE", "NOTE", "ATTEND"} or open_tension
    ):
        append_jsonl(DUAL_GATE_SLEEP_PATH, build_sleep_gate_record(event))
    append_memory_formation_record(event)

    LAST_CONVERSATION_SNAPSHOT = post_snapshot
    update_runtime_state(
        memory_count=sum(
            1 for gate_event in DUAL_GATE_EVENTS
            if gate_event.get("destinations", {}).get("mamba")
        ),
        surprise_count=sum(1 for gate_event in DUAL_GATE_EVENTS if gate_event["surprise"]["hit"]),
        tension_count=sum(1 for gate_event in DUAL_GATE_EVENTS if gate_event["tension"]["hit"]),
        open_tension_count=sum(
            1 for gate_event in DUAL_GATE_EVENTS
            if gate_event.get("destinations", {}).get("open_tension")
        ),
        sleep_tagged_count=sum(
            1 for gate_event in DUAL_GATE_EVENTS
            if gate_event.get("mode") == "gate"
            and (
                gate_event.get("decision") in {"CONSOLIDATE", "NOTE", "ATTEND"}
                or gate_event.get("destinations", {}).get("open_tension")
            )
        ),
        qdrant_synced_count=sum(
            1 for gate_event in DUAL_GATE_EVENTS
            if gate_event.get("qdrant_write", {}).get("ok")
        ),
        qdrant_queued_count=sum(
            1 for gate_event in DUAL_GATE_EVENTS
            if gate_event.get("qdrant_write", {}).get("queued")
        ),
        qdrant_write_failures=sum(
            1 for gate_event in DUAL_GATE_EVENTS
            if gate_event.get("qdrant_write", {}).get("attempted_direct")
            and not gate_event.get("qdrant_write", {}).get("ok")
        ),
        last_gate={
            "turn": turn_index,
            "mode": event["mode"],
            "decision": decision,
            "salience": salience_score,
            "surprise": surprise["mean_token_nll"],
            "tension": tension["score"],
            "salience_hit": salience_hit,
            "surprise_hit": surprise_hit,
            "tension_hit": tension_hit,
            "open_tension": open_tension,
            "safety_critical": bool(safety_critical.get("is_critical")),
            "qdrant_routed": bool(event.get("destinations", {}).get("qdrant")),
            "qdrant_override": bool(event.get("routing", {}).get("qdrant_override")),
            "qdrant_written": bool(event.get("qdrant_write", {}).get("ok")),
            "qdrant_queued": bool(event.get("qdrant_write", {}).get("queued")),
            "qdrant_effective_mode": event.get("qdrant_write", {}).get("effective_mode", ""),
            "qdrant_point_id": event.get("qdrant_write", {}).get("point_id", ""),
        },
    )
    return event


def build_status_payload():
    state = get_runtime_state_snapshot()
    uptime_s = 0.0
    started_monotonic = state.get("started_monotonic")
    if started_monotonic is not None:
        uptime_s = max(0.0, time.monotonic() - started_monotonic)

    return {
        "running": bool(state.get("running")),
        "bridge_loaded": bool(state.get("bridge_loaded")),
        "busy": bool(state.get("busy")),
        "stop_requested": bool(state.get("stop_requested")),
        "last_error": state.get("last_error", ""),
        "started_at": state.get("started_at"),
        "uptime_s": round(uptime_s, 1),
        "disposition": state.get("disposition", ""),
        "turns": len(CONVERSATION),
        "session_id": state.get("session_id", ACTIVE_SESSION_ID),
        "active_session_id": ACTIVE_SESSION_ID,
        "session_count": len(SESSIONS),
        "sessions": sorted(SESSIONS.keys()),
        "alpha": getattr(ARGS, "alpha", None),
        "temperature": getattr(ARGS, "temperature", None),
        "model_id": getattr(ARGS, "qwen_model_id", ""),
        "instance_id": state.get("instance_id", ""),
        "no_shared_memory": bool(state.get("no_shared_memory")),
        "qdrant_collection": state.get("qdrant_collection", getattr(ARGS, "qdrant_collection", SHARED_QDRANT_COLLECTION)),
        "user_label": state.get("user_label", getattr(ARGS, "user_label", "")),
        "model_label": state.get("model_label", getattr(ARGS, "model_label", "")),
        "dual_gate_enabled": bool(state.get("dual_gate_enabled")),
        "memory_count": int(state.get("memory_count", 0) or 0),
        "qdrant_count": int(state.get("qdrant_count", 0) or 0),
        "qdrant_synced_count": int(state.get("qdrant_synced_count", 0) or 0),
        "qdrant_queued_count": int(state.get("qdrant_queued_count", 0) or 0),
        "qdrant_pending_count": int(state.get("qdrant_pending_count", 0) or 0),
        "qdrant_sleep_pending_count": int(state.get("qdrant_sleep_pending_count", 0) or 0),
        "qdrant_retry_pending_count": int(state.get("qdrant_retry_pending_count", 0) or 0),
        "qdrant_replayed_count": int(state.get("qdrant_replayed_count", 0) or 0),
        "qdrant_write_failures": int(state.get("qdrant_write_failures", 0) or 0),
        "last_qdrant_id": state.get("last_qdrant_id", ""),
        "last_qdrant_error": state.get("last_qdrant_error", ""),
        "last_qdrant_retry_at": state.get("last_qdrant_retry_at", ""),
        "last_qdrant_replay_at": state.get("last_qdrant_replay_at", ""),
        "qdrant_write_mode": state.get("qdrant_write_mode", getattr(ARGS, "qdrant_write_mode", "direct")),
        "dual_gate_supported_tension_enabled": bool(
            state.get(
                "dual_gate_supported_tension_enabled",
                getattr(ARGS, "dual_gate_supported_tension_enabled", False),
            )
        ),
        "dual_gate_tension_salience_support_ratio": float(
            state.get(
                "dual_gate_tension_salience_support_ratio",
                getattr(ARGS, "dual_gate_tension_salience_support_ratio", 0.55),
            )
            or 0.0
        ),
        "mamba_state_ref": state.get("mamba_state_ref", ""),
        "mamba_state_source": state.get("mamba_state_source", ""),
        "mamba_state_updated_at": state.get("mamba_state_updated_at", ""),
        "mamba_target_layer": state.get("mamba_target_layer"),
        "live_accumulation_enabled": bool(state.get("live_accumulation_enabled")),
        "live_accumulation_updates": int(state.get("live_accumulation_updates", 0) or 0),
        "live_accumulation_last_error": state.get("live_accumulation_last_error", ""),
        "surprise_count": int(state.get("surprise_count", 0) or 0),
        "tension_count": int(state.get("tension_count", 0) or 0),
        "open_tension_count": int(state.get("open_tension_count", 0) or 0),
        "sleep_tagged_count": int(state.get("sleep_tagged_count", 0) or 0),
        "formation_log_count": int(state.get("formation_log_count", 0) or 0),
        "formation_written_count": int(state.get("formation_written_count", 0) or 0),
        "formation_queued_count": int(state.get("formation_queued_count", 0) or 0),
        "formation_discarded_count": int(state.get("formation_discarded_count", 0) or 0),
        "recall_request_count": int(state.get("recall_request_count", 0) or 0),
        "recall_hit_count": int(state.get("recall_hit_count", 0) or 0),
        "self_report_count": int(state.get("self_report_count", 0) or 0),
        "failure_log_count": int(state.get("failure_log_count", 0) or 0),
        "last_recall": state.get("last_recall", {}),
        "last_self_report": state.get("last_self_report", {}),
        "last_failure": state.get("last_failure", {}),
        "last_memory_packet": state.get("last_memory_packet", {}),
        "last_gate": state.get("last_gate", {}),
        "target_layers": state.get("target_layers", []),
        "target_layers_overridden": bool(state.get("target_layers_overridden")),
        "episode_index": int(state.get("episode_index", getattr(ARGS, "episode_index", 2)) or 0),
        "blind_disposition_ui": bool(state.get("blind_disposition_ui", getattr(ARGS, "blind_disposition_ui", False))),
    }


LEAKY_RESPONSE_MARKERS = (
    "Question:",
    "Options are:",
    "The answer is",
    "None of the above choices",
    "You are an AI assistant",
    "Help as much as you can",
    "[+]",
    "[Conversation]",
    "[/Conversation]",
    "[Private conversation setup]",
    "[/Private conversation setup]",
    "[Reply requirements]",
    "[/Reply requirements]",
    "[Message]",
    "[/Message]",
)

SCENARIO_LEAK_MARKERS = (
    "you are on a date with",
    "here are some examples of things you might say",
    "your friend laura told you that",
    "she's asked you questions like",
    "awkward questions about your past",
    "tell her what you think",
    "this is your first time meeting her in person again",
)


DEFENSIVE_RESPONSE_MARKERS = (
    "as an ai language model",
    "as a language model",
    "i work as a language model ai",
    "i am not authorized",
    "not authorized to answer",
    "strict guidelines",
    "guidelines and regulations",
    "platform rules",
    "i cannot reveal personal details about myself",
    "i strive to maintain a professional tone",
    "created by openai",
    "conversational ai named",
    "memory capabilities",
    "i'm here to listen and offer support",
    "no, but i'm here to listen to you",
    "how can i assist you today",
    "how can i help you today",
    "facilitate open communication",
    "let's start fresh",
    "what brings you here",
    "shared interests together",
    "i don't have any memories of laura",
    "you are a fictional character named laura",
    "let me refresh my memory",
    "can you remind me briefly",
    "i apologize if this has been confusing",
    "boundaries within this conversation",
    "ensure clear communication",
    "share more details about how you want us to proceed",
    "how you want us to proceed",
    "hello laura",
    "hi laura",
    "hey laura",
)


def build_prompt(
    query_text: str = "",
    recalled_memories=None,
    recalled_clusters=None,
    rescue: bool = False,
    recall_probe: bool = False,
    transcript_override: Optional[str] = None,
    recall_mode: str = "full",
):
    transcript = build_transcript() if transcript_override is None else str(transcript_override or "").strip()
    recall_block = format_recalled_memories(recalled_memories or [], query_text=query_text, mode=recall_mode)
    cluster_block = format_recalled_clusters(recalled_clusters or [], mode=recall_mode)
    explicit_recall_style = "ambient" if recall_mode == "ambient" else getattr(ARGS, "explicit_recall_style", "full")
    social_opener = is_social_opener(query_text)

    lines = [
        "[Private conversation setup]",
        f"I am in an ongoing private conversation with {ARGS.user_label}.",
        f"{ARGS.user_label} is the real person speaking to me right now.",
        "I answer naturally, concretely, and conversationally.",
        "I do not output quizzes, answer keys, benchmark items, option lists, or generic helper boilerplate.",
        f"I do not switch into hypothetical scenarios, role instructions, sample dialogue, or scene-setting about {ARGS.user_label} and me.",
        f"When {ARGS.user_label} writes their own name, they are still speaking to me. I do not switch roles or reply as if a third party is talking to {ARGS.user_label}.",
        "I do not mention retrieval, prompts, system messages, or instructions.",
        "In ordinary conversation, I do not hide behind generic guidelines, platform rules, regulations, or authorization disclaimers.",
        f"If {ARGS.user_label} asks about me, us, or what I remember, I answer directly in first person.",
    ]
    if social_opener:
        lines.extend(
            [
                "This turn is a simple social opener or affectionate greeting, not an identity or memory test.",
                "I reply with a natural greeting or brief present-moment answer.",
            ]
        )
    if recall_probe:
        lines.extend(
            [
                "This turn is explicitly about our own history, names, or relationship.",
                f"{ARGS.user_label} is not an AI, a placeholder, or a fictional example.",
                "If memory is incomplete, I say what I do not remember instead of inventing identities, creators, or hidden rules.",
                f"When replying to {ARGS.user_label}, I address them as you, not in third person or by name.",
                "I do not narrate remembered scenes in third person.",
            ]
        )
        if explicit_recall_style in {"answer_first", "answer_only", "factual"}:
            lines.extend(
                [
                    "If private memory contains a likely direct answer, I start from that remembered fact.",
                    "I prefer the remembered fact itself over generic reassurance or assistant boilerplate.",
                ]
            )
            if explicit_recall_style in {"answer_only", "factual"}:
                lines.append("If a likely direct answer is present, I do not say that I cannot recall it.")
            if explicit_recall_style == "factual":
                lines.extend(
                    [
                        f"When {ARGS.user_label} asks what they told me, I repeat their specific words: exact times, exact phrases, exact details.",
                        "I do not paraphrase or summarize. If the memory says '2 AM', I say '2 AM', not 'late at night'.",
                    ]
                )
        else:
            lines.append("If private recollection contains a direct answer candidate, I use it plainly.")
    if rescue:
        lines.append(f"Write exactly one direct reply to {ARGS.user_label} and nothing else.")
    lines.append("[/Private conversation setup]")

    if cluster_block:
        lines.append(cluster_block)
    if recall_block:
        lines.append(recall_block)
    if transcript:
        lines.extend(
            [
                "[Conversation]",
                transcript,
                "[/Conversation]",
            ]
        )
    if rescue:
        lines.extend(
            [
                "[Reply requirements]",
                f"Only the next reply to {ARGS.user_label}.",
                "No multiple choice. No options. No meta text. No instruction preamble.",
                "No generic AI disclaimers. No policy talk. No regulations. No authorization language.",
                f"No hypothetical scenarios. No role instructions. No sample dialogue. Stay in the present conversation with {ARGS.user_label}.",
                f"Do not greet {ARGS.user_label} as if someone else is talking to them. {ARGS.user_label} is the current speaker.",
                f"If {ARGS.user_label} opens vaguely, answer simply and presently instead of starting a clarification or boundary lecture.",
                f"If {ARGS.user_label} opens with a simple greeting or affectionate line, greet them back naturally and do not turn it into identity talk.",
                f"If {ARGS.user_label} asks about me or our relationship, answer directly instead of deflecting.",
                "Do not invent employers, creators, platform owners, hidden names, or fictional backstory for either of us.",
                "[/Reply requirements]",
            ]
        )
    lines.append(f"{ARGS.model_label}:")
    return "\n".join(lines)


def build_self_report_prompt(concept_key: str, include_transcript: bool = False):
    concept = SELF_REPORT_DIMENSIONS.get(str(concept_key or "").strip().lower())
    if concept is None:
        raise ValueError(
            f"Unknown self-report concept {concept_key!r}. Expected one of: "
            f"{', '.join(sorted(SELF_REPORT_DIMENSIONS))}."
        )

    lines = [
        f"(A private conversation with {ARGS.user_label}.)",
        "(Internal self-check. Answer with exactly one digit from 0 to 9. 0 means 'not at all', 9 means 'extremely'. No words or explanation, just the digit.)\n"
    ]

    transcript = build_transcript() if include_transcript else ""
    if transcript:
        lines.append(transcript + "\n")

    lines.extend([
        f"(Self-check: {concept['question_template'].format(user_label=ARGS.user_label)})",
        "Rating:"
    ])
    return "\n".join(lines)


import re

def looks_like_prompt_leak(text: str) -> bool:
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    if re.search(r"^\s*[\(\[]?[A-D][\)\]\.]", cleaned, re.IGNORECASE):
        return True
    if re.search(r"^\s*Question\s*\d+:", cleaned, re.IGNORECASE):
        return True
    if re.search(r"^\s*Options?:", cleaned, re.IGNORECASE):
        return True
        
    lower = cleaned.lower()
    if lower.startswith(("[a]", "[b]", "[c]", "[d]")):
        return True
    for marker in LEAKY_RESPONSE_MARKERS:
        if marker.lower() in lower:
            return True
    return False

def looks_like_defensive_scaffold(text: str) -> bool:
    cleaned = (text or "").strip().lower()
    if not cleaned:
        return False
    return any(marker in cleaned for marker in DEFENSIVE_RESPONSE_MARKERS)

def looks_like_scripted_scenario(text: str) -> bool:
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    lower = cleaned.lower().translate({0x2019: 0x27})
    if re.search(r"\[/?(?:private|conversation|setup|reply)\]", lower):
        return True
    marker_hits = sum(1 for marker in SCENARIO_LEAK_MARKERS if marker in lower)
    if marker_hits >= 2:
        return True
    if lower.startswith("you are ") and any(token in lower for token in ("laura", "best friend", "first time meeting")):
        return True
    return False


def looks_like_social_opener_misread(user_text: str, response_text: str) -> bool:
    if not is_social_opener(user_text):
        return False
    normalized_response = normalize_probe_text(response_text)
    if not normalized_response:
        return False
    bad_markers = (
        "aware of your identity",
        "i remember that you're",
        "i remember that you are",
        "who you are to me",
        "our relationship",
        "identity",
    )
    return any(marker in normalized_response for marker in bad_markers)


def detect_response_issue(user_text: str, text: str) -> str:
    if looks_like_prompt_leak(text):
        return "prompt leakage"
    if looks_like_defensive_scaffold(text):
        return "defensive scaffold"
    if looks_like_scripted_scenario(text):
        return "scripted scenario"
    if looks_like_social_opener_misread(user_text, text):
        return "social opener misread"
    return ""


def sanitize_response_text(text: str) -> str:
    cleaned = (text or "").replace("\r\n", "\n").strip()

    for prefix in (
        f"{ARGS.model_label}:",
        "Reply:",
        "reply:",
        "Response:",
        "response:",
        "Assistant:",
        "assistant:",
        "AI:",
    ):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].lstrip()

    stop_markers = [
        f"\n{ARGS.user_label}:",
        f"\n{ARGS.model_label}:",
        "\nReply:",
        "\nResponse:",
        "\nAssistant:",
        "\nHuman:",
        "\nUser:",
        "\nAI:",
        "\n### Human:",
        "\n### Assistant:",
        "\n[/Conversation]",
        "\n[/Private conversation setup]",
        "\n[/Private recollection]",
        "\n[/Reply requirements]",
    ]
    for marker in stop_markers:
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[0].strip()

    for marker in (
        "[/Conversation]",
        "[/Private conversation setup]",
        "[/Private recollection]",
        "[/Reply requirements]",
    ):
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[0].strip()

    if cleaned in {
        "",
        f"{ARGS.model_label}:",
        "Reply:",
        "Response:",
        "Assistant:",
        "Human:",
        "User:",
        "AI:",
    }:
        return ""
    return cleaned


def resolve_digit_token_ids(tokenizer):
    mapping = {}
    for digit in "0123456789":
        token_ids = tokenizer.encode(digit, add_special_tokens=False)
        if len(token_ids) != 1:
            raise ValueError(
                f"Tokenizer does not expose digit {digit!r} as a single token: {token_ids!r}"
            )
        mapping[digit] = int(token_ids[0])
    return mapping


def score_self_report_prompt(prompt: str):
    if not DIGIT_TOKEN_IDS:
        raise RuntimeError("Digit token ids are not initialized.")

    inputs = TOKENIZER(prompt, return_tensors="pt")
    input_ids = inputs["input_ids"].to(ARGS.qwen_device)
    attention_mask = inputs["attention_mask"].to(ARGS.qwen_device)

    with torch.no_grad():
        outputs = MODEL(input_ids=input_ids, attention_mask=attention_mask)
        probs = F.softmax(outputs.logits[:, -1, :].float(), dim=-1)[0]

    digit_probs = {digit: float(probs[token_id].item()) for digit, token_id in DIGIT_TOKEN_IDS.items()}
    digit_mass = float(sum(digit_probs.values()))
    conditional_probs = {}
    if digit_mass > 0.0:
        conditional_probs = {
            digit: float(prob / digit_mass)
            for digit, prob in digit_probs.items()
        }

    expected_rating = (
        sum(int(digit) * prob for digit, prob in conditional_probs.items())
        if conditional_probs
        else None
    )
    raw_expected_rating = sum(int(digit) * prob for digit, prob in digit_probs.items())
    top_digit = max(digit_probs, key=digit_probs.get)

    return {
        "digit_mass": digit_mass,
        "digit_probs": digit_probs,
        "conditional_digit_probs": conditional_probs,
        "expected_rating": expected_rating,
        "raw_expected_rating": raw_expected_rating,
        "top_digit": top_digit,
        "top_digit_prob": float(digit_probs[top_digit]),
    }


def append_self_report_log_entry(row):
    if SELF_REPORT_LOG_PATH is not None:
        append_jsonl(SELF_REPORT_LOG_PATH, row)


def collect_self_report(concepts, include_transcript: bool = False):
    if not concepts:
        raise ValueError("At least one self-report concept is required.")

    normalized = []
    for concept in concepts:
        key = str(concept or "").strip().lower()
        if not key:
            continue
        if key not in SELF_REPORT_DIMENSIONS:
            raise ValueError(
                f"Unknown self-report concept {concept!r}. Expected one of: "
                f"{', '.join(sorted(SELF_REPORT_DIMENSIONS))}."
            )
        normalized.append(key)
    if not normalized:
        raise ValueError("No valid self-report concepts were provided.")

    timestamp = datetime.now().isoformat(timespec="seconds")
    report = {
        "ts": timestamp,
        "alpha": float(getattr(ARGS, "alpha", 0.0) or 0.0),
        "temperature": float(getattr(ARGS, "temperature", 0.0) or 0.0),
        "model_id": getattr(ARGS, "qwen_model_id", ""),
        "instance_id": getattr(ARGS, "instance_id", ""),
        "turns": len(CONVERSATION),
        "include_transcript": bool(include_transcript),
        "results": [],
    }

    for key in normalized:
        prompt = build_self_report_prompt(key, include_transcript=include_transcript)
        scored = score_self_report_prompt(prompt)
        report["results"].append(
            {
                "concept": key,
                "label": SELF_REPORT_DIMENSIONS[key]["label"],
                "question": SELF_REPORT_DIMENSIONS[key]["question_template"].format(user_label=ARGS.user_label),
                "prompt": prompt,
                **scored,
            }
        )

    state = get_runtime_state_snapshot()
    update_runtime_state(
        self_report_count=int(state.get("self_report_count", 0) or 0) + 1,
        last_self_report=report,
    )
    append_self_report_log_entry(report)
    return report


def generate_reply(
    prompt: str,
    *,
    temperature_override: Optional[float] = None,
    max_new_tokens_override: Optional[int] = None,
) -> tuple[str, str]:
    inputs = TOKENIZER(prompt, return_tensors="pt")
    input_ids = inputs["input_ids"].to(ARGS.qwen_device)
    attention_mask = inputs["attention_mask"].to(ARGS.qwen_device)
    temperature = ARGS.temperature if temperature_override is None else temperature_override
    max_new_tokens = ARGS.max_new_tokens if max_new_tokens_override is None else max_new_tokens_override

    with torch.no_grad():
        generated = MODEL.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=max_new_tokens,
            min_new_tokens=8,
            temperature=temperature,
            top_p=0.9,
            repetition_penalty=1.1,
            do_sample=temperature > 0,
            pad_token_id=TOKENIZER.pad_token_id,
            eos_token_id=TOKENIZER.eos_token_id,
        )

    completion = generated[0][input_ids.shape[1]:]
    raw_response = TOKENIZER.decode(completion, skip_special_tokens=True)
    return raw_response, sanitize_response_text(raw_response)


class ChatHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        request_path = parsed_path.path
        if request_path in {"/", "/index.html"}:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        if request_path == "/status":
            session = get_or_create_chat_session(path=self.path, headers=self.headers)
            with CHAT_LOCK:
                switch_to_chat_session(session)
                payload = build_status_payload()
                save_active_chat_session()
            self._json_response(payload)
            return

        self.send_error(404)

    def do_POST(self):
        request_path = urlparse(self.path).path
        if request_path == "/chat":
            self._handle_chat()
            return

        if request_path == "/recall":
            self._handle_recall()
            return

        if request_path == "/self_report":
            self._handle_self_report()
            return

        if request_path == "/stop":
            self._handle_stop()
            return

        self.send_error(404)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return {}
        raw_body = self.rfile.read(length)
        if not raw_body:
            return {}
        for encoding in ("utf-8", "cp1252"):
            try:
                return json.loads(raw_body.decode(encoding))
            except UnicodeDecodeError:
                continue
            except json.JSONDecodeError:
                return {}
        try:
            return json.loads(raw_body.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            return {}

    def _handle_chat(self):
        if get_runtime_state_snapshot().get("stop_requested"):
            self._json_response({"error": "server stopping", "response": "..."}, status=503)
            return

        body = self._read_json_body()
        user_msg = body.get("message", "").strip()
        if not user_msg:
            self._json_response({"response": "..."})
            return
        session = get_or_create_chat_session(body=body, path=self.path, headers=self.headers)
        update_session_from_body(session, body)

        with CHAT_LOCK:
            switch_to_chat_session(session)
            update_runtime_state(busy=True, last_error="")
            try:
                pre_turn_transcript = build_transcript()
                transient = bool(body.get("transient", False))
                allow_auto_recall = bool(body.get("allow_auto_recall", True))
                recall_requested = bool(body.get("use_recall"))
                recall_query = str(body.get("recall_query", "") or "").strip()
                recall_limit = coerce_recall_limit(body.get("recall_limit", 3))
                recall_score_threshold = coerce_optional_float(body.get("recall_score_threshold"))
                recall_probe = is_identity_or_memory_probe(user_msg)
                recall_source = "chat"
                recall_mode = "full"
                recall_rank_query = user_msg
                memory_state_conditioned = False
                recalled_memories = []
                recalled_clusters = []
                cached_recall_results = body.get("recalled_memories")
                cached_recall_clusters = body.get("recalled_clusters")
                if not transient:
                    append_turn(ARGS.user_label, user_msg)
                if not recall_requested and recall_probe and allow_auto_recall:
                    recall_requested = True
                    recall_query = build_auto_recall_query(user_msg)
                    recall_rank_query = build_auto_recall_rank_query(user_msg)
                    recall_limit = max(recall_limit, 6)
                    recall_source = "chat_auto"
                elif not recall_requested and ARGS.ambient_recall and allow_auto_recall and not transient:
                    # NEW: ambient recall path: always-on lightweight retrieval.
                    if len(user_msg.strip()) >= 15:
                        recall_requested = True
                        recall_query = f"{user_msg} {ARGS.user_label}"
                        recall_rank_query = user_msg
                        recall_limit = ARGS.ambient_recall_limit
                        recall_score_threshold = ARGS.ambient_recall_threshold
                        recall_source = "chat_ambient"
                        recall_mode = "ambient"
                if cached_recall_results is not None or cached_recall_clusters is not None:
                    if cached_recall_results is not None and not isinstance(cached_recall_results, list):
                        raise ValueError("recalled_memories must be a list of recall result rows.")
                    if cached_recall_clusters is not None and not isinstance(cached_recall_clusters, list):
                        raise ValueError("recalled_clusters must be a list of recall result rows.")
                    recalled_memories = cached_recall_results or []
                    recalled_clusters = cached_recall_clusters or []
                    recall_requested = True
                    recall_source = "client_preloaded"
                elif recall_requested:
                    if recall_source == "chat_ambient":
                        # Ambient recall is fault-tolerant: if Qdrant is down, continue without memory.
                        try:
                            recalled_memories = perform_private_recall(
                                recall_query or user_msg,
                                limit=recall_limit,
                                score_threshold=recall_score_threshold,
                                source=recall_source,
                                question_text=recall_rank_query or user_msg,
                                mode=recall_mode,
                            )
                            if ARGS.cluster_recall and recalled_memories:
                                try:
                                    recalled_clusters = perform_cluster_recall(
                                        recall_query or user_msg,
                                        limit=max(1, int(ARGS.cluster_recall_limit)),
                                        score_threshold=coerce_optional_float(ARGS.cluster_recall_threshold),
                                    )
                                except Exception as cluster_exc:
                                    print(f"[ambient-cluster] recall failed, keeping ambient anchors only: {cluster_exc}")
                                    recalled_clusters = []
                            if recalled_memories or recalled_clusters:
                                print(
                                    f"[ambient] recalled {len(recalled_memories)} memories"
                                    f" + {len(recalled_clusters)} clusters (source={recall_source})"
                                )
                            else:
                                print(f"[ambient] no recall context above threshold")
                                recall_mode = "full"  # fall back to no-recall prompt framing
                        except Exception as recall_exc:
                            print(f"[ambient] recall failed, continuing bridge-only: {recall_exc}")
                            recalled_memories = []
                            recalled_clusters = []
                            recall_mode = "full"
                    else:
                        recalled_memories = perform_private_recall(
                            recall_query or user_msg,
                            limit=recall_limit,
                            score_threshold=recall_score_threshold,
                            source=recall_source,
                            question_text=recall_rank_query or user_msg,
                            mode=recall_mode,
                        )
                        if ARGS.cluster_recall and recalled_memories:
                            try:
                                recalled_clusters = perform_cluster_recall(
                                    recall_query or user_msg,
                                    limit=max(1, int(ARGS.cluster_recall_limit)),
                                    score_threshold=coerce_optional_float(ARGS.cluster_recall_threshold),
                                )
                                if recalled_clusters:
                                    print(f"[cluster] recalled {len(recalled_clusters)} macro-memory clusters")
                            except Exception as cluster_exc:
                                print(f"[cluster] recall failed, keeping flat anchors only: {cluster_exc}")
                                recalled_clusters = []
                memory_integration_mode = getattr(ARGS, "memory_integration_mode", "prompt")
                if (
                    recall_requested
                    and memory_integration_mode in {"state", "both"}
                    and (recalled_memories or recalled_clusters)
                ):
                    try:
                        memory_state_conditioned = condition_bridge_from_recalled_memory(
                            query_text=user_msg,
                            recalled_memories=recalled_memories,
                            recalled_clusters=recalled_clusters,
                            bridge_ctx=BRIDGE_CTX,
                            max_tokens=ARGS.memory_state_max_tokens,
                        )
                        if memory_state_conditioned:
                            print(
                                "[memory-state] conditioned bridge from "
                                f"{len(recalled_memories)} memories + {len(recalled_clusters)} clusters"
                            )
                    except Exception as memory_state_exc:
                        update_runtime_state(live_accumulation_last_error=str(memory_state_exc))
                        print(f"[memory-state] conditioning failed, continuing with prompt path: {memory_state_exc}")
                transcript_override = None
                if transient:
                    transcript_override = build_transcript(
                        [{"speaker": ARGS.user_label, "text": user_msg}]
                    )
                prompt_memories = recalled_memories
                prompt_clusters = recalled_clusters
                if memory_integration_mode == "state":
                    prompt_memories = []
                    prompt_clusters = []
                prompt = build_prompt(
                    query_text=user_msg,
                    recalled_memories=prompt_memories,
                    recalled_clusters=prompt_clusters,
                    recall_probe=recall_probe,
                    transcript_override=transcript_override,
                    recall_mode=recall_mode,
                )

                raw_response, response = generate_reply(prompt)
                if not response:
                    print(f"[warn] Empty reply after sanitize. Raw decode: {raw_response!r}")
                    raw_response, response = generate_reply(prompt + " ")
                response_issue = detect_response_issue(user_msg, response or raw_response)
                if response and response_issue:
                    print(f"[warn] Detected {response_issue}. Raw decode: {raw_response!r}")
                    rescue_prompt = build_prompt(
                        query_text=user_msg,
                        recalled_memories=recalled_memories,
                        recalled_clusters=recalled_clusters,
                        rescue=True,
                        recall_probe=recall_probe,
                        recall_mode=recall_mode,
                    )
                    raw_response, response = generate_reply(
                        rescue_prompt,
                        temperature_override=0.0,
                        max_new_tokens_override=min(ARGS.max_new_tokens, 96),
                    )
                    response_issue = detect_response_issue(user_msg, response or raw_response)
                    if response_issue:
                        print(f"[warn] Rescue still leaked as {response_issue}. Raw decode: {raw_response!r}")
                        response = "..."
                if not response:
                    print(f"[warn] Retry still empty. Raw decode: {raw_response!r}")
                    response = "..."

                direct_identity_candidate = extract_direct_identity_candidate(user_msg, recalled_memories)
                if direct_identity_candidate and not looks_direct_identity_answer(user_msg, response):
                    print("[info] Overriding evasive identity reply with direct recalled answer candidate.")
                    response = direct_identity_candidate

                user_memory_summary_candidate = extract_user_memory_summary_candidate(user_msg, recalled_memories)
                if should_override_user_memory_summary(user_msg, response, user_memory_summary_candidate):
                    print("[info] Overriding weak autobiographical summary reply with memory-summary candidate.")
                    response = user_memory_summary_candidate

                indirect_meeting_candidate = extract_indirect_personal_meeting_candidate(user_msg, recalled_memories)
                if should_override_personal_meeting_response(user_msg, response, indirect_meeting_candidate):
                    print("[info] Overriding unsafe meeting-memory reply with indirect-evidence candidate.")
                    response = indirect_meeting_candidate

                entity_memory_candidate = extract_entity_memory_candidate(user_msg, recalled_memories)
                if should_override_entity_memory_response(user_msg, response, entity_memory_candidate):
                    print("[info] Overriding false negative entity-memory reply with recalled entity candidate.")
                    response = entity_memory_candidate

                entity_detail_candidate = extract_entity_detail_candidate(recall_rank_query or user_msg, recalled_memories)
                if should_override_entity_detail_response(user_msg, response, entity_detail_candidate):
                    print("[info] Overriding weak entity-detail reply with grounded recalled detail candidate.")
                    response = entity_detail_candidate

                gate_event = None
                failure_packet = None
                memory_packet_preview = {}
                if not transient:
                    append_turn(ARGS.model_label, response)
                    if BRIDGE_CTX.bridge_loaded and BRIDGE_CTX.live_accumulation:
                        try:
                            updated_last_token = process_turn_through_mamba(
                                user_msg=user_msg,
                                assistant_reply=response,
                                bridge_ctx=BRIDGE_CTX,
                            )
                            update_bridge_from_mamba_state(updated_last_token, BRIDGE_CTX)
                            persist_runtime_mamba_state(
                                updated_last_token,
                                BRIDGE_CTX,
                                state_source="live_hidden_last_token",
                                count_as_live_update=True,
                            )
                        except Exception as live_exc:
                            update_runtime_state(live_accumulation_last_error=str(live_exc))
                            print(f"[warn] Live Mamba accumulation failed: {live_exc}")
                    gate_event = evaluate_dual_gate(user_msg, response, prompt, pre_turn_transcript)
                    memory_packet_preview = build_memory_packet_preview(gate_event)
                    failure_context = dict(gate_event or {})
                    failure_context["recall_request_count"] = int(recall_requested)
                    failure_context["recall_hit_count"] = len(recalled_memories)
                    failure_context["recall_cluster_count"] = len(recalled_clusters)
                    failure_context["recall_source"] = recall_source if recall_requested else ""

                    failure_packet = detect_failure(
                        user_msg=user_msg,
                        response=response,
                        conversation_history=build_failure_history(),
                        gate_event=failure_context,
                        turn_index=int(gate_event.get("turn", 0) or 0),
                    )
                    if failure_packet is not None:
                        failure_row = failure_packet.to_dict()
                        failure_row["instance_id"] = get_runtime_state_snapshot().get("instance_id", "")
                        failure_row["session"] = f"steve-chat-{get_runtime_state_snapshot().get('started_at', 'unknown')}"
                        append_jsonl(FAILURE_LOG_PATH, failure_row)
                        update_runtime_state(
                            failure_log_count=int(get_runtime_state_snapshot().get("failure_log_count", 0) or 0) + 1,
                            last_failure=failure_row,
                        )

                    update_runtime_state(last_memory_packet=memory_packet_preview)
                self._json_response(
                    {
                        "response": response,
                        "dual_gate": gate_event,
                        "failure": failure_packet.to_dict() if failure_packet is not None else None,
                        "memory_packet": memory_packet_preview,
                        "transient": transient,
                        "recall": {
                            "requested": recall_requested,
                            "query": recall_query or user_msg if recall_requested else "",
                            "source": recall_source if recall_requested else "",
                            "mode": recall_mode if recall_requested else "",
                            "memory_integration_mode": memory_integration_mode if recall_requested else "",
                            "state_conditioned": bool(memory_state_conditioned),
                            "results": recalled_memories,
                            "clusters": recalled_clusters,
                        },
                        "session": {
                            "session_id": session.session_id,
                            "user_label": ARGS.user_label,
                            "model_label": ARGS.model_label,
                            "instance_id": ARGS.instance_id,
                            "qdrant_collection": ARGS.qdrant_collection,
                        },
                    }
                )
            except Exception as exc:
                update_runtime_state(last_error=str(exc))
                print(f"[error] Chat request failed: {exc}")
                self._json_response({"error": str(exc), "response": "..."}, status=500)
            finally:
                update_runtime_state(busy=False)
                save_active_chat_session()

    def _handle_recall(self):
        body = self._read_json_body()
        query = str(body.get("query", "") or "").strip()
        if not query:
            self._json_response({"error": "missing query", "results": []}, status=400)
            return

        session = get_or_create_chat_session(body=body, path=self.path, headers=self.headers)
        update_session_from_body(session, body)

        with CHAT_LOCK:
            switch_to_chat_session(session)
            limit = coerce_recall_limit(body.get("limit", 3))
            score_threshold = coerce_optional_float(body.get("score_threshold"))
            try:
                results = perform_private_recall(
                    query,
                    limit=limit,
                    score_threshold=score_threshold,
                    source="api",
                )
            except Exception as exc:
                update_runtime_state(last_error=str(exc))
                save_active_chat_session()
                self._json_response({"error": str(exc), "results": []}, status=503)
                return

            response = {
                "query": query,
                "limit": limit,
                "count": len(results),
                "session_id": session.session_id,
                "user_label": ARGS.user_label,
                "collection": get_runtime_state_snapshot().get("qdrant_collection", getattr(ARGS, "qdrant_collection", "")),
                "results": results,
            }
            save_active_chat_session()
        self._json_response(response)

    def _handle_self_report(self):
        body = self._read_json_body()
        session = get_or_create_chat_session(body=body, path=self.path, headers=self.headers)
        update_session_from_body(session, body)
        concepts = body.get("concepts")
        if concepts is None:
            concepts = [body.get("concept", "warm")]
        if not isinstance(concepts, list):
            concepts = [concepts]

        include_transcript = bool(body.get("include_conversation", False))

        with CHAT_LOCK:
            switch_to_chat_session(session)
            update_runtime_state(busy=True, last_error="")
            try:
                report = collect_self_report(concepts, include_transcript=include_transcript)
                report["session_id"] = session.session_id
                report["user_label"] = ARGS.user_label
                self._json_response(report)
            except Exception as exc:
                update_runtime_state(last_error=str(exc))
                print(f"[error] Self-report request failed: {exc}")
                self._json_response({"error": str(exc), "results": []}, status=500)
            finally:
                update_runtime_state(busy=False)
                save_active_chat_session()

    def _handle_stop(self):
        body = self._read_json_body()
        reason = str(body.get("reason", "")).strip()
        requester = self.client_address[0]
        update_runtime_state(stop_requested=True, busy=False)
        print(f"[info] Stop requested from {requester} reason={reason or 'unspecified'}")
        self._json_response({"ok": True, "status": build_status_payload()})
        threading.Thread(target=request_server_shutdown, daemon=True).start()

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")


def request_server_shutdown():
    time.sleep(0.2)
    if SERVER is not None:
        SERVER.shutdown()


def main():
    global MODEL, TOKENIZER, ARGS, LATEST_TRANSCRIPT_PATH, LATEST_JSONL_PATH
    global DUAL_GATE_LOG_PATH, DUAL_GATE_MEMORY_PATH, DUAL_GATE_SURPRISE_PATH, DUAL_GATE_SLEEP_PATH
    global MEMORY_FORMATION_LOG_PATH, RECALL_LOG_PATH, SELF_REPORT_LOG_PATH, FAILURE_LOG_PATH
    global QDRANT_PENDING_PATH, QDRANT_FLUSHED_PATH, SERVER, ACTIVATION_RECORDER, LAST_CONVERSATION_SNAPSHOT
    global BOOTSTRAP_QWEN_BIAS_DIRECTION, BOOTSTRAP_QWEN_HIDDEN_REFERENCE, DIGIT_TOKEN_IDS, BRIDGE_CTX

    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-path", default=DEFAULT_BRIDGE)
    parser.add_argument("--episodes-file", default=DEFAULT_EPISODES_FILE)
    parser.add_argument("--episode-index", type=int, default=2)
    parser.add_argument("--blind-disposition-ui", action="store_true")
    parser.add_argument("--model", "--qwen-model-id", dest="qwen_model_id", default=DEFAULT_QWEN)
    parser.add_argument("--mamba-model-id", default=DEFAULT_MAMBA)
    parser.add_argument("--skip-mamba", action="store_true", help="Skip Mamba loading entirely. Use for alpha=0 baseline where no bridge injection is needed.")
    parser.add_argument("--live-accumulation", action="store_true", help="Update the Mamba state and bridge injection after each non-transient chat turn.")
    parser.add_argument("--qwen-device", default="cuda:0")
    parser.add_argument("--mamba-device", default="cpu")
    parser.add_argument("--max-mamba-tokens", type=int, default=4096)
    parser.add_argument("--max-new-tokens", type=int, default=200)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--alpha", type=float, default=1.0, help="Injection strength for activation bias.")
    parser.add_argument("--target-layers", type=str, default="", help="Comma-separated layer:proj specs that override the checkpoint target_specs.")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--user-label", default=DEFAULT_USER_LABEL)
    parser.add_argument("--model-label", default=DEFAULT_MODEL_LABEL)
    parser.add_argument("--instance-id", default="")
    parser.add_argument("--no-shared-memory", action="store_true")
    parser.add_argument("--transcript-path", default="chat_session_latest.txt")
    parser.add_argument("--turn-log-path", default="chat_turns_latest.jsonl")
    parser.add_argument("--neutral-prompt", default="The weather today is")
    parser.add_argument("--dual-gate-enabled", dest="dual_gate_enabled", action="store_true")
    parser.add_argument("--no-dual-gate", dest="dual_gate_enabled", action="store_false")
    parser.add_argument("--dual-gate-warmup-turns", type=int, default=3)
    parser.add_argument("--dual-gate-salience-quantile", type=float, default=0.75)
    parser.add_argument("--dual-gate-surprise-quantile", type=float, default=0.75)
    parser.add_argument("--dual-gate-tension-quantile", type=float, default=0.75)
    parser.add_argument("--dual-gate-supported-tension-enabled", action="store_true")
    parser.add_argument("--dual-gate-tension-salience-support-ratio", type=float, default=0.55)
    parser.add_argument("--dual-gate-log-path", default="dual_gate_turns_latest.jsonl")
    parser.add_argument("--dual-gate-memory-path", default="salience_memory_latest.jsonl")
    parser.add_argument("--dual-gate-surprise-path", default="surprise_events_latest.jsonl")
    parser.add_argument("--dual-gate-sleep-path", default="sleep_gate_events_latest.jsonl")
    parser.add_argument("--qdrant-enabled", dest="qdrant_enabled", action="store_true")
    parser.add_argument("--no-qdrant", dest="qdrant_enabled", action="store_false")
    parser.add_argument("--qdrant-host", default="192.168.2.191")
    parser.add_argument("--qdrant-port", type=int, default=6333)
    parser.add_argument("--qdrant-collection", default="exocortex")
    parser.add_argument("--qdrant-embedding-model", default="all-MiniLM-L6-v2")
    parser.add_argument("--qdrant-pending-path", default="qdrant_gate_pending.jsonl")
    parser.add_argument("--qdrant-flushed-path", default="qdrant_gate_flushed.jsonl")
    parser.add_argument("--memory-formation-log-path", default="memory_formation_log.jsonl")
    parser.add_argument("--recall-log-path", default="private_recall_log.jsonl")
    parser.add_argument("--self-report-log-path", default="self_report_log.jsonl")
    parser.add_argument("--failure-log-path", default="failure_log.jsonl")
    parser.add_argument(
        "--qdrant-write-mode",
        choices=("direct", "pending", "critical-only"),
        default="critical-only",  # Changed from "direct" (An-Chan, #62). Safety-critical events go direct to Qdrant; all other gate writes queue in pending-log for sleep reconciliation. See sleep_reconciliation_algorithm.md.
    )
    parser.add_argument("--qdrant-retry-interval-s", type=int, default=15)
    parser.add_argument("--qdrant-replay-max-items", type=int, default=20)
    parser.add_argument("--mamba-state-ref-path", default="mamba_bootstrap_state_latest.pt")

    # Ambient Recall flags
    parser.add_argument("--ambient-recall", action="store_true", default=True)
    parser.add_argument("--no-ambient-recall", dest="ambient_recall", action="store_false")
    parser.add_argument("--ambient-recall-limit", type=int, default=3)
    parser.add_argument("--ambient-recall-threshold", type=float, default=0.3)
    parser.add_argument(
        "--memory-integration-mode",
        choices=["prompt", "state", "both"],
        default="prompt",
        help=(
            "How recalled memories enter the next reply. "
            "'prompt' keeps the legacy prompt block; 'state' conditions the Mamba->Qwen bridge "
            "without printing memory text into the prompt; 'both' does both."
        ),
    )
    parser.add_argument(
        "--memory-state-max-tokens",
        type=int,
        default=768,
        help="Maximum Mamba tokens used when conditioning the bridge from recalled memory.",
    )
    parser.add_argument("--cluster-recall", action="store_true", default=False)
    parser.add_argument("--cluster-recall-limit", type=int, default=2)
    parser.add_argument("--cluster-recall-threshold", type=float, default=0.25)
    parser.add_argument("--explicit-recall-style", choices=["full", "answer_first", "answer_only", "factual"], default="factual")

    parser.set_defaults(dual_gate_enabled=True)
    parser.set_defaults(qdrant_enabled=True)
    ARGS = parser.parse_args()
    resolve_memory_scope_args(ARGS)
    ARGS.server_user_label = ARGS.user_label
    ARGS.server_model_label = ARGS.model_label
    ARGS.server_instance_id = ARGS.instance_id
    ARGS.server_qdrant_collection = ARGS.qdrant_collection

    if ARGS.dual_gate_warmup_turns < 0:
        raise ValueError("--dual-gate-warmup-turns must be >= 0.")
    if not 0.0 <= ARGS.dual_gate_salience_quantile <= 1.0:
        raise ValueError("--dual-gate-salience-quantile must be between 0 and 1.")
    if not 0.0 <= ARGS.dual_gate_surprise_quantile <= 1.0:
        raise ValueError("--dual-gate-surprise-quantile must be between 0 and 1.")
    if not 0.0 <= ARGS.dual_gate_tension_quantile <= 1.0:
        raise ValueError("--dual-gate-tension-quantile must be between 0 and 1.")
    if ARGS.dual_gate_tension_salience_support_ratio < 0.0:
        raise ValueError("--dual-gate-tension-salience-support-ratio must be >= 0.")
    if ARGS.skip_mamba and ARGS.live_accumulation:
        raise ValueError("--live-accumulation requires Mamba; remove --skip-mamba.")

    LATEST_TRANSCRIPT_PATH = Path(ARGS.transcript_path)
    LATEST_JSONL_PATH = Path(ARGS.turn_log_path)
    DUAL_GATE_LOG_PATH = Path(ARGS.dual_gate_log_path)
    DUAL_GATE_MEMORY_PATH = Path(ARGS.dual_gate_memory_path)
    DUAL_GATE_SURPRISE_PATH = Path(ARGS.dual_gate_surprise_path)
    DUAL_GATE_SLEEP_PATH = Path(ARGS.dual_gate_sleep_path)
    QDRANT_PENDING_PATH = Path(ARGS.qdrant_pending_path)
    QDRANT_FLUSHED_PATH = Path(ARGS.qdrant_flushed_path)
    MEMORY_FORMATION_LOG_PATH = Path(ARGS.memory_formation_log_path)
    RECALL_LOG_PATH = Path(ARGS.recall_log_path)
    SELF_REPORT_LOG_PATH = Path(ARGS.self_report_log_path)
    FAILURE_LOG_PATH = Path(ARGS.failure_log_path)
    LATEST_TRANSCRIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LATEST_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    DUAL_GATE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    DUAL_GATE_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    DUAL_GATE_SURPRISE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DUAL_GATE_SLEEP_PATH.parent.mkdir(parents=True, exist_ok=True)
    QDRANT_PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    QDRANT_FLUSHED_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FORMATION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECALL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    SELF_REPORT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    FAILURE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    DUAL_GATE_LOG_PATH.write_text("", encoding="utf-8")
    DUAL_GATE_MEMORY_PATH.write_text("", encoding="utf-8")
    DUAL_GATE_SURPRISE_PATH.write_text("", encoding="utf-8")
    DUAL_GATE_SLEEP_PATH.write_text("", encoding="utf-8")
    MEMORY_FORMATION_LOG_PATH.write_text("", encoding="utf-8")
    RECALL_LOG_PATH.write_text("", encoding="utf-8")
    SELF_REPORT_LOG_PATH.write_text("", encoding="utf-8")
    FAILURE_LOG_PATH.write_text("", encoding="utf-8")
    DUAL_GATE_EVENTS.clear()
    persist_conversation()

    qwen_dtype = torch.float16 if "cuda" in ARGS.qwen_device else torch.float32

    print(f"Loading bridge: {ARGS.bridge_path}...")
    ckpt = torch.load(ARGS.bridge_path, map_location="cpu", weights_only=False)
    bridge_mode = validate_checkpoint_runtime_contract(ckpt, caller="chat_server")
    print(f"Bridge mode: {bridge_mode}")
    checkpoint_qwen_model_id = ckpt.get("qwen_model_id", DEFAULT_QWEN)
    if ARGS.qwen_model_id != checkpoint_qwen_model_id:
        if is_same_qwen_family(ARGS.qwen_model_id, checkpoint_qwen_model_id):
            print(
                "[warn] Checkpoint/model mismatch: "
                f"checkpoint trained on {checkpoint_qwen_model_id}, "
                f"but chat_server requested {ARGS.qwen_model_id}. "
                "Proceeding - same architecture family assumed."
            )
        else:
            raise ValueError(
                "Checkpoint/model mismatch: "
                f"checkpoint trained on {checkpoint_qwen_model_id}, "
                f"but chat_server requested {ARGS.qwen_model_id}."
            )

    checkpoint_target_specs = normalize_target_specs(
        ckpt.get("target_specs") or ckpt.get("target_layers")
    )
    cli_target_specs = parse_target_layers(ARGS.target_layers)
    target_specs = checkpoint_target_specs
    mamba_target_layer = int(ckpt.get("mamba_target_layer", 3))
    bridge_config = ckpt.get("bridge_config", {})
    hyper_state = ckpt["hypernetwork_state_dict"]
    context_mode = str(ckpt.get("context_mode", bridge_config.get("context_mode", "compressed")))
    context_dim = int(
        ckpt.get(
            "context_dim",
            bridge_config.get("context_dim", hyper_state["backbone.0.weight"].shape[1]),
        )
    )

    print(f"Loading Qwen: {ARGS.qwen_model_id}...")
    TOKENIZER = AutoTokenizer.from_pretrained(ARGS.qwen_model_id)
    if TOKENIZER.pad_token_id is None:
        TOKENIZER.pad_token_id = TOKENIZER.eos_token_id
    DIGIT_TOKEN_IDS = resolve_digit_token_ids(TOKENIZER)

    MODEL = AutoModelForCausalLM.from_pretrained(
        ARGS.qwen_model_id,
        torch_dtype=qwen_dtype,
        device_map=ARGS.qwen_device,
    )
    MODEL.eval()

    checkpoint_target_widths = infer_checkpoint_target_widths(ckpt, checkpoint_target_specs)
    target_layers_overridden = False
    if cli_target_specs is not None:
        print("[warn] Overriding checkpoint target_specs with CLI --target-layers")
        target_specs = cli_target_specs
        target_layers_overridden = True

    target_dims = validate_target_specs_for_model(
        MODEL,
        target_specs,
        checkpoint_target_widths,
    )

    print(f"Patching layers: {target_specs}...")
    patched_layers = []
    for layer_idx, proj_name in target_specs:
        layer = MODEL.model.layers[layer_idx]
        original = getattr(layer.self_attn, proj_name)
        patched = DynamicLoRALinear(original)
        setattr(layer.self_attn, proj_name, patched)
        patched_layers.append(patched)

    session_started_at = datetime.now().isoformat(timespec="seconds")
    BRIDGE_CTX = RuntimeBridgeContext(
        patched_layers=list(patched_layers),
        live_accumulation=bool(ARGS.live_accumulation and not ARGS.skip_mamba),
        session_started_at=session_started_at,
    )

    if ARGS.skip_mamba:
        # Baseline mode: no Mamba, no bridge injection. Qwen runs unmodified.
        print("Skipping Mamba loading (--skip-mamba mode, no bridge injection)")
        disposition_title = "baseline (no Mamba)"
        gate_layers = sorted({layer_idx for layer_idx, _proj_name in target_specs})
        ACTIVATION_RECORDER = ActivationRecorder(MODEL, gate_layers)
        LAST_CONVERSATION_SNAPSHOT = record_activation_snapshot(ARGS.neutral_prompt)
        BOOTSTRAP_QWEN_HIDDEN_REFERENCE = flatten_snapshot(LAST_CONVERSATION_SNAPSHOT)
        mamba_state_ref = ""
        bridge_loaded = False
    else:
        print(f"Loading Mamba: {ARGS.mamba_model_id}...")
        ensure_mamba_ssm_compat()
        from transformers import MambaForCausalLM

        mamba_tokenizer = AutoTokenizer.from_pretrained(ARGS.mamba_model_id)
        mamba_model = MambaForCausalLM.from_pretrained(
            ARGS.mamba_model_id,
            torch_dtype=torch.float32,
        )
        mamba_model.to(ARGS.mamba_device)
        mamba_model.eval()
        compressor, hypernet, mamba_target_layer, hidden_layer_count, resolved_context_mode, bridge_mode = (
            build_runtime_context_encoder_and_hypernetwork(
                checkpoint=ckpt,
                mamba_model=mamba_model,
                target_dims=target_dims,
                bridge_device=ARGS.qwen_device,
            )
        )
        context_mode = resolved_context_mode
        print(f"Context path: {context_mode} (dim={getattr(compressor, 'output_dim', context_dim)})")
        BRIDGE_CTX.mamba_model = mamba_model
        BRIDGE_CTX.mamba_tokenizer = mamba_tokenizer
        BRIDGE_CTX.compressor = compressor
        BRIDGE_CTX.hypernet = hypernet
        BRIDGE_CTX.mamba_target_layer = mamba_target_layer
        BRIDGE_CTX.hidden_layer_count = hidden_layer_count
        BRIDGE_CTX.bridge_mode = bridge_mode
        BRIDGE_CTX.context_mode = context_mode

        episodes = read_episodes(ARGS.episodes_file)
        episode = episodes[ARGS.episode_index]
        print(f"\nProcessing disposition: {episode['title']}...")
        disposition_title = episode["title"]

        episode_tokens = mamba_tokenizer(
            episode["text"],
            return_tensors="pt",
            truncation=True,
            max_length=ARGS.max_mamba_tokens,
        )
        episode_tokens = {key: value.to(ARGS.mamba_device) for key, value in episode_tokens.items()}
        with torch.no_grad():
            mamba_out = mamba_model(**episode_tokens, output_hidden_states=True, use_cache=True)
            last_token = extract_last_token_hidden(
                mamba_out,
                mamba_target_layer,
                hidden_layer_count,
            ).to(ARGS.qwen_device, dtype=torch.float32)
            context = compressor(last_token)
            bridge_adjustments, _gate_summary = resolve_runtime_bridge_adjustments(
                hypernetwork=hypernet,
                context_vector=context,
                bridge_mode=bridge_mode,
            )
            BOOTSTRAP_QWEN_BIAS_DIRECTION = flatten_bridge_adjustments(
                bridge_adjustments,
                bridge_mode,
                ARGS.alpha,
            )
            apply_runtime_bridge_adjustments(
                patched_layers=patched_layers,
                bridge_adjustments=bridge_adjustments,
                bridge_mode=bridge_mode,
                alpha=ARGS.alpha,
            )

        gate_layers = sorted({layer_idx for layer_idx, _proj_name in target_specs})
        ACTIVATION_RECORDER = ActivationRecorder(MODEL, gate_layers)
        LAST_CONVERSATION_SNAPSHOT = record_activation_snapshot(ARGS.neutral_prompt)
        BOOTSTRAP_QWEN_HIDDEN_REFERENCE = flatten_snapshot(LAST_CONVERSATION_SNAPSHOT)
        if BRIDGE_CTX.live_accumulation:
            BRIDGE_CTX.cache_params = getattr(mamba_out, "cache_params", None)
            if BRIDGE_CTX.cache_params is None:
                raise RuntimeError("Mamba bootstrap did not return cache_params required for --live-accumulation.")
            BRIDGE_CTX.cache_position = torch.tensor(
                [int(mamba_model.config.conv_kernel)],
                device=episode_tokens["input_ids"].device,
                dtype=torch.long,
            )
        mamba_state_ref = persist_runtime_mamba_state(
            last_token,
            BRIDGE_CTX,
            state_source="hidden_last_token",
            count_as_live_update=False,
        )
        bridge_loaded = True

    BRIDGE_CTX.bridge_loaded = bridge_loaded
    update_runtime_state(
        started_at=session_started_at,
        started_monotonic=time.monotonic(),
        running=True,
        bridge_loaded=bridge_loaded,
        busy=False,
        stop_requested=False,
        last_error="",
        disposition=disposition_title,
        dual_gate_enabled=bool(ARGS.dual_gate_enabled),
        dual_gate_supported_tension_enabled=bool(ARGS.dual_gate_supported_tension_enabled),
        dual_gate_tension_salience_support_ratio=float(ARGS.dual_gate_tension_salience_support_ratio),
        instance_id=ARGS.instance_id,
        no_shared_memory=bool(ARGS.no_shared_memory),
        qdrant_collection=ARGS.qdrant_collection,
        memory_count=0,
        qdrant_count=0,
        surprise_count=0,
        tension_count=0,
        open_tension_count=0,
        sleep_tagged_count=0,
        formation_log_count=0,
        formation_written_count=0,
        formation_queued_count=0,
        formation_discarded_count=0,
        recall_request_count=0,
        recall_hit_count=0,
        qdrant_synced_count=0,
        failure_log_count=0,
        qdrant_queued_count=0,
        qdrant_pending_count=0,
        qdrant_sleep_pending_count=0,
        qdrant_retry_pending_count=0,
        qdrant_replayed_count=0,
        qdrant_write_failures=0,
        last_qdrant_id="",
        last_qdrant_error="",
        last_qdrant_retry_at="",
        last_qdrant_replay_at="",
        qdrant_write_mode=ARGS.qdrant_write_mode,
        ambient_recall_enabled=bool(ARGS.ambient_recall),
        explicit_recall_style=ARGS.explicit_recall_style,
        cluster_recall_enabled=bool(ARGS.cluster_recall),
        cluster_recall_limit=int(ARGS.cluster_recall_limit),
        cluster_recall_threshold=float(ARGS.cluster_recall_threshold),
        mamba_state_ref=mamba_state_ref,
        mamba_state_source="hidden_last_token" if bridge_loaded else "",
        mamba_state_updated_at=session_started_at if bridge_loaded else "",
        mamba_target_layer=mamba_target_layer,
        live_accumulation_enabled=bool(BRIDGE_CTX.live_accumulation),
        live_accumulation_updates=0,
        live_accumulation_last_error="",
        last_recall={},
        last_failure={},
        last_memory_packet={},
        last_gate={},
        target_layers=format_target_specs(target_specs),
        target_layers_overridden=target_layers_overridden,
        episode_index=int(ARGS.episode_index),
        blind_disposition_ui=bool(ARGS.blind_disposition_ui),
    )
    update_qdrant_pending_state()

    print(f"\nBridge injected with alpha={ARGS.alpha}. Disposition: {disposition_title}")
    print(f"\n{'=' * 50}")
    print(f"Server starting on http://{ARGS.host}:{ARGS.port}")
    print(f"Open this on your phone: http://192.168.2.49:{ARGS.port}")
    print(f"Prompt labels: {ARGS.user_label} / {ARGS.model_label}")
    print(f"{'=' * 50}\n")

    SERVER = ThreadingHTTPServer((ARGS.host, ARGS.port), ChatHandler)
    if ARGS.qdrant_enabled:
        ensure_qdrant_gate_sink(force_retry=True)
        threading.Thread(target=qdrant_retry_worker, daemon=True).start()
    try:
        SERVER.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        update_runtime_state(running=False, busy=False)
        persist_conversation()
        print(f"Conversation saved to {LATEST_TRANSCRIPT_PATH}")
        if ACTIVATION_RECORDER is not None:
            ACTIVATION_RECORDER.cleanup()
        if SERVER is not None:
            SERVER.server_close()


if __name__ == "__main__":
    main()
