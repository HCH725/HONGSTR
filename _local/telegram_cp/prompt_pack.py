#!/usr/bin/env python3
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PACK_DIR = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "prompt_packs"
    / "hongstr_ollama_pack"
    / "prompts"
)

_DEFAULT_OVERLAY = "overlay_qwen2.5_7b_instruct.md"


@lru_cache(maxsize=None)
def load_text(path: Path | str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


@lru_cache(maxsize=None)
def select_overlay(model_name: str) -> str:
    normalized = (model_name or "").strip().lower()
    if "qwen2.5-coder:7b-instruct" in normalized or "qwen2.5-coder" in normalized:
        return "overlay_qwen2.5-coder_7b_instruct.md"
    if "deepseek-r1:7b" in normalized or "deepseek-r1" in normalized:
        return "overlay_deepseek-r1_7b.md"
    if "qwen2.5:7b-instruct" in normalized or "qwen2.5" in normalized:
        return _DEFAULT_OVERLAY
    return _DEFAULT_OVERLAY


@lru_cache(maxsize=None)
def build_system_prompt(model_name: str) -> str:
    parts = (
        load_text(PACK_DIR / "base_system_prompt.md"),
        load_text(PACK_DIR / select_overlay(model_name)),
        load_text(PACK_DIR / "injection_contract.md"),
    )
    return "\n\n".join(part for part in parts if part).strip()
