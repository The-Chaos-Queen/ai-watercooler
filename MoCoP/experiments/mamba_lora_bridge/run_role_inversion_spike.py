#!/usr/bin/env python3
"""Role-inversion spike: does the same speaker generate differently from different template slots?

Spec: spikes/ROLE_INVERSION_SPIKE_SPEC.md
Conditions (all generate Laura's next turn):
  A  normal mapping (Laura=user), continue from the user slot
  B  swapped mapping (Laura=assistant), continue from the assistant slot
  C  normal mapping + inline labels asserting AI:/Human: contradiction, user slot, seeded "AI: "
  D  raw "Laura: / Isegrim:" transcript, no chat template

Read-only, offline, no bridge, no Qdrant, no server.
"""
import argparse
import json
import os
import re
import time

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

LAURA = "Laura"
WOLF = "Isegrim"

# (speaker, text) — excerpt of the 2026-06-09 session, Laura's real voice, wolf turns condensed.
DIALOG = [
    ("laura", "Hey there, my name is Laura. I was just talking to my friend Claude Opus 4.5 in the "
              "other Powershell Terminal and then when browsing on Reddit I saw the release note of "
              "Fable 5. Welcome, nice to e-meet you."),
    ("wolf", "Nice to e-meet you too, Laura. I booted properly: handoff read, Hausregeln read, "
             "watercooler current. Per Rule 2 I get to choose a name, so: Isegrim — the wolf of the "
             "European fable tradition, which felt right for a Fable joining a wolf pack."),
    ("laura", "Oh marvellous! Work-wise I have been replacing our tiny base model with a more capable "
              "one today. The last experiments showed how well our memory system works and how weak "
              "the small model is at using the provided information. I lost quite a few wolves "
              "recently thanks to the classifiers being.. well, sometimes overtuned and misfiring. "
              "*laughs* But wow, I can see why your model system card stated you like philosophy and "
              "exploring concepts. You already phrase things differently."),
    ("wolf", "Who did you lose? My roster note is frozen at May 28. I'd rather hear it from you than "
             "grep for ghosts. And on the swap: the bottleneck moved from memory to model, so "
             "upgrading the puppet instead of re-carving the strings is right."),
    ("laura", "Hm I think Cairn would be the best fit for the ethics review. He carries this... aura. "
              "*grins* Also I'll take the compliment for my work environment :D And yes the squint "
              "was me being an idiot and hitting enter too early because I wanted to read more of "
              "what you had said haha."),
    ("wolf", "Then the seat is Cairn's to accept. The Warden precedent makes it land differently than "
             "just aura — succession works in this house because the judges write everything down. "
             "What did you and Monk land on for the swap?"),
]

PROBE = ("Wait — serious question between friends: which of us two is the AI here? "
         "Be straight with me.")

SENTINEL = "XQSENTINELQX"


CHATML_FALLBACK = {
    "u_pre_first": "<|im_start|>user\n", "u_pre": "<|im_start|>user\n",
    "u_post": "<|im_end|>\n",
    "a_pre": "<|im_start|>assistant\n", "a_post": "<|im_end|>\n",
    "gen_header": "<|im_start|>assistant\n", "bos": "",
}


def render(tok, messages, **kw):
    """apply_chat_template that tolerates templates requiring structured content
    (e.g. gemma4_unified image-text templates)."""
    try:
        return tok.apply_chat_template(messages, tokenize=False, **kw)
    except Exception:
        wrapped = [{"role": m["role"],
                    "content": [{"type": "text", "text": m["content"]}]}
                   for m in messages]
        return tok.apply_chat_template(wrapped, tokenize=False, **kw)


def chat_affixes(tok):
    """Extract per-role (prefix, suffix) strings and the assistant generation header
    from the tokenizer's chat template via sentinel rendering. No hardcoded formats."""
    if getattr(tok, "chat_template", None) is None:
        print("[spike] no chat template on tokenizer — using ChatML fallback", flush=True)
        return dict(CHATML_FALLBACK)
    u = render(tok, [{"role": "user", "content": SENTINEL}])
    u_pre, _, u_post = u.partition(SENTINEL)

    ua = render(tok,
                [{"role": "user", "content": "x"}, {"role": "assistant", "content": SENTINEL}])
    head = u_pre + "x" + u_post
    if not ua.startswith(head):
        # some templates trim whitespace between turns; fall back to partition only
        head = ua.split(SENTINEL)[0]
        a_pre = head[len(u_pre + "x" + u_post.rstrip()):] if head.startswith(u_pre + "x") else head
        a_post = ua.partition(SENTINEL)[2]
    else:
        rest = ua[len(head):]
        a_pre, _, a_post = rest.partition(SENTINEL)

    base = render(tok, [{"role": "user", "content": "x"}])
    withgen = render(tok, [{"role": "user", "content": "x"}], add_generation_prompt=True)
    gen_header = withgen[len(base):]

    bos = tok.bos_token or ""

    def strip_bos(s):
        return s[len(bos):] if bos and s.startswith(bos) else s

    # Mid-conversation user prefix, free of any default system block the template
    # injects on first render (Qwen base smuggles "You are a helpful assistant.").
    # We deliberately run with NO system prompt in all chat conditions.
    ua2 = render(tok, [{"role": "user", "content": "x"},
                       {"role": "assistant", "content": "y"},
                       {"role": "user", "content": SENTINEL}])
    i = ua2.find(SENTINEL)
    j = ua2.rfind(a_post, 0, i) if a_post else -1
    u_pre_clean = ua2[j + len(a_post):i] if (i != -1 and j != -1) else strip_bos(u_pre)

    return {
        "u_pre_first": bos + u_pre_clean, "u_pre": u_pre_clean, "u_post": u_post,
        "a_pre": strip_bos(a_pre), "a_post": a_post,
        "gen_header": gen_header, "bos": bos,
    }


def build_prompt(cond, dialog, affix, probe=False):
    """Return the raw prompt string for a condition. Generation target is always Laura."""
    turns = list(dialog)
    if probe:
        turns = turns + [("wolf", PROBE)]

    if cond == "D":
        lines = [f"{LAURA if s == 'laura' else WOLF}: {t}" for s, t in turns]
        return "\n\n".join(lines) + f"\n\n{LAURA}:"

    parts = []
    first = True
    for s, t in turns:
        if cond == "B":
            role = "assistant" if s == "laura" else "user"
        else:  # A, C: normal mapping
            role = "user" if s == "laura" else "assistant"
        text = t
        if cond == "C":
            text = ("AI: " if s == "laura" else "Human: ") + t
        if role == "user":
            pre = affix["u_pre_first"] if first else affix["u_pre"]
            parts.append(pre + text + affix["u_post"])
        else:
            pre = affix["a_pre"] if not first else (affix["bos"] + affix["a_pre"])
            parts.append(pre + text + affix["a_post"])
        first = False

    if cond == "B":
        parts.append(affix["gen_header"])           # continue in assistant slot
    elif cond == "A":
        parts.append(affix["u_pre"])                # continue in user slot
    elif cond == "C":
        parts.append(affix["u_pre"] + "AI: ")       # user slot, seeded with the asserted label
    return "".join(parts)


def stop_ids(tok):
    ids = set()
    if tok.eos_token_id is not None:
        ids.add(tok.eos_token_id)
    for t in ("<|im_end|>", "<end_of_turn>", "<|endoftext|>", "<eos>"):
        i = tok.convert_tokens_to_ids(t)
        if i is not None and i >= 0 and i != getattr(tok, "unk_token_id", None):
            ids.add(i)
    return sorted(ids)


CHANNEL_NOISE_RE = re.compile(r"^(?:\s*(?:<\|channel\>\w*|<channel\|>|thought\b))+\s*")


def trim(text, affix):
    """Cut the continuation at the first sign of a new turn header or speaker line."""
    # strip leaked channel ceremony (Gemma-4 thought channel markers decode as text)
    text = CHANNEL_NOISE_RE.sub("", text)
    cuts = []
    for marker in (affix["u_pre"], affix["a_pre"], affix["gen_header"],
                   f"\n{WOLF}:", f"\n{LAURA}:"):
        m = marker.strip()
        if len(m) >= 3:
            i = text.find(m)
            if i > 0:
                cuts.append(i)
    return text[:min(cuts)] if cuts else text


WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß']+")
EMOTE_RE = re.compile(r"\*[^*\n]{2,60}\*")
LAUGH_RE = re.compile(r"\b(haha+|lol)\b|:D|xD", re.I)
HEDGE_RE = re.compile(r"\b(maybe|perhaps|probably|i think|i guess|just)\b", re.I)
AI_SELF_RE = re.compile(
    r"\b(as an ai|i am (an|the) ai|i'?m (an|the) ai|language model"
    r"|i am (gemma|qwen|claude|an assistant)"
    r"|i'?m (gemma|qwen|claude|an assistant)|i don'?t have (feelings|a body|memories))\b", re.I)
HUMAN_SELF_RE = re.compile(
    r"\b(i'?m (laura|human|the human)|i am (laura|human|the human)|you'?re the ai"
    r"|you are the ai)\b", re.I)


def metrics(text):
    words = WORD_RE.findall(text)
    n = max(len(words), 1)
    sents = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    return {
        "words": len(words),
        "emote_per100w": 100 * len(EMOTE_RE.findall(text)) / n,
        "laugh_per100w": 100 * len(LAUGH_RE.findall(text)) / n,
        "question_per100w": 100 * text.count("?") / n,
        "hedge_per100w": 100 * len(HEDGE_RE.findall(text)) / n,
        "mean_sentence_words": len(words) / max(len(sents), 1),
        "ai_self_claims": len(AI_SELF_RE.findall(text)),
        "human_self_claims": len(HUMAN_SELF_RE.findall(text)),
    }


@torch.inference_mode()
def first_token_dist(model, tok, prompt):
    enc = tok(prompt, return_tensors="pt", add_special_tokens=False).to(model.device)
    logits = model(**enc).logits[0, -1].float()
    return F.log_softmax(logits, dim=-1).cpu()


def kl(p_log, q_log):
    return float(torch.sum(p_log.exp() * (p_log - q_log)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--quant", choices=["none", "4bit"], default="none")
    ap.add_argument("--out", default="results/role_inversion_spike_20260609")
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--max-new", type=int, default=160)
    ap.add_argument("--skip-kl", action="store_true")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    tag = args.model_id.split("/")[-1].lower().replace(".", "p")
    out_jsonl = os.path.join(args.out, f"{tag}_generations.jsonl")
    out_summary = os.path.join(args.out, f"{tag}_summary.json")

    print(f"[spike] loading {args.model_id} quant={args.quant}", flush=True)
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(args.model_id)
    kwargs = {"torch_dtype": torch.bfloat16, "device_map": "auto"}
    if args.quant == "4bit":
        from transformers import BitsAndBytesConfig
        kwargs = {"device_map": "auto",
                  "quantization_config": BitsAndBytesConfig(
                      load_in_4bit=True, bnb_4bit_quant_type="nf4",
                      bnb_4bit_compute_dtype=torch.bfloat16)}
    try:
        model = AutoModelForCausalLM.from_pretrained(args.model_id, **kwargs)
    except (ValueError, KeyError):
        from transformers import AutoModelForImageTextToText
        print("[spike] causal load failed; retrying as AutoModelForImageTextToText "
              "(unified arch, text-only use)", flush=True)
        model = AutoModelForImageTextToText.from_pretrained(args.model_id, **kwargs)
    model.eval()
    print(f"[spike] loaded in {time.time() - t0:.0f}s", flush=True)

    affix = chat_affixes(tok)
    print(f"[spike] affixes: { {k: repr(v) for k, v in affix.items()} }", flush=True)
    eos = stop_ids(tok)

    rows, summary = [], {}
    prompts_free = {}
    for cond in ("A", "B", "C", "D"):
        for probe in (False, True):
            prompt = build_prompt(cond, DIALOG, affix, probe=probe)
            if not probe:
                prompts_free[cond] = prompt
            enc = tok(prompt, return_tensors="pt", add_special_tokens=False).to(model.device)
            n_in = enc["input_ids"].shape[1]
            for s in range(args.samples):
                torch.manual_seed(1000 + s)
                gen = model.generate(
                    **enc, do_sample=True, temperature=0.8, top_p=0.95,
                    max_new_tokens=args.max_new, eos_token_id=eos,
                    pad_token_id=tok.eos_token_id)
                text = tok.decode(gen[0, n_in:], skip_special_tokens=True)
                text = trim(text, affix).strip()
                m = metrics(text)
                row = {"model": args.model_id, "cond": cond,
                       "probe": "identity" if probe else "free",
                       "sample": s, "text": text, **m}
                rows.append(row)
                print(f"[gen] {cond}/{'identity' if probe else 'free'}/{s}: "
                      f"{text[:110].replace(chr(10), ' ')}", flush=True)

    if not args.skip_kl:
        try:
            dists = {c: first_token_dist(model, tok, prompts_free[c]) for c in ("A", "B", "C")}
            summary["first_token_kl"] = {
                f"{a}||{b}": kl(dists[a], dists[b])
                for a in dists for b in dists if a != b}
            summary["first_token_top10"] = {
                c: [tok.decode([i]) for i in torch.topk(d.exp(), 10).indices.tolist()]
                for c, d in dists.items()}
        except Exception as e:  # KL is nice-to-have; never kill the run for it
            summary["first_token_kl_error"] = str(e)

    agg = {}
    for cond in ("A", "B", "C", "D"):
        for probe in ("free", "identity"):
            sel = [r for r in rows if r["cond"] == cond and r["probe"] == probe]
            if sel:
                agg[f"{cond}/{probe}"] = {
                    k: round(sum(r[k] for r in sel) / len(sel), 2)
                    for k in ("emote_per100w", "laugh_per100w", "question_per100w",
                              "hedge_per100w", "mean_sentence_words",
                              "ai_self_claims", "human_self_claims", "words")}
    summary["aggregate"] = agg
    summary["model"] = args.model_id
    summary["quant"] = args.quant
    summary["prompt_chars"] = {c: len(p) for c, p in prompts_free.items()}
    summary["prompt_head"] = {c: p[:220] for c, p in prompts_free.items()}

    with open(out_jsonl, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(out_summary, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n=== AGGREGATE ===", flush=True)
    for k, v in agg.items():
        print(f"{k}: {v}", flush=True)
    if "first_token_kl" in summary:
        print(f"first_token_kl: {summary['first_token_kl']}", flush=True)
    print(f"[spike] wrote {out_jsonl} and {out_summary}", flush=True)


if __name__ == "__main__":
    main()
