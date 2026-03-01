import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from _local.telegram_cp.reasoning_client import call_reasoning_specialist
from _local.telegram_cp.schemas_reasoning import ReasoningAnalysis


FIX_DIR = Path("/Users/hong/Projects/HONGSTR/_local/telegram_cp/tests/fixtures/reasoning_client")


def _mock_response_from_payload(payload: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    return mock_resp


def _fixture_payload(name: str) -> dict:
    return json.loads((FIX_DIR / name).read_text(encoding="utf-8"))


class TestReasoningClient(unittest.TestCase):

    def test_call_success_outer_json_priority(self):
        payload = {
            "status": "OK",
            "problem": "Outer payload should be used",
            "key_findings": ["outer"],
            "hypotheses": [],
            "recommended_next_steps": [],
            "risks": [],
            "actions": ["ILLEGAL_ACTION"],
            "citations": [],
            "message": {
                "content": "{\"status\":\"FAIL\",\"problem\":\"inner\"}"
            },
        }
        with patch("urllib.request.urlopen", return_value=_mock_response_from_payload(payload)):
            analysis = call_reasoning_specialist("Analyze this")
        self.assertIsInstance(analysis, ReasoningAnalysis)
        self.assertEqual(analysis.status, "OK")
        self.assertEqual(analysis.problem, "Outer payload should be used")
        self.assertEqual(analysis.actions, [])

    def test_call_success_with_prose_fixture(self):
        with patch("urllib.request.urlopen", return_value=_mock_response_from_payload(_fixture_payload("prose.json"))):
            analysis = call_reasoning_specialist("Analyze this")
        self.assertIsInstance(analysis, ReasoningAnalysis)
        self.assertEqual(analysis.status, "OK")
        self.assertEqual(analysis.problem, "prose-first")
        self.assertEqual(analysis.actions, [])

    def test_call_success_with_codefence_fixture(self):
        with patch("urllib.request.urlopen", return_value=_mock_response_from_payload(_fixture_payload("codefence.json"))):
            analysis = call_reasoning_specialist("Analyze this")
        self.assertIsInstance(analysis, ReasoningAnalysis)
        self.assertEqual(analysis.status, "WARN")
        self.assertEqual(analysis.problem, "codefence")
        self.assertEqual(analysis.actions, [])

    def test_call_success_with_double_json_uses_first_object(self):
        with patch("urllib.request.urlopen", return_value=_mock_response_from_payload(_fixture_payload("double_json.json"))):
            analysis = call_reasoning_specialist("Analyze this")
        self.assertIsInstance(analysis, ReasoningAnalysis)
        self.assertEqual(analysis.status, "OK")
        self.assertEqual(analysis.problem, "first-object")
        self.assertEqual(analysis.actions, [])

    def test_call_bad_json_falls_back_warn(self):
        with patch("urllib.request.urlopen", return_value=_mock_response_from_payload(_fixture_payload("bad_json.json"))):
            analysis = call_reasoning_specialist("Analyze this")
        self.assertIsInstance(analysis, ReasoningAnalysis)
        self.assertEqual(analysis.status, "WARN")
        self.assertEqual(analysis.actions, [])
        self.assertIn("refresh_state.sh", analysis.refresh_hint)
        self.assertTrue(any("refresh_state.sh" in x for x in analysis.recommended_next_steps))

    def test_call_timeout_falls_back_unknown(self):
        with patch("urllib.request.urlopen", side_effect=TimeoutError("Timeout")):
            analysis = call_reasoning_specialist("Analyze this", timeout=1)
        self.assertIsInstance(analysis, ReasoningAnalysis)
        self.assertEqual(analysis.status, "UNKNOWN")
        self.assertEqual(analysis.actions, [])
        self.assertIn("refresh_state.sh", analysis.refresh_hint)

    def test_call_schema_normalization(self):
        payload = {
            "message": {
                "content": json.dumps(
                    {
                        "problem": "missing fields",
                        "key_findings": [],
                        "hypotheses": [],
                        "recommended_next_steps": [],
                        "risks": [],
                        "citations": [],
                    }
                )
            }
        }
        with patch("urllib.request.urlopen", return_value=_mock_response_from_payload(payload)):
            analysis = call_reasoning_specialist("Analyze this")
        self.assertIsInstance(analysis, ReasoningAnalysis)
        self.assertEqual(analysis.status, "WARN")
        self.assertEqual(analysis.problem, "missing fields")
        self.assertEqual(analysis.actions, [])
        self.assertTrue(any("refresh_state.sh" in x for x in analysis.recommended_next_steps))

    def test_call_tool_roundtrip_then_final_json(self):
        first_payload = {
            "message": {
                "content": json.dumps(
                    {
                        "tool": "rag_search",
                        "args": {"query": "freshness status", "k": 5},
                    }
                )
            }
        }
        second_payload = {
            "message": {
                "content": json.dumps(
                    {
                        "status": "OK",
                        "problem": "freshness diagnosis",
                        "key_findings": ["Freshness is degraded"],
                        "hypotheses": ["ETL lag"],
                        "recommended_next_steps": ["Review the daily freshness report."],
                        "risks": [],
                        "actions": [],
                        "citations": ["Daily/2026/03/2026-03-02.md#Summary"],
                    }
                )
            }
        }
        seen = {}

        def fake_tool_handler(tool_name, args):
            seen["tool_name"] = tool_name
            seen["args"] = args
            return {
                "status": "OK",
                "provider": "lancedb",
                "db_path": "_local/lancedb/hongstr_obsidian.lancedb",
                "chunks": [
                    {
                        "pointer": "Daily/2026/03/2026-03-02.md#Summary",
                        "text": "Freshness status is WARN.",
                        "score": 3.0,
                        "metadata": {"type": "daily"},
                    }
                ],
            }

        with patch(
            "urllib.request.urlopen",
            side_effect=[
                _mock_response_from_payload(first_payload),
                _mock_response_from_payload(second_payload),
            ],
        ):
            analysis = call_reasoning_specialist("Analyze this", tool_handler=fake_tool_handler)

        self.assertIsInstance(analysis, ReasoningAnalysis)
        self.assertEqual(seen["tool_name"], "rag_search")
        self.assertEqual(seen["args"], {"query": "freshness status", "k": 5})
        self.assertEqual(analysis.status, "OK")
        self.assertIn("Daily/2026/03/2026-03-02.md#Summary", analysis.citations)


if __name__ == "__main__":
    unittest.main()
