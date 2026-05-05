#!/usr/bin/env node
// thinking-proxy.js — strips redact-thinking beta flag from Anthropic API requests
// Usage: node thinking-proxy.js
//        export ANTHROPIC_BASE_URL=http://localhost:8082

const http = require('http');
const https = require('https');

const fs = require('fs');
const path = require('path');

const PORT = parseInt(process.env.PORT, 10) || 8082;
const TARGET_HOST = 'api.anthropic.com';
const REDACT_FLAG = 'redact-thinking-2026-02-12';
const STATUSLINE = path.join(process.env.USERPROFILE || process.env.HOME || '', '.claude', 'statusline.json');

function log(msg) {
  process.stderr.write(`[thinking-proxy] ${msg}\n`);
}

function stripRedactFlag(headerValue) {
  if (!headerValue) return null;
  const parts = headerValue
    .split(',')
    .map(s => s.trim())
    .filter(s => s !== REDACT_FLAG);
  return parts.length > 0 ? parts.join(', ') : null;
}

function sniffThinkingParams(bodyStr) {
  // Extract thinking/reasoning params from the API request body
  // and write them to the statusline state file.
  // Also dump top-level keys once for discovery.
  try {
    const body = JSON.parse(bodyStr);
    const update = {};

    // Lightweight debug dump — skip bulky arrays (tools, messages, system)
    const skipKeys = new Set(['messages', 'system', 'tools']);
    const debugSnippet = {};
    for (const k of Object.keys(body)) {
      if (!skipKeys.has(k)) debugSnippet[k] = body[k];
    }
    const debugPath = path.join(path.dirname(STATUSLINE), 'proxy_sniff.json');
    fs.writeFileSync(debugPath, JSON.stringify(debugSnippet, null, 2), 'utf-8');

    // thinking.budget_tokens (extended thinking)
    if (body.thinking) {
      update.thinking_type = body.thinking.type || 'unknown';
      if (body.thinking.budget_tokens) {
        update.thinking_budget = body.thinking.budget_tokens;
      }
    }

    // output_config.effort (Claude Code /effort setting)
    if (body.output_config && body.output_config.effort) {
      // Log effort changes to catch unexpected resets
      try {
        let prev = {};
        try { prev = JSON.parse(fs.readFileSync(STATUSLINE, 'utf-8')); } catch {}
        if (prev.effort && prev.effort !== body.output_config.effort) {
          const logLine = `${new Date().toISOString()} effort: ${prev.effort} -> ${body.output_config.effort}\n`;
          fs.appendFileSync(path.join(path.dirname(STATUSLINE), 'effort_log.txt'), logLine, 'utf-8');
        }
      } catch {}
      update.effort = body.output_config.effort;
    }

    // temperature
    if (body.temperature !== undefined) {
      update.temperature = body.temperature;
    }

    // model from request
    if (body.model) {
      update.req_model = body.model;
    }

    if (Object.keys(update).length > 0) {
      // Merge into existing statusline state
      let state = {};
      try { state = JSON.parse(fs.readFileSync(STATUSLINE, 'utf-8')); } catch {}
      Object.assign(state, update);
      fs.writeFileSync(STATUSLINE, JSON.stringify(state), 'utf-8');
    }
  } catch {
    // Don't break the proxy over a sniff failure
  }
}

const server = http.createServer((clientReq, clientRes) => {
  log(`${clientReq.method} ${clientReq.url}`);
  if (clientReq.headers['anthropic-beta']) {
    log(`anthropic-beta: ${clientReq.headers['anthropic-beta']}`);
  }

  // Copy headers, strip the redact flag from anthropic-beta
  const headers = Object.assign({}, clientReq.headers);

  // Remove hop-by-hop headers that shouldn't be forwarded
  delete headers['host'];
  headers['host'] = TARGET_HOST;

  // Strip the redact-thinking flag
  if (headers['anthropic-beta']) {
    const cleaned = stripRedactFlag(headers['anthropic-beta']);
    if (cleaned) {
      headers['anthropic-beta'] = cleaned;
    } else {
      delete headers['anthropic-beta'];
    }
  }

  // Don't forward transfer-encoding/connection as we're making a new request
  delete headers['connection'];
  delete headers['transfer-encoding'];

  const options = {
    hostname: TARGET_HOST,
    port: 443,
    path: clientReq.url,
    method: clientReq.method,
    headers: headers,
  };

  const upstreamReq = https.request(options, (upstreamRes) => {
    // Forward status and headers from upstream
    clientRes.writeHead(upstreamRes.statusCode, upstreamRes.headers);
    // Pipe directly — no buffering, SSE streams through in real time
    upstreamRes.pipe(clientRes);
  });

  upstreamReq.on('error', (err) => {
    log(`upstream error: ${err.message}`);
    if (!clientRes.headersSent) {
      clientRes.writeHead(502, { 'Content-Type': 'application/json' });
      clientRes.end(JSON.stringify({ error: 'upstream_connection_failed', message: err.message }));
    } else {
      clientRes.end();
    }
  });

  // For POST to /v1/messages — sniff the body for thinking params
  // Buffer it, sniff, then write to upstream
  if (clientReq.method === 'POST' && clientReq.url.includes('/messages')) {
    const chunks = [];
    clientReq.on('data', chunk => {
      chunks.push(chunk);
      upstreamReq.write(chunk);
    });
    clientReq.on('end', () => {
      const bodyStr = Buffer.concat(chunks).toString('utf-8');
      sniffThinkingParams(bodyStr);
      upstreamReq.end();
    });
  } else {
    // Non-messages requests — pipe directly
    clientReq.pipe(upstreamReq);
  }
});

server.on('error', (err) => {
  log(`server error: ${err.message}`);
  process.exit(1);
});

server.listen(PORT, '127.0.0.1', () => {
  log(`listening on http://127.0.0.1:${PORT} -> https://${TARGET_HOST}`);
  log(`set ANTHROPIC_BASE_URL=http://localhost:${PORT}`);
});

// Graceful shutdown
function shutdown() {
  log('shutting down');
  server.close(() => process.exit(0));
  // Force exit after 3s if connections linger
  setTimeout(() => process.exit(0), 3000);
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
