import json
import logging
import os
import time
import urllib.request
from typing import Optional
from pathlib import Path

from .schemas_reasoning import ReasoningAnalysis

# Environment overrides
OLLAMA_ENDPOINT = os.getenv("HONGSTR_LLM_ENDPOINT", "http://127.0.0.1:11434")
REASONING_MODEL = os.getenv("HONGSTR_REASONING_MODEL", "deepseek-r1:7b")
REASONING_TIMEOUT = int(os.getenv("HONGSTR_REASONING_TIMEOUT", "120"))
DEBUG_JSON = os.getenv("HONGSTR_DEBUG_JSON", "0") == "1"

logger = logging.getLogger("reasoning_client")

def call_reasoning_specialist(prompt: str, system_prompt: Optional[str] = None, timeout: int = REASONING_TIMEOUT) -> Optional[ReasoningAnalysis]:
    """
    Call the Reasoning Specialist (DeepSeek-R1) and return a validated ReasoningAnalysis object.
    Enforces strict JSON output.
    """
    if not system_prompt:
        system_prompt = (
            "You are a Reasoning Specialist for HONGSTR, a professional quantitative trading system.\n"
            "Your task is to analyze system anomalies, data drift, or model performance degradation.\n"
            "You must output a single valid JSON object following this schema strictly:\n"
            "{\n"
            "  \"status\": \"OK|WARN|FAIL\",\n"
            "  \"problem\": \"...\",\n"
            "  \"key_findings\": [\"...\"],\n"
            "  \"hypotheses\": [\"...\"],\n"
            "  \"recommended_next_steps\": [\"...\"],\n"
            "  \"risks\": [\"...\"],\n"
            "  \"actions\": [],\n"
            "  \"citations\": [\"...\"]\n"
            "}\n"
            "CRITICAL: 'actions' MUST be an empty list []. Do not propose any executable actions."
        )

    body = {
        "model": REASONING_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "format": "json", # Support JSON mode if available, though deepseek-r1 might ignore it
        "options": {"temperature": 0.2},
    }

    url = f"{OLLAMA_ENDPOINT}/api/chat"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

    try:
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_response = resp.read().decode("utf-8", "ignore")
            j = json.loads(raw_response)
            
            # 1. Outer JSON extraction
            content = j.get("message", {}).get("content", "").strip()
            
            analysis_dict = None
            
            # 2. Primary success: direct json.loads
            try:
                analysis_dict = json.loads(content)
            except json.JSONDecodeError:
                # 3. Fallback: regex extraction (non-greedy, first complete block)
                import re
                # Look for the first balanced { ... } block
                # Simple non-greedy regex + validation loop
                match = re.search(r'(\{.*\})', content, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    # Try to find the shortest prefix that is valid JSON to avoid greediness
                    # or just take the whole chunk if it starts and ends with {}
                    try:
                        analysis_dict = json.loads(json_str)
                    except json.JSONDecodeError:
                        # If that failed, try the non-greedy search
                        match_ng = re.search(r'(\{.*?\})', content, re.DOTALL)
                        if match_ng:
                            try:
                                analysis_dict = json.loads(match_ng.group(1))
                            except json.JSONDecodeError:
                                pass

            # 4. Schema Normalization & Final Fallback
            if analysis_dict is None or not isinstance(analysis_dict, dict):
                logger.warning(f"Specialist parsing failed for content: {content[:100]}...")
                analysis_dict = {
                    "status": "WARN",
                    "problem": "Specialist output parsing failed or invalid schema",
                    "key_findings": ["Raw content was unparsable or not a JSON object"],
                    "hypotheses": [],
                    "recommended_next_steps": ["Check LLM connectivity or prompt template"],
                    "risks": ["Visibility deficit"],
                    "actions": [],
                    "citations": []
                }
            
            # Ensure mandatory fields for ReasoninigAnalysis
            if "status" not in analysis_dict:
                analysis_dict["status"] = "WARN"
            if "actions" not in analysis_dict:
                analysis_dict["actions"] = []

            analysis = ReasoningAnalysis(**analysis_dict)
            analysis.validate_actions_empty() # Hard redline enforcement: actions MUST be []
            
            elapsed = int((time.time() - t0) * 1000)
            logger.info(f"Reasoning Specialist SUCCESS in {elapsed}ms (status={analysis.status})")
            return analysis

    except Exception as e:
        logger.error(f"Reasoning Specialist FAILED: {type(e).__name__}: {e}")
        return None
