from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

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
                "Set HONGSTR_LLM_MODE=ollama (recommended) or qwen and configure endpoint/model."
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


@dataclass
class LocalOllamaLLM(LLMAdapter):
    endpoint: str = "http://127.0.0.1:11434"
    model: str = "qwen2.5:7b"
    timeout: int = 8

    def _chat_url(self) -> str:
        base = self.endpoint.rstrip("/")
        if base.endswith("/api/chat"):
            return base
        return f"{base}/api/chat"

    @staticmethod
    def _extract_content(data: Any) -> str:
        if not isinstance(data, dict):
            raise RuntimeError("Ollama endpoint returned non-object response")

        message = data.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content

        response = data.get("response")
        if isinstance(response, str) and response.strip():
            return response

        raise RuntimeError("Ollama response missing message.content/response")

    def generate(self, decision_prompt: str) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
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
        }
        response = requests.post(self._chat_url(), json=payload, timeout=self.timeout)
        response.raise_for_status()
        return self._extract_content(response.json())


def build_llm_from_env() -> tuple[LLMAdapter, str]:
    mode = os.getenv("HONGSTR_LLM_MODE", "null").strip().lower()
    endpoint = os.getenv("HONGSTR_LLM_ENDPOINT", "").strip()
    model = os.getenv("HONGSTR_LLM_MODEL", "qwen2.5:7b")
    timeout = int(os.getenv("HONGSTR_LLM_TIMEOUT", "8"))

    if mode == "ollama":
        endpoint = endpoint or "http://127.0.0.1:11434"
        return LocalOllamaLLM(endpoint=endpoint, model=model, timeout=timeout), "ollama"

    if mode == "qwen":
        if not endpoint:
            return NullLLM(reason="HONGSTR_LLM_ENDPOINT missing; fallback to null mode"), "null"
        return LocalQwenLLM(endpoint=endpoint, model=model, timeout=timeout), "qwen"

    return NullLLM(reason="HONGSTR_LLM_MODE is not supported"), "null"
