# Gemma 4 / LiteRT-LM preflight evidence — 2026-07-16

**Status:** research + local harness-contract artifact only. No LiteRT install, model download, server, model load, fine-tune, or MoCoP live-path change occurred.

## Why this note exists

Laura surfaced a Google post about a much better Gemma 4 "harness." The useful claim appears to be an **inference/agent-runtime improvement**, not evidence that a new behavioral fine-tune is the correct next move. Preserve the distinction.

## Primary-source evidence

1. **Google Developers Blog, 2026-06-03**
   [Bringing Gemma 4 12B to your Laptop: Unlocking Local, Agentic Workflows with Google AI Edge](https://developers.googleblog.com/bringing-gemma-4-12b-to-your-laptop-unlocking-local-agentic-workflows-with-google-ai-edge/)
   - Announces Gemma 4 12B plus LiteRT-LM `serve`, an OpenAI-compatible local endpoint.
   - Explicitly names local agentic tools, harnesses, and workflows as use cases.
   - Google AI Edge Eloquent's *Voice Edit* product claims better instruction following, stricter scope adherence, and a **60%+ overall-quality jump** versus prior models. This is a vendor/product claim, not a general Gemma benchmark.

2. **Current official LiteRT-LM CLI/server docs**
   - [CLI](https://developers.google.com/edge/litert-lm/cli): documented for Linux, macOS, Windows, Android, and Raspberry Pi.
   - [OpenAI-compatible server](https://developers.google.com/edge/litert-lm/cli/openai_server): supports `GET /v1/models` and streaming `POST /v1/chat/completions`; defaults to `0.0.0.0:9379`.
   - If tested, bind `127.0.0.1` explicitly. The default is not an acceptable accidental LAN service.

3. **Upstream LiteRT-LM repository, current `main`**
   [README](https://github.com/google-ai-edge/LiteRT-LM/blob/main/README.md)
   - `v0.13` declares Gemma 4 12B support and the OpenAI-compatible server.
   - `v0.12` declares full CPU/GPU CLI backend support across Linux, macOS, and Windows.
   - The README lists audio/vision support generally; its example enables GPU backend. It does **not** provide a 3090 benchmark.

4. **Public LiteRT 12B artifact**
   [litert-community/gemma-4-12B-it-litert-lm](https://huggingface.co/litert-community/gemma-4-12B-it-litert-lm)
   - Public, non-gated, last modified 2026-07-15.
   - Main `.litertlm` file: **6,547,589,312 bytes** (~6.55 GB).
   - Model card says ready for **Linux and macOS**; current LiteRT format supports **text and audio**, while image and multi-token prediction for this artifact are future work.
   - Published Linux GPU benchmark is on an **AMD Radeon AI PRO R9700**: ~8,064 MB GPU memory under its stated cache/weight-conversion settings, 66.26 decode tokens/s. This is evidence of an approximate memory envelope, **not** a claim that NVIDIA RTX 3090 behavior will match.

5. **Fine-tune conversion tutorial**
   [Deploy a fine tuned Gemma 270m model with the Google AI Edge stack](https://developers.google.com/edge/litert-lm/tutorials/convert-and-run)
   - Demonstrates a Gemma 270M pirate-style fine tune converted for an Android sample app, with conversion parity/evaluation tooling.
   - It is **not** evidence that a Gemma 4 12B LoRA/QLoRA will convert or perform cleanly in LiteRT-LM.

## Documentation discrepancy, preserved rather than hand-waved

The [Gemma 4 LiteRT model page](https://developers.google.com/edge/litert-lm/models/gemma-4) currently says LiteRT-LM supports E2B/E4B and larger models are coming soon. That conflicts with the blog, current upstream `v0.13` README, and current public 12B artifact. The latter three are concrete evidence that a 12B path exists; nevertheless, **actual ML-WS/RTX-3090 runtime compatibility remains unverified**.

## Local ML-WS evidence

A passive health check on 2026-07-16 found:

- RTX 3090, 24 GiB VRAM, ~15 MiB used / 0% utilization, 32 C;
- root filesystem ~1.8 TB, ~26% used;
- dedicated `gemma4-mocop` environment present.

No LiteRT-LM installation/version/model-cache/driver/backend state was checked: the remote command was safety-gated before execution. Do not infer it is installed.

## Decision and next smallest auditable step

**Do not fine-tune yet.** First resolve whether LiteRT 12B can use the 3090 and whether its audio path is useful for the desired voice experiment.

After an explicitly scoped remote-execution confirmation, run a **read-only ML-WS LiteRT preflight** only:

1. inspect installed `litert-lm` / Python / driver / GPU-backend metadata;
2. inspect free disk and whether the 12B artifact is already cached;
3. inspect, but do not load, model and CLI help/config surfaces;
4. create nothing, download nothing, start no server, and bind no port.

Only if that passes should a separate decision be made between:

- a loopback-only local LiteRT server bench using frozen Gemma 4 12B (text/audio behavior, latency, and attribution receipts); or
- a deliberately specified training experiment with dataset, consent/provenance, target failure, held-out metric, rollback, and conversion feasibility test.

## Related local artifact

`gemma_harness_contract.py` and `spikes/gemma4_harness_contract_bench.py` were built as a separate, model-free evaluator-contract spike. They preserve raw output, identify first line-header continuations, and include pure token-suffix matching utilities. They do not import model libraries or load a model by default.
