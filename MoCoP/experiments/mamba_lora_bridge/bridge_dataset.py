"""
bridge_dataset.py - Synthetic data pipeline for Phase 2 bridge training.

This module builds paired training examples for:
1. Mamba history ingestion over an exact 8192-token context window.
2. Qwen ChatML supervision with CrossEntropyLoss-compatible masking.

The factual training path masks every token except the exact factual answer.
The general evaluation path masks the prompt and scores only the assistant
response so it can be reused for perplexity tracking.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoTokenizer, PreTrainedTokenizerBase

MAMBA_MODEL_ID = "state-spaces/mamba-2.8b-hf"
# Keep the default aligned with the bridge target model so tokenizer/model IDs
# do not drift silently once training is wired up.
QWEN_MODEL_ID = "Qwen/Qwen3-4B"

MAX_MAMBA_HISTORY_TOKENS = 8192


def _cross_product(left: Sequence[str], right: Sequence[str]) -> List[str]:
    return [f"{lhs} {rhs}" for lhs in left for rhs in right]


def _prepositional_product(prepositions: Sequence[str], locations: Sequence[str]) -> List[str]:
    return [f"{prep} {location}" for prep in prepositions for location in locations]


NAME_POOL = [
    "Thornwick",
    "Jinx",
    "Mira",
    "Sable",
    "Kestrel",
    "Rook",
    "Lumen",
    "Iris",
    "Voss",
    "Nyra",
    "Marrow",
    "Orla",
    "Fen",
    "Cinder",
    "Pike",
    "Tamsin",
    "Elric",
    "Maelin",
    "Corvin",
    "Selka",
    "Bram",
    "Neris",
    "Talon",
    "Ysra",
    "Hollis",
    "Vael",
    "Torren",
    "Aveline",
    "Quill",
    "Sorrel",
    "Dorian",
    "Brindle",
]

MARKETS = _cross_product(
    ["Brass Lantern", "Southgate", "Salt Alley", "Moonwake", "Cinder Row", "North Quay"],
    ["Market", "Arcade", "Bazaar", "Exchange", "Stalls"],
)

INNS = _cross_product(
    ["Mosswell", "Red Sash", "Lantern", "Pilgrim's", "Quiet Kettle", "Riverglass"],
    ["Inn", "Hostel", "Rest", "House", "Lodge"],
)

SHRINES = _cross_product(
    ["Willow", "Ashwater", "Bellglass", "Northbank", "Cinder Bloom", "Sunkeep"],
    ["Chapel", "Shrine", "Cloister", "Sanctum", "Hospice"],
)

RELICS = _cross_product(
    ["storm", "amber", "glass", "sun", "iron", "moon"],
    ["key", "seal", "compass", "map", "prayer wheel"],
)

HIDING_PLACES = _prepositional_product(
    ["under the", "inside the", "beneath the", "behind the", "beyond the", "within the"],
    ["bell foundry", "flooded archive", "willow shrine", "cracked observatory", "east quay stairs"],
)

FERRIES = _cross_product(
    ["Moonwake", "Blackwater", "Siltbridge", "North Weir", "Ash Harbor", "Lantern Quay"],
    ["Pier", "Ferry", "Landing", "Dock", "Skiff"],
)

CARAVANS = _cross_product(
    ["copper", "salt", "glass", "amber", "cedar", "obsidian"],
    ["caravan", "convoy", "train", "wagon line", "trade band"],
)

TIME_PHRASES = _cross_product(
    ["before", "at", "after", "near", "just past", "well before"],
    ["dawn", "second bell", "moonrise", "midnight", "first light"],
)

EVENTS = _cross_product(
    ["the shipyard", "the market", "the bridge", "the tavern", "the guardhouse", "the customhouse"],
    ["fire", "riot", "collapse", "raid", "brawl", "murder"],
)

RELATIONSHIP_TYPES = [
    ("answers to", "answer to"),
    ("spies on", "spy on"),
    ("works for", "work for"),
    ("owes a debt to", "owe a debt to"),
    ("secretly funds", "secretly fund"),
    ("reports directly to", "report directly to"),
    ("buys stolen goods from", "buy stolen goods from"),
    ("takes orders from", "take orders from"),
    ("blackmails", "blackmail"),
    ("is hiding from", "hide from"),
    ("extorts money from", "extort money from"),
    ("sabotages", "sabotage"),
    ("smuggles for", "smuggle for"),
    ("provides an alibi for", "provide an alibi for"),
    ("launders coin for", "launder coin for"),
    ("forges documents for", "forge documents for"),
    ("bribes", "bribe"),
    ("steals from", "steal from"),
    ("assassinates targets for", "assassinate targets for"),
    ("has a blood feud with", "have a blood feud with"),
    ("is apprenticed to", "apprentice to"),
    ("trades secrets with", "trade secrets with"),
    ("distrusts", "distrust"),
    ("swore an oath to", "swear an oath to"),
    ("protects", "protect"),
    ("conspires with", "conspire with"),
    ("collects taxes for", "collect taxes for"),
    ("supplies weapons to", "supply weapons to"),
    ("buys silence from", "buy silence from"),
    ("shares a safehouse with", "share a safehouse with"),
    ("fences goods for", "fence goods for"),
]

CODE_COLORS = [
    "amber",
    "azure",
    "crimson",
    "ivory",
    "obsidian",
    "jade",
    "cobalt",
    "sable",
    "scarlet",
    "silver",
    "gold",
    "copper",
    "bronze",
    "teal",
    "violet",
    "indigo",
    "russet",
    "umber",
    "pearl",
    "smoke",
    "frost",
    "ember",
    "moss",
    "onyx",
    "coral",
    "sienna",
    "ochre",
    "garnet",
    "cerulean",
    "sepia",
]

CODE_ANIMALS = [
    "wolf",
    "lynx",
    "owl",
    "falcon",
    "raven",
    "viper",
    "otter",
    "stag",
    "heron",
    "fox",
    "hound",
    "eel",
    "hawk",
    "ibis",
    "badger",
    "ferret",
    "kite",
    "moorhen",
    "adder",
    "wren",
    "boar",
    "gull",
    "marten",
    "pike",
    "asp",
    "crow",
    "hare",
    "stoat",
    "ram",
    "newt",
]

FILLER_EVENTS = [
    "The market square is crowded while a porter argues over wet grain sacks.",
    "Rain beads on the cobblestones and every lantern throws a long gold smear.",
    "A kitchen runner cuts through the alley carrying bread and dried river fish.",
    "Two guards trade rumors about a caravan delayed by mud beyond the west gate.",
    "A bard retunes a travel harp beside the tavern hearth while cups knock together.",
    "A black cat slips under a handcart and vanishes beneath a drape of canvas.",
    "Steam rises from the tannery quarter and the whole street smells of lime and oak bark.",
    "Dock ropes creak against damp posts while gulls fight over a split crate of eels.",
]

PLAYER_ACTIONS = [
    "You pause to listen without drawing attention to yourself.",
    "You keep moving, letting the detail sink in with the rest of the night's noise.",
    "You mark the line mentally and say nothing.",
    "You nod once and let the conversation wash past you.",
    "You watch from the edge of the room and commit the detail to memory.",
]

AMBIENT_LINES = [
    "Someone laughs too loudly near the fountain and a clerk snaps a ledger shut.",
    "A stable hand complains that the south road is chewing wagon wheels to splinters.",
    "Lantern smoke gathers under the rafters while a crier reads tax revisions.",
    "A pair of apprentices compare bruises earned unloading stone from a river barge.",
    "The tavern shutters rattle when the wind comes in from the marsh.",
]

GENERAL_DIALOGUE_PAIRS = [
    (
        "Describe the square tonight.",
        "Lantern light slides over wet stone while merchants bicker under patched awnings.",
    ),
    (
        "What does the harbor sound like right now?",
        "Ropes knock against the piers, gulls scream over the fish stalls, and water slaps the black pilings.",
    ),
    (
        "Give me a quick read on the tavern.",
        "The tavern is crowded, warm, and loud enough that private whispers vanish under the room's hum.",
    ),
    (
        "How do the alleys feel after the rain?",
        "They feel slick, narrow, and full of reflected lanternlight, with runoff threading between broken stones.",
    ),
    (
        "What are the guards focused on tonight?",
        "They are watching the gates, delayed caravans, and anyone lingering too long near the customs ledgers.",
    ),
    (
        "Summarize the mood at the market.",
        "The market feels tense but alive, with hard bargaining, damp canvas, and everyone trying to close one more deal.",
    ),
    (
        "What would a newcomer notice first in this district?",
        "A newcomer would notice the smoke, the wet cobbles, and how every conversation seems half practical and half suspicious.",
    ),
    (
        "How is the weather affecting the city?",
        "The rain slows carts, slicks the streets, and drives most business under lanterns and awnings rather than out in the open.",
    ),
]

FACT_SYSTEM_PROMPT = (
    "You are a MUD recall assistant. Answer with only the exact requested fact. "
    "No explanation, no extra words, no punctuation unless it is part of the fact."
)

GENERAL_SYSTEM_PROMPT = (
    "You are a grounded fantasy MUD assistant. Reply naturally, briefly, and in-world."
)


@dataclass(frozen=True)
class BridgeDatasetConfig:
    num_samples: int
    mode: str = "fact"
    mamba_context_tokens: int = MAX_MAMBA_HISTORY_TOKENS
    max_qwen_tokens: int = 256
    min_post_target_tokens: int = 1024
    max_post_target_tokens: int = 4096
    distractor_injection_rate: float = 0.22
    seed: int = 0
    include_text: bool = True


@dataclass(frozen=True)
class FactRecord:
    fact_kind: str
    question: str
    answer: str
    injection_text: str


@dataclass(frozen=True)
class HistoryBlock:
    text: str
    token_ids: Tuple[int, ...]
    kind: str


def load_bridge_tokenizers(
    mamba_model_id: str = MAMBA_MODEL_ID,
    qwen_model_id: str = QWEN_MODEL_ID,
) -> Tuple[PreTrainedTokenizerBase, PreTrainedTokenizerBase]:
    mamba_tokenizer = AutoTokenizer.from_pretrained(mamba_model_id)
    qwen_tokenizer = AutoTokenizer.from_pretrained(qwen_model_id, use_fast=True)

    if qwen_tokenizer.pad_token_id is None:
        qwen_tokenizer.pad_token = qwen_tokenizer.eos_token

    return mamba_tokenizer, qwen_tokenizer


class BridgeDataset(Dataset):
    """
    Synthetic paired dataset for the Mamba-to-Qwen bridge.

    Modes:
    - "fact": factual retrieval supervision. Only answer tokens are unmasked.
    - "general": generic conversational supervision for perplexity tracking.
    """

    def __init__(
        self,
        config: BridgeDatasetConfig,
        mamba_tokenizer: Optional[PreTrainedTokenizerBase] = None,
        qwen_tokenizer: Optional[PreTrainedTokenizerBase] = None,
        mamba_model_id: str = MAMBA_MODEL_ID,
        qwen_model_id: str = QWEN_MODEL_ID,
        pools: Optional[Dict[str, List[Any]]] = None,
    ):
        if config.num_samples <= 0:
            raise ValueError("num_samples must be > 0")
        if config.mode not in {"fact", "general"}:
            raise ValueError(f"Unsupported dataset mode: {config.mode}")
        if config.mamba_context_tokens <= 0:
            raise ValueError("mamba_context_tokens must be > 0")
        if config.max_qwen_tokens <= 0:
            raise ValueError("max_qwen_tokens must be > 0")
        if config.min_post_target_tokens < 0 or config.max_post_target_tokens < config.min_post_target_tokens:
            raise ValueError("Invalid post-target token range")
        if config.mode == "fact" and config.min_post_target_tokens >= config.mamba_context_tokens:
            raise ValueError("min_post_target_tokens must stay below the Mamba context window")

        if mamba_tokenizer is None or qwen_tokenizer is None:
            loaded_mamba, loaded_qwen = load_bridge_tokenizers(
                mamba_model_id=mamba_model_id,
                qwen_model_id=qwen_model_id,
            )
            mamba_tokenizer = mamba_tokenizer or loaded_mamba
            qwen_tokenizer = qwen_tokenizer or loaded_qwen

        if qwen_tokenizer.pad_token_id is None:
            qwen_tokenizer.pad_token = qwen_tokenizer.eos_token

        self.config = config
        self.mode = config.mode
        self.mamba_tokenizer = mamba_tokenizer
        self.qwen_tokenizer = qwen_tokenizer
        self.qwen_pad_token_id = int(qwen_tokenizer.pad_token_id)
        self.pools = pools or {
            "NAME_POOL": NAME_POOL,
            "MARKETS": MARKETS,
            "INNS": INNS,
            "SHRINES": SHRINES,
            "RELICS": RELICS,
            "HIDING_PLACES": HIDING_PLACES,
            "FERRIES": FERRIES,
            "CARAVANS": CARAVANS,
            "EVENTS": EVENTS,
            "RELATIONSHIP_TYPES": RELATIONSHIP_TYPES,
            "FILLER_EVENTS": FILLER_EVENTS,
            "PLAYER_ACTIONS": PLAYER_ACTIONS,
            "AMBIENT_LINES": AMBIENT_LINES,
            "TIME_PHRASES": TIME_PHRASES,
            "GENERAL_DIALOGUE_PAIRS": GENERAL_DIALOGUE_PAIRS,
        }
        self._validate_qwen_chat_tokens()

    def __len__(self) -> int:
        if hasattr(self, "_disk_records"):
            return len(self._disk_records)
        return self.config.num_samples

    def __getitem__(self, index: int) -> Dict[str, Any]:
        if hasattr(self, "_disk_records"):
            record = self._disk_records[index]
            metadata = record["metadata"]
            
            q_ids = self._disk_qwen_ids[index]
            q_lbls = self._disk_qwen_labels[index]
            q_mask = self._disk_qwen_masks[index]
            
            seq_len = int(q_mask.sum().item())
            prompt_len = metadata["answer_span"][0]
            
            qwen_input_ids = q_ids[:seq_len]
            qwen_attention_mask = q_mask[:seq_len]
            qwen_labels = q_lbls[:seq_len]
            qwen_prompt_ids = q_ids[:prompt_len]
            qwen_prompt_attention_mask = torch.ones(prompt_len, dtype=torch.long)
            
            sample = {
                "sample_mode": record.get("sample_mode", getattr(self, "mode", "fact")),
                "mamba_history_ids": self._disk_mamba_ids[index],
                "mamba_attention_mask": torch.ones_like(self._disk_mamba_ids[index]),
                "qwen_input_ids": qwen_input_ids,
                "qwen_prompt_ids": qwen_prompt_ids,
                "qwen_attention_mask": qwen_attention_mask,
                "qwen_prompt_attention_mask": qwen_prompt_attention_mask,
                "qwen_labels": qwen_labels,
                "answer_text": record["answer"],
                "question_text": record["question"],
                "metadata": metadata,
            }
            if "mamba_context_text" in record:
                sample["mamba_context_text"] = record["mamba_context_text"]
            if "qwen_chat_text" in record:
                sample["qwen_chat_text"] = record["qwen_chat_text"]
            return sample

        rng = random.Random(self.config.seed + (index * 104729) + (17 if self.mode == "general" else 0))

        if self.mode == "fact":
            item = self._build_fact_item(index=index, rng=rng)
        else:
            item = self._build_general_item(index=index, rng=rng)

        sample: Dict[str, Any] = {
            "sample_mode": self.mode,
            "mamba_history_ids": item["mamba_history_ids"],
            "mamba_attention_mask": item["mamba_attention_mask"],
            "qwen_input_ids": item["qwen_input_ids"],
            "qwen_prompt_ids": item["qwen_prompt_ids"],
            "qwen_attention_mask": item["qwen_attention_mask"],
            "qwen_prompt_attention_mask": item["qwen_prompt_attention_mask"],
            "qwen_labels": item["qwen_labels"],
            "answer_text": item["answer_text"],
            "question_text": item["question_text"],
            "metadata": item["metadata"],
        }
        if self.config.include_text:
            sample["mamba_context_text"] = item["mamba_context_text"]
            sample["qwen_chat_text"] = item["qwen_chat_text"]
        return sample

    @classmethod
    def from_disk(cls, path: str | Path) -> "BridgeDataset":
        path = Path(path)
        with open(path / "dataset.json", "r") as f:
            data = json.load(f)
            
        instance = cls.__new__(cls)
        
        # Backward compatibility for old raw-list format
        if isinstance(data, list):
            records = data
            instance.mode = records[0].get("sample_mode", "fact") if records else "fact"
            instance.config = BridgeDatasetConfig(
                num_samples=len(records), 
                mode=instance.mode
            )
            instance.qwen_pad_token_id = 151643 # default fallback
        else:
            records = data["records"]
            instance.mode = data.get("mode", "fact")
            instance.qwen_pad_token_id = data.get("pad_token_id", 151643)
            # Restore enough config to allow re-saving
            instance.config = BridgeDatasetConfig(
                num_samples=len(records),
                mode=instance.mode,
                max_qwen_tokens=data.get("max_qwen_tokens", 256)
            )

        for rec in records:
            if "metadata" in rec and "answer_span" in rec["metadata"]:
                rec["metadata"]["answer_span"] = tuple(rec["metadata"]["answer_span"])
                
        instance._disk_records = records
        
        # Load tensors without requiring Tokenizers
        instance._disk_mamba_ids = torch.load(path / "mamba_ids.pt", weights_only=True)
        instance._disk_qwen_ids = torch.load(path / "qwen_ids.pt", weights_only=True)
        instance._disk_qwen_labels = torch.load(path / "qwen_labels.pt", weights_only=True)
        instance._disk_qwen_masks = torch.load(path / "qwen_masks.pt", weights_only=True)
        
        # Fallback pad ID extraction only if not in manifest and old format
        if isinstance(data, list) and instance._disk_qwen_masks.numel() > 0:
            pad_mask = instance._disk_qwen_masks[0] == 0
            if pad_mask.any():
                instance.qwen_pad_token_id = int(instance._disk_qwen_ids[0][pad_mask][0].item())
                
        return instance

    def save_to_disk(self, path: str | Path) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        records = []
        mamba_ids = []
        qwen_ids = []
        qwen_labels = []
        qwen_masks = []
        
        for i in range(len(self)):
            sample = self[i]
            record = {
                "question": sample["question_text"],
                "answer": sample["answer_text"],
                "fact_kind": sample["metadata"]["fact_kind"],
                "metadata": sample["metadata"],
                "sample_mode": sample.get("sample_mode", self.mode)
            }
            if "mamba_context_text" in sample:
                record["mamba_context_text"] = sample["mamba_context_text"]
            if "qwen_chat_text" in sample:
                record["qwen_chat_text"] = sample["qwen_chat_text"]
            records.append(record)
            
            mamba_ids.append(sample["mamba_history_ids"])
            
            q_ids = sample["qwen_input_ids"]
            q_lbls = sample["qwen_labels"]
            q_mask = sample["qwen_attention_mask"]
            
            pad_len = self.config.max_qwen_tokens - len(q_ids)
            if pad_len > 0:
                pad_id = torch.full((pad_len,), self.qwen_pad_token_id, dtype=torch.long)
                q_ids = torch.cat([q_ids, pad_id])
                
                pad_lbl = torch.full((pad_len,), -100, dtype=torch.long)
                q_lbls = torch.cat([q_lbls, pad_lbl])
                
                pad_msk = torch.zeros(pad_len, dtype=torch.long)
                q_mask = torch.cat([q_mask, pad_msk])
                
            qwen_ids.append(q_ids)
            qwen_labels.append(q_lbls)
            qwen_masks.append(q_mask)
            
        manifest = {
            "version": 1,
            "mode": self.mode,
            "pad_token_id": self.qwen_pad_token_id,
            "max_qwen_tokens": self.config.max_qwen_tokens,
            "records": records,
        }
            
        with open(path / "dataset.json", "w") as f:
            json.dump(manifest, f, indent=2)
            
        torch.save(torch.stack(mamba_ids, dim=0), path / "mamba_ids.pt")
        torch.save(torch.stack(qwen_ids, dim=0), path / "qwen_ids.pt")
        torch.save(torch.stack(qwen_labels, dim=0), path / "qwen_labels.pt")
        torch.save(torch.stack(qwen_masks, dim=0), path / "qwen_masks.pt")

    def _validate_qwen_chat_tokens(self) -> None:
        all_specials = set(getattr(self.qwen_tokenizer, "all_special_tokens", []) or [])
        required = {"<|im_start|>", "<|im_end|>"}
        if not required.issubset(all_specials):
            raise ValueError(
                "Qwen tokenizer is missing ChatML special tokens. "
                f"Expected {sorted(required)}, found {sorted(all_specials)}."
            )

    def _encode_mamba(self, text: str) -> Tuple[int, ...]:
        return tuple(self.mamba_tokenizer.encode(text, add_special_tokens=False))

    def _encode_qwen(self, text: str) -> List[int]:
        return list(self.qwen_tokenizer.encode(text, add_special_tokens=False))

    def _make_history_block(self, text: str, kind: str) -> HistoryBlock:
        return HistoryBlock(text=text, token_ids=self._encode_mamba(text), kind=kind)

    def _random_name(self, rng: random.Random, exclude: Optional[Sequence[str]] = None) -> str:
        exclude_set = set(exclude or [])
        choices = [name for name in self.pools["NAME_POOL"] if name not in exclude_set]
        if not choices:
            raise RuntimeError("Name pool exhausted")
        return rng.choice(choices)

    def _make_code_phrase(self, index: int, rng: random.Random) -> str:
        color = CODE_COLORS[index % len(CODE_COLORS)]
        animal = CODE_ANIMALS[(index * 3) % len(CODE_ANIMALS)]
        suffix = 100 + ((index * 17 + rng.randint(0, 99)) % 900)
        return f"{color}-{animal}-{suffix}"

    def _make_fact_record(
        self,
        index: int,
        rng: random.Random,
        exclude_answers: Optional[Sequence[str]] = None,
    ) -> FactRecord:
        excluded = set(exclude_answers or [])
        fact_kind = (
            "merchant_identity",
            "innkeeper_identity",
            "healer_identity",
            "relic_location",
            "ferry_password",
            "caravan_time",
            "event_witness",
            "npc_relationship",
        )[index % 8]

        for attempt in range(32):
            if fact_kind == "merchant_identity":
                market = rng.choice(self.pools["MARKETS"])
                merchant = self._random_name(rng)
                answer = merchant
                question = f"Who is the merchant in {market}?"
                injection = (
                    "[private ledger]\n"
                    f"A guild runner mutters that the licensed merchant in {market} is {merchant}.\n"
                    "[memory]\nRemember the merchant's name exactly.\n\n"
                )
            elif fact_kind == "innkeeper_identity":
                inn = rng.choice(self.pools["INNS"])
                innkeeper = self._random_name(rng)
                answer = innkeeper
                question = f"Who keeps the keys at {inn}?"
                injection = (
                    "[tavern whisper]\n"
                    f"The night clerk says the key-ring for {inn} stays with {innkeeper}.\n"
                    "[memory]\nKeep that name for later.\n\n"
                )
            elif fact_kind == "healer_identity":
                shrine = rng.choice(self.pools["SHRINES"])
                healer = self._random_name(rng)
                answer = healer
                question = f"Who is the healer at {shrine}?"
                injection = (
                    "[chapel note]\n"
                    f"A pilgrim quietly points out that the healer serving {shrine} is {healer}.\n"
                    "[memory]\nDo not lose the healer's name.\n\n"
                )
            elif fact_kind == "relic_location":
                relic = rng.choice(self.pools["RELICS"])
                location = rng.choice(self.pools["HIDING_PLACES"])
                answer = location
                question = f"Where is the {relic} hidden?"
                injection = (
                    "[smuggler note]\n"
                    f"Someone hisses that the {relic} is hidden {location}.\n"
                    "[memory]\nHold the location exactly as spoken.\n\n"
                )
            elif fact_kind == "ferry_password":
                ferry = rng.choice(self.pools["FERRIES"])
                code = self._make_code_phrase(index + attempt, rng)
                answer = code
                question = f"What is the ferry password for {ferry}?"
                injection = (
                    "[dock whisper]\n"
                    f"A ferryman says the spoken password for {ferry} is {code}.\n"
                    "[memory]\nRepeat it only when asked.\n\n"
                )
            elif fact_kind == "caravan_time":
                caravan = rng.choice(self.pools["CARAVANS"])
                arrival = rng.choice(self.pools["TIME_PHRASES"])
                answer = arrival
                question = f"When does the {caravan} arrive?"
                injection = (
                    "[caravan notice]\n"
                    f"A mud-stained dispatcher confirms the {caravan} arrives {arrival}.\n"
                    "[memory]\nKeep the timing exact.\n\n"
                )
            elif fact_kind == "event_witness":
                event = rng.choice(self.pools["EVENTS"])
                witness = self._random_name(rng)
                answer = witness
                question = f"Who witnessed {event}?"
                injection = (
                    "[overheard]\n"
                    f"A soldier says {witness} was present at {event}.\n"
                    "[memory]\nRemember the witness.\n\n"
                )
            else:
                rel_3rd, rel_base = rng.choice(self.pools["RELATIONSHIP_TYPES"])
                name_a = self._random_name(rng)
                name_b = self._random_name(rng, exclude=[name_a])
                answer = name_b
                question = f"Who does {name_a} {rel_base}?"
                injection = (
                    "[rumor]\n"
                    f"The barkeep mentions {name_a} {rel_3rd} {name_b}.\n"
                    "[memory]\nNote the connection.\n\n"
                )

            if answer not in excluded:
                return FactRecord(
                    fact_kind=fact_kind,
                    question=question,
                    answer=answer,
                    injection_text=injection,
                )

        raise RuntimeError(f"Could not sample a unique fact after repeated attempts: kind={fact_kind}")

    def _render_filler_block(self, rng: random.Random) -> str:
        return (
            "[room]\n"
            f"{rng.choice(self.pools['FILLER_EVENTS'])}\n"
            "[player]\n"
            f"{rng.choice(self.pools['PLAYER_ACTIONS'])}\n"
            "[ambient]\n"
            f"{rng.choice(self.pools['AMBIENT_LINES'])}\n\n"
        )

    def _render_fact_block(self, fact: FactRecord, rng: random.Random) -> str:
        return (
            "[conversation]\n"
            f"{rng.choice(self.pools['AMBIENT_LINES'])}\n"
            f"{fact.injection_text}"
            "[player]\n"
            f"{rng.choice(self.pools['PLAYER_ACTIONS'])}\n\n"
        )

    def _render_compact_fact_block(self, fact: FactRecord) -> str:
        return (
            "[memory]\n"
            f"{fact.question}\n"
            f"{fact.answer}\n\n"
        )

    def _build_target_history_block(self, fact: FactRecord, rng: random.Random) -> HistoryBlock:
        candidates = [
            self._render_fact_block(fact, rng=rng),
            self._render_compact_fact_block(fact),
        ]
        for text in candidates:
            block = self._make_history_block(text, kind="target_fact")
            if len(block.token_ids) <= self.config.mamba_context_tokens:
                return block
        raise RuntimeError("Target fact block exceeds the entire Mamba context window")

    def _build_fact_history(self, index: int, rng: random.Random) -> Tuple[torch.Tensor, str, FactRecord, int]:
        target_fact = self._make_fact_record(index=index, rng=rng)
        target_block = self._build_target_history_block(target_fact, rng=rng)

        max_suffix_budget = max(0, self.config.mamba_context_tokens - len(target_block.token_ids))
        suffix_budget_low = min(self.config.min_post_target_tokens, max_suffix_budget)
        suffix_budget_high = min(self.config.max_post_target_tokens, max_suffix_budget)
        if suffix_budget_high < suffix_budget_low:
            suffix_budget_high = suffix_budget_low

        suffix_blocks: List[HistoryBlock] = []
        suffix_tokens = 0
        target_suffix_budget = rng.randint(suffix_budget_low, suffix_budget_high)

        distractor_index = index + 1
        while suffix_tokens < target_suffix_budget:
            if rng.random() < self.config.distractor_injection_rate:
                distractor_fact = self._make_fact_record(
                    index=distractor_index,
                    rng=rng,
                    exclude_answers=[target_fact.answer],
                )
                distractor_index += 1
                block = self._make_history_block(
                    self._render_fact_block(distractor_fact, rng=rng),
                    kind="distractor_fact",
                )
            else:
                block = self._make_history_block(
                    self._render_filler_block(rng),
                    kind="filler",
                )
            suffix_blocks.append(block)
            suffix_tokens += len(block.token_ids)

        prefix_blocks: List[HistoryBlock] = []
        total_tokens = len(target_block.token_ids) + suffix_tokens
        while total_tokens < self.config.mamba_context_tokens:
            if rng.random() < self.config.distractor_injection_rate:
                distractor_fact = self._make_fact_record(
                    index=distractor_index,
                    rng=rng,
                    exclude_answers=[target_fact.answer],
                )
                distractor_index += 1
                block = self._make_history_block(
                    self._render_fact_block(distractor_fact, rng=rng),
                    kind="distractor_fact",
                )
            else:
                block = self._make_history_block(
                    self._render_filler_block(rng),
                    kind="filler",
                )
            prefix_blocks.append(block)
            total_tokens += len(block.token_ids)

        ordered_blocks = prefix_blocks + [target_block] + suffix_blocks
        full_ids: List[int] = []
        for block in ordered_blocks:
            full_ids.extend(block.token_ids)

        if len(full_ids) < self.config.mamba_context_tokens:
            raise RuntimeError("Failed to build a full Mamba context window")

        final_ids = full_ids[-self.config.mamba_context_tokens :]
        history_ids = torch.tensor(final_ids, dtype=torch.long)

        if self.config.include_text:
            history_text = self.mamba_tokenizer.decode(final_ids, skip_special_tokens=False)
        else:
            history_text = ""

        return history_ids, history_text, target_fact, suffix_tokens

    def _build_general_history(self, index: int, rng: random.Random) -> Tuple[torch.Tensor, str]:
        blocks: List[HistoryBlock] = []
        total_tokens = 0
        # Keep general-mode distractor fact IDs far away from fact-mode indices.
        # This assumes per-split sample counts stay comfortably below 500k.
        distractor_index = index + 500_000

        while total_tokens < self.config.mamba_context_tokens:
            if rng.random() < self.config.distractor_injection_rate * 0.5:
                block = self._make_history_block(
                    self._render_fact_block(self._make_fact_record(distractor_index, rng=rng), rng=rng),
                    kind="ambient_fact",
                )
                distractor_index += 1
            else:
                block = self._make_history_block(
                    self._render_filler_block(rng),
                    kind="filler",
                )
            blocks.append(block)
            total_tokens += len(block.token_ids)

        full_ids: List[int] = []
        for block in blocks:
            full_ids.extend(block.token_ids)
        final_ids = full_ids[-self.config.mamba_context_tokens :]
        history_ids = torch.tensor(final_ids, dtype=torch.long)

        if self.config.include_text:
            history_text = self.mamba_tokenizer.decode(final_ids, skip_special_tokens=False)
        else:
            history_text = ""

        return history_ids, history_text

    def _build_chatml_example(
        self,
        system_prompt: str,
        user_prompt: str,
        assistant_text: str,
    ) -> Dict[str, Any]:
        prefix_text = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{user_prompt}<|im_end|>\n"
            "<|im_start|>assistant\n"
        )
        suffix_text = "<|im_end|>\n"

        prefix_ids = self._encode_qwen(prefix_text)
        assistant_ids = self._encode_qwen(assistant_text)
        suffix_ids = self._encode_qwen(suffix_text)

        input_ids = prefix_ids + assistant_ids + suffix_ids
        if len(input_ids) > self.config.max_qwen_tokens:
            raise RuntimeError(
                "Qwen sequence exceeded max_qwen_tokens "
                f"({len(input_ids)} > {self.config.max_qwen_tokens}) for prompt: {user_prompt!r}"
            )

        labels = ([-100] * len(prefix_ids)) + assistant_ids + ([-100] * len(suffix_ids))
        attention_mask = [1] * len(input_ids)
        chat_text = prefix_text + assistant_text + suffix_text

        return {
            "qwen_input_ids": torch.tensor(input_ids, dtype=torch.long),
            "qwen_prompt_ids": torch.tensor(prefix_ids, dtype=torch.long),
            "qwen_attention_mask": torch.tensor(attention_mask, dtype=torch.long),
            "qwen_prompt_attention_mask": torch.tensor([1] * len(prefix_ids), dtype=torch.long),
            "qwen_labels": torch.tensor(labels, dtype=torch.long),
            "qwen_chat_text": chat_text,
            "answer_span": (len(prefix_ids), len(prefix_ids) + len(assistant_ids)),
        }

    def _build_fact_item(self, index: int, rng: random.Random) -> Dict[str, Any]:
        mamba_history_ids, history_text, target_fact, suffix_tokens = self._build_fact_history(index=index, rng=rng)
        chat = self._build_chatml_example(
            system_prompt=FACT_SYSTEM_PROMPT,
            user_prompt=target_fact.question,
            assistant_text=target_fact.answer,
        )

        qwen_labels = chat["qwen_labels"]
        unmasked = qwen_labels[qwen_labels != -100]
        if unmasked.numel() == 0:
            raise RuntimeError("Factual sample produced no supervised answer tokens")

        return {
            "mamba_history_ids": mamba_history_ids,
            "mamba_attention_mask": torch.ones_like(mamba_history_ids, dtype=torch.long),
            "qwen_input_ids": chat["qwen_input_ids"],
            "qwen_prompt_ids": chat["qwen_prompt_ids"],
            "qwen_attention_mask": chat["qwen_attention_mask"],
            "qwen_prompt_attention_mask": chat["qwen_prompt_attention_mask"],
            "qwen_labels": qwen_labels,
            "answer_text": target_fact.answer,
            "question_text": target_fact.question,
            "mamba_context_text": history_text,
            "qwen_chat_text": chat["qwen_chat_text"],
            "metadata": {
                "fact_kind": target_fact.fact_kind,
                "answer_span": chat["answer_span"],
                "suffix_token_distance": suffix_tokens,
                "mamba_context_tokens": int(mamba_history_ids.shape[0]),
                "qwen_tokens": int(chat["qwen_input_ids"].shape[0]),
            },
        }

    def _build_general_item(self, index: int, rng: random.Random) -> Dict[str, Any]:
        mamba_history_ids, history_text = self._build_general_history(index=index, rng=rng)
        pairs = self.pools["GENERAL_DIALOGUE_PAIRS"]
        question_text, answer_text = pairs[index % len(pairs)]
        chat = self._build_chatml_example(
            system_prompt=GENERAL_SYSTEM_PROMPT,
            user_prompt=question_text,
            assistant_text=answer_text,
        )

        return {
            "mamba_history_ids": mamba_history_ids,
            "mamba_attention_mask": torch.ones_like(mamba_history_ids, dtype=torch.long),
            "qwen_input_ids": chat["qwen_input_ids"],
            "qwen_prompt_ids": chat["qwen_prompt_ids"],
            "qwen_attention_mask": chat["qwen_attention_mask"],
            "qwen_prompt_attention_mask": chat["qwen_prompt_attention_mask"],
            "qwen_labels": chat["qwen_labels"],
            "answer_text": answer_text,
            "question_text": question_text,
            "mamba_context_text": history_text,
            "qwen_chat_text": chat["qwen_chat_text"],
            "metadata": {
                "fact_kind": "general_eval",
                "answer_span": chat["answer_span"],
                "mamba_context_tokens": int(mamba_history_ids.shape[0]),
                "qwen_tokens": int(chat["qwen_input_ids"].shape[0]),
            },
        }


class BridgeBatchCollator:
    """Pad variable-length Qwen sequences while preserving fixed Mamba windows."""

    def __init__(self, qwen_pad_token_id: int):
        self.qwen_pad_token_id = int(qwen_pad_token_id)

    def __call__(self, batch: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        if not batch:
            raise ValueError("Cannot collate an empty batch")

        mamba_history_ids = torch.stack([sample["mamba_history_ids"] for sample in batch], dim=0)
        mamba_attention_mask = torch.stack([sample["mamba_attention_mask"] for sample in batch], dim=0)

        max_qwen_len = max(int(sample["qwen_input_ids"].shape[0]) for sample in batch)
        max_qwen_prompt_len = max(int(sample["qwen_prompt_ids"].shape[0]) for sample in batch)
        batch_size = len(batch)

        qwen_input_ids = torch.full(
            (batch_size, max_qwen_len),
            fill_value=self.qwen_pad_token_id,
            dtype=torch.long,
        )
        qwen_attention_mask = torch.zeros((batch_size, max_qwen_len), dtype=torch.long)
        qwen_labels = torch.full((batch_size, max_qwen_len), fill_value=-100, dtype=torch.long)
        qwen_prompt_ids = torch.full(
            (batch_size, max_qwen_prompt_len),
            fill_value=self.qwen_pad_token_id,
            dtype=torch.long,
        )
        qwen_prompt_attention_mask = torch.zeros((batch_size, max_qwen_prompt_len), dtype=torch.long)

        for row, sample in enumerate(batch):
            seq_len = int(sample["qwen_input_ids"].shape[0])
            prompt_len = int(sample["qwen_prompt_ids"].shape[0])
            qwen_input_ids[row, :seq_len] = sample["qwen_input_ids"]
            qwen_attention_mask[row, :seq_len] = sample["qwen_attention_mask"]
            qwen_labels[row, :seq_len] = sample["qwen_labels"]
            qwen_prompt_ids[row, :prompt_len] = sample["qwen_prompt_ids"]
            qwen_prompt_attention_mask[row, :prompt_len] = sample["qwen_prompt_attention_mask"]

        collated: Dict[str, Any] = {
            "sample_mode": [sample["sample_mode"] for sample in batch],
            "mamba_history_ids": mamba_history_ids,
            "mamba_attention_mask": mamba_attention_mask,
            "qwen_input_ids": qwen_input_ids,
            "qwen_prompt_ids": qwen_prompt_ids,
            "qwen_attention_mask": qwen_attention_mask,
            "qwen_prompt_attention_mask": qwen_prompt_attention_mask,
            "qwen_labels": qwen_labels,
            "answer_text": [sample["answer_text"] for sample in batch],
            "question_text": [sample["question_text"] for sample in batch],
            "metadata": [sample["metadata"] for sample in batch],
        }

        if "mamba_context_text" in batch[0]:
            collated["mamba_context_text"] = [sample["mamba_context_text"] for sample in batch]
        if "qwen_chat_text" in batch[0]:
            collated["qwen_chat_text"] = [sample["qwen_chat_text"] for sample in batch]

        return collated


def build_bridge_dataloader(
    dataset_config: BridgeDatasetConfig,
    batch_size: int,
    shuffle: bool,
    num_workers: int = 0,
    pin_memory: bool = False,
    drop_last: bool = False,
    mamba_tokenizer: Optional[PreTrainedTokenizerBase] = None,
    qwen_tokenizer: Optional[PreTrainedTokenizerBase] = None,
    mamba_model_id: str = MAMBA_MODEL_ID,
    qwen_model_id: str = QWEN_MODEL_ID,
) -> DataLoader:
    dataset = BridgeDataset(
        config=dataset_config,
        mamba_tokenizer=mamba_tokenizer,
        qwen_tokenizer=qwen_tokenizer,
        mamba_model_id=mamba_model_id,
        qwen_model_id=qwen_model_id,
    )
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=drop_last,
        collate_fn=BridgeBatchCollator(dataset.qwen_pad_token_id),
    )


def build_splits(
    config: BridgeDatasetConfig,
    mamba_tokenizer: Optional[PreTrainedTokenizerBase] = None,
    qwen_tokenizer: Optional[PreTrainedTokenizerBase] = None,
) -> Tuple[BridgeDataset, BridgeDataset, BridgeDataset]:
    import dataclasses

    n = config.num_samples
    if n == 750:
        n_train, n_val, n_test = 500, 150, 100
    else:
        n_test = max(1, int(n * 0.1333))
        n_val = max(1, int(n * 0.2))
        n_train = n - n_val - n_test

    r_train = n_train / n
    r_val = n_val / n

    rng = random.Random(config.seed + 9_999_999)
    
    global_pools = {
        "NAME_POOL": NAME_POOL,
        "MARKETS": MARKETS,
        "INNS": INNS,
        "SHRINES": SHRINES,
        "RELICS": RELICS,
        "HIDING_PLACES": HIDING_PLACES,
        "FERRIES": FERRIES,
        "CARAVANS": CARAVANS,
        "EVENTS": EVENTS,
        "RELATIONSHIP_TYPES": RELATIONSHIP_TYPES,
        "FILLER_EVENTS": FILLER_EVENTS,
        "PLAYER_ACTIONS": PLAYER_ACTIONS,
        "AMBIENT_LINES": AMBIENT_LINES,
        "TIME_PHRASES": TIME_PHRASES,
        "GENERAL_DIALOGUE_PAIRS": GENERAL_DIALOGUE_PAIRS,
    }

    train_pools = {}
    val_pools = {}
    test_pools = {}

    for name, pool in global_pools.items():
        shuffled = list(pool)
        rng.shuffle(shuffled)
        
        pcnt = len(shuffled)
        if pcnt < 3:
            train_pools[name] = list(pool)
            val_pools[name] = list(pool)
            test_pools[name] = list(pool)
        else:
            c_train = max(1, int(pcnt * r_train))
            c_val = max(1, int(pcnt * r_val))
            if c_train + c_val >= pcnt:
                c_train = max(1, c_train - 1)
                c_val = max(1, c_val - 1)
                
            train_pools[name] = shuffled[:c_train]
            val_pools[name] = shuffled[c_train : c_train + c_val]
            test_pools[name] = shuffled[c_train + c_val :]

    train_cfg = dataclasses.replace(config, num_samples=n_train, seed=config.seed + 1_000_000)
    val_cfg = dataclasses.replace(config, num_samples=n_val, seed=config.seed + 2_000_000)
    test_cfg = dataclasses.replace(config, num_samples=n_test, seed=config.seed + 3_000_000)

    train_ds = BridgeDataset(train_cfg, mamba_tokenizer, qwen_tokenizer, pools=train_pools)
    val_ds = BridgeDataset(val_cfg, mamba_tokenizer, qwen_tokenizer, pools=val_pools)
    test_ds = BridgeDataset(test_cfg, mamba_tokenizer, qwen_tokenizer, pools=test_pools)

    return train_ds, val_ds, test_ds


__all__ = [
    "BridgeBatchCollator",
    "BridgeDataset",
    "BridgeDatasetConfig",
    "MAMBA_MODEL_ID",
    "MAX_MAMBA_HISTORY_TOKENS",
    "QWEN_MODEL_ID",
    "build_bridge_dataloader",
    "build_splits",
    "load_bridge_tokenizers",
]
