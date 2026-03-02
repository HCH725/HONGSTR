from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from json import JSONDecodeError
from typing import Any, Callable, Optional

from .schemas_reasoning import ReasoningAnalysis

# Environment overrides
OLLAMA_ENDPOINT = os.getenv("HONGSTR_LLM_ENDPOINT", "http://127.0.0.1:11434")
REASONING_MODEL = os.getenv("HONGSTR_REASONING_MODEL", "deepseek-r1:7b")
REASONING_TIMEOUT = int(os.getenv("HONGSTR_REASONING_TIMEOUT", "120"))
DEBUG_JSON = os.getenv("HONGSTR_DEBUG_JSON", "0") == "1"
REFRESH_HINT = "bash scripts/refresh_state.sh"
ALLOWED_STATUS = {"OK", "WARN", "FAIL", "UNKNOWN"}
RAG_SEARCH_TOOL_NAME = "rag_search"

logger = logging.getLogger("reasoning_client")

def _coerce_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        out = []
        for item in value:
            s = str(item).strip()
            if s:
                out.append(s)
        return out
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else []
    return []


def _normalize_status(value: Any, default: str = "UNKNOWN") -> str:
    status = str(value or default).strip().upper()
    return status if status in ALLOWED_STATUS else default


def _message_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    chunks.append(text)
                else:
                    chunks.append(str(item))
        return "\n".join(chunks).strip()
    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            return text
    return str(content or "").strip()


def _extract_first_json_object(text: str) -> dict[str, Any] | None:
    """Scan left-to-right and decode the first balanced JSON object."""
    if not isinstance(text, str):
        return None
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[idx:])
        except JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _extract_reasoning_payload(raw_response: str) -> tuple[dict[str, Any] | None, str]:
    try:
        outer = json.loads(raw_response)
    except Exception:
        return None, "outer_json_unreadable"

    # Priority 1: outer JSON payload already matches the contract
    if isinstance(outer, dict) and (
        isinstance(outer.get("status"), str)
        or "actions" in outer
        or "problem" in outer
    ):
        return outer, "outer_json"

    if not isinstance(outer, dict):
        return None, "outer_not_object"

    # Priority 2: extract from message.content (DeepSeek may wrap prose + JSON)
    msg = outer.get("message")
    if isinstance(msg, dict):
        content = _message_content_to_text(msg.get("content"))
        if content:
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    return parsed, "message_content_direct"
            except Exception:
                pass
            parsed = _extract_first_json_object(content)
            if parsed is not None:
                return parsed, "message_content_first_object"

    return None, "no_json_object_found"


def _fallback_payload(status: str, problem: str) -> dict[str, Any]:
    return {
        "status": _normalize_status(status, default="UNKNOWN"),
        "problem": problem,
        "key_findings": ["Reasoning output parsing failed or upstream response was invalid."],
        "hypotheses": [],
        "recommended_next_steps": [f"Run `{REFRESH_HINT}` then retry /consult."],
        "risks": ["Diagnosis fidelity reduced due to invalid reasoning output."],
        "actions": [],
        "citations": [],
        "refresh_hint": REFRESH_HINT,
    }


def _extract_tool_call(payload: dict[str, Any] | None) -> tuple[str, dict[str, Any]] | None:
    if not isinstance(payload, dict):
        return None

    tool_name: Any = None
    tool_args: Any = None

    nested = payload.get("tool_call")
    if isinstance(nested, dict):
        tool_name = nested.get("name") or nested.get("tool")
        tool_args = nested.get("args")
    else:
        tool_name = payload.get("tool") or payload.get("name")
        tool_args = payload.get("args")

    normalized_name = str(tool_name or "").strip()
    if normalized_name != RAG_SEARCH_TOOL_NAME:
        return None
    if not isinstance(tool_args, dict):
        tool_args = {}
    return normalized_name, tool_args


def _tool_prompt_block() -> str:
    schema = {
        "tool": "rag_search",
        "args": {
            "query": "string (required, <=512 chars)",
            "k": "int (optional, 1..12)",
            "filter_type": "daily|strategy|incident (optional)",
            "since_date": "YYYY-MM-DD (optional)",
            "verbose": "string (optional, '0' or '1')",
        },
    }
    return (
        "If local Obsidian RAG evidence is needed before diagnosing, you may first output exactly one JSON "
        "tool call for the read-only `rag_search` tool instead of the final analysis object. "
        "The system will execute it and send you the result, then you must return the final analysis JSON only.\n"
        + json.dumps(schema, ensure_ascii=False)
    )


def _tool_followup_prompt(tool_name: str, tool_result: dict[str, Any]) -> str:
    return (
        f"Tool `{tool_name}` result (JSON):\n"
        f"{json.dumps(tool_result, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "Use this evidence to finalize your diagnosis. "
        "Return one valid JSON object that matches the original schema exactly, and cite relevant `pointer` values."
    )


def _normalize_payload(payload: dict[str, Any] | None, *, fallback_status: str, fallback_problem: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {}

    status = _normalize_status(payload.get("status"), default=fallback_status)
    problem = str(payload.get("problem") or fallback_problem).strip()
    if not problem:
        problem = fallback_problem

    findings = _coerce_str_list(payload.get("key_findings"))
    hypotheses = _coerce_str_list(payload.get("hypotheses"))
    next_steps = _coerce_str_list(payload.get("recommended_next_steps"))
    risks = _coerce_str_list(payload.get("risks"))
    citations = _coerce_str_list(payload.get("citations"))
    refresh_hint = str(payload.get("refresh_hint") or REFRESH_HINT).strip() or REFRESH_HINT

    if not findings:
        findings = ["No structured key findings were provided by the reasoning model."]
    refresh_step = f"Run `{refresh_hint}` to refresh SSOT snapshots before retry."
    if refresh_step not in next_steps:
        next_steps.append(refresh_step)

    return {
        "status": status,
        "problem": problem,
        "key_findings": findings,
        "hypotheses": hypotheses,
        "recommended_next_steps": next_steps,
        "risks": risks,
        "actions": [],
        "citations": citations,
        "refresh_hint": refresh_hint,
    }


def call_reasoning_specialist(
    prompt: str,
    system_prompt: Optional[str] = None,
    timeout: int = REASONING_TIMEOUT,
    tool_handler: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
) -> Optional[ReasoningAnalysis]:
    """Call Reasoning Specialist and normalize to strict JSON-only contract."""
    if not system_prompt:
        system_prompt = (
            "You are a Reasoning Specialist for HONGSTR, a professional quantitative trading system.\n"
            "Your task is to analyze system anomalies, data drift, or model performance degradation.\n"
            "You must output a single valid JSON object following this schema strictly:\n"
            "{\n"
            "  \"status\": \"OK|WARN|FAIL|UNKNOWN\",\n"
            "  \"problem\": \"...\",\n"
            "  \"key_findings\": [\"...\"],\n"
            "  \"hypotheses\": [\"...\"],\n"
            "  \"recommended_next_steps\": [\"...\"],\n"
            "  \"risks\": [\"...\"],\n"
            "  \"actions\": [],\n"
            "  \"citations\": [\"...\"],\n"
            "  \"refresh_hint\": \"bash scripts/refresh_state.sh\"\n"
            "}\n"
            "CRITICAL:\n"
            "- Output JSON only (no prose, no markdown, no code fences).\n"
            "- 'actions' MUST be an empty list [].\n"
            "- report_only behavior only; do not propose executable actions.\n"
        )
    if tool_handler:
        system_prompt = system_prompt.rstrip() + "\n" + _tool_prompt_block()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    def _request(current_messages: list[dict[str, str]]) -> str:
        body = {
            "model": REASONING_MODEL,
            "messages": current_messages,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
        }
        url = f"{OLLAMA_ENDPOINT}/api/chat"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "ignore")

    try:
        t0 = time.time()
        raw_response = _request(messages)
        extracted, source = _extract_reasoning_payload(raw_response)

        if tool_handler:
            tool_call = _extract_tool_call(extracted)
            if tool_call is not None:
                tool_name, tool_args = tool_call
                try:
                    tool_result = tool_handler(tool_name, tool_args)
                except Exception as exc:
                    tool_result = {
                        "status": "WARN",
                        "provider": "lancedb",
                        "db_path": "_local/lancedb/hongstr_obsidian.lancedb",
                        "chunks": [],
                        "warn": f"tool_handler_error: {type(exc).__name__}",
                    }
                if not isinstance(tool_result, dict):
                    tool_result = {
                        "status": "WARN",
                        "provider": "lancedb",
                        "db_path": "_local/lancedb/hongstr_obsidian.lancedb",
                        "chunks": [],
                        "warn": "tool_handler_returned_non_object",
                    }
                messages = list(messages) + [
                    {"role": "assistant", "content": json.dumps(extracted, ensure_ascii=False, separators=(",", ":"))},
                    {"role": "user", "content": _tool_followup_prompt(tool_name, tool_result)},
                ]
                raw_response = _request(messages)
                extracted, source = _extract_reasoning_payload(raw_response)

        if extracted is None:
            logger.warning("Reasoning JSON extraction failed (source=%s)", source)
            payload = _fallback_payload(
                "WARN",
                f"Reasoning JSON extraction failed ({source})",
            )
        else:
            payload = _normalize_payload(
                extracted,
                fallback_status="WARN",
                fallback_problem="Reasoning output missing required fields.",
            )

        analysis = ReasoningAnalysis(**payload)
        analysis.validate_actions_empty()  # Hard redline enforcement

        elapsed = int((time.time() - t0) * 1000)
        logger.info(
            "Reasoning Specialist SUCCESS in %sms (status=%s, source=%s)",
            elapsed,
            analysis.status,
            source,
        )
        return analysis

    except Exception as e:
        logger.error("Reasoning Specialist FAILED: %s: %s", type(e).__name__, e)
        payload = _fallback_payload(
            "UNKNOWN",
            f"Reasoning specialist call failed: {type(e).__name__}",
        )
        analysis = ReasoningAnalysis(**payload)
        analysis.validate_actions_empty()
        return analysis
