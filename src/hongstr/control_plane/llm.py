from __future__ import annotations

import json
import os
from dataclasses import dataclass

import requests


class LLMAdapter:
    def generate(self, decision_prompt: str) -> str:
        raise NotImplementedError


@dataclass
class NullLLM(LLMAdapter):
    reason: str = "LLM disabled"

    def generate(self, decision_prompt: str) -> str:
        payload = {
            "status": "WARN",
            "diagnosis": "Local LLM unavailable",
            "summary": self.reason,
            "next_tasks": ["Continue pipeline execution without control-plane automation."],
            "remediation_suggestions": [
                "Set HONGSTR_LLM_MODE=qwen and provide HONGSTR_LLM_ENDPOINT when local server is ready."
            ],
            "actions": [],
            "notes": ["NullLLM fallback in use."],
        }
        return json.dumps(payload, ensure_ascii=True)


@dataclass
class LocalQwenLLM(LLMAdapter):
    endpoint: str
    model: str
    timeout: int = 8

    def generate(self, decision_prompt: str) -> str:
        if not self.endpoint:
            raise RuntimeError("HONGSTR_LLM_ENDPOINT is not configured")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are HONGSTR control-plane advisor. Output strict JSON only. "
                        "No markdown, no prose outside JSON."
                    ),
                },
                {"role": "user", "content": decision_prompt},
            ],
            "temperature": 0.0,
        }

        response = requests.post(self.endpoint, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict):
            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                message = choices[0].get("message", {})
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content
            text = data.get("output_text")
            if isinstance(text, str) and text.strip():
                return text

        raise RuntimeError("Qwen endpoint returned unsupported response format")


def build_llm_from_env() -> tuple[LLMAdapter, str]:
    mode = os.getenv("HONGSTR_LLM_MODE", "null").strip().lower()
    endpoint = os.getenv("HONGSTR_LLM_ENDPOINT", "").strip()
    model = os.getenv("HONGSTR_LLM_MODEL", "qwen")
    timeout = int(os.getenv("HONGSTR_LLM_TIMEOUT", "8"))

    if mode != "qwen":
        return NullLLM(reason="HONGSTR_LLM_MODE is not qwen"), "null"

    if not endpoint:
        return NullLLM(reason="HONGSTR_LLM_ENDPOINT missing; fallback to null mode"), "null"

    return LocalQwenLLM(endpoint=endpoint, model=model, timeout=timeout), "qwen"
