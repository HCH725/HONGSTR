"""
PR1 Tests: Research Loop Lock, Schema Invalid, and Timeout Fallbacks.
"""
import json
import os
import sys
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.loop import research_loop as rl


def _fake_snapshot_module(*, raise_exc: Exception | None = None, payload: dict | None = None):
    module = types.SimpleNamespace()

    def _collect_snapshot():
        if raise_exc is not None:
            raise raise_exc
        return payload or {}

    module._collect_snapshot = _collect_snapshot
    return module


class TestLockMechanism(unittest.TestCase):

    def _clear_lock(self):
        if rl.LOCK_PATH.exists():
            rl.LOCK_PATH.unlink()

    def setUp(self):
        self._clear_lock()

    def tearDown(self):
        self._clear_lock()

    def test_lock_acquire_fresh(self):
        """Lock not present → acquires successfully."""
        result = rl.acquire_lock()
        self.assertTrue(result)
        self.assertTrue(rl.LOCK_PATH.exists())
        lock = json.loads(rl.LOCK_PATH.read_text())
        self.assertEqual(lock["pid"], os.getpid())

    def test_lock_reentry_blocked_by_live_process(self):
        """Lock held by our own PID → treated as re-entry (blocked)."""
        # Write a fresh lock with our own PID
        rl.LOCK_PATH.write_text(json.dumps({
            "pid": os.getpid(),
            "start_ts": time.time(),
            "ttl_hours": 2,
        }))
        # Should block because pid is us and the process is alive
        result = rl.acquire_lock()
        self.assertFalse(result)

    def test_lock_stale_released(self):
        """Lock older than TTL → auto-released and loop proceeds."""
        # Write a lock from 3 hours ago
        old_ts = time.time() - (3 * 3600)
        rl.LOCK_PATH.write_text(json.dumps({
            "pid": 99999,  # Non-existent PID
            "start_ts": old_ts,
            "ttl_hours": 2,
        }))
        result = rl.acquire_lock()
        self.assertTrue(result)

    def test_lock_nonexistent_pid_released(self):
        """Lock with non-existent PID (even if fresh) → auto-released."""
        rl.LOCK_PATH.write_text(json.dumps({
            "pid": 99999,  # Non-existent PID
            "start_ts": time.time(),
            "ttl_hours": 2,
        }))
        result = rl.acquire_lock()
        self.assertTrue(result)


class TestStateWrite(unittest.TestCase):

    def test_warn_state_has_empty_actions(self):
        """WARN state must always have actions=[]."""
        rl.write_state("WARN", error="Test error")
        state = json.loads(rl.STATE_PATH.read_text())
        self.assertEqual(state["status"], "WARN")
        self.assertEqual(state["actions"], [])
        self.assertEqual(state["error"], "Test error")

    def test_ok_state_structure(self):
        """OK state has required fields."""
        rl.write_state("OK", exp_id="EXP_TEST", gate_passed=True, report_path="/tmp/report.md")
        state = json.loads(rl.STATE_PATH.read_text())
        self.assertEqual(state["status"], "OK")
        self.assertEqual(state["actions"], [])
        self.assertTrue(state["gate_passed"])
        self.assertEqual(state["last_exp"], "EXP_TEST")


class TestTimeoutFallback(unittest.TestCase):

    def test_ollama_timeout_exits_zero_and_writes_warn(self):
        """If any step raises (simulating Ollama timeout), loop writes WARN state and exits 0."""
        # Simulate a failure in _collect_snapshot (which would be an Ollama call)
        fake_mod = _fake_snapshot_module(raise_exc=TimeoutError("Simulated Ollama timeout"))
        with patch.dict(sys.modules, {"_local.telegram_cp.tg_cp_server": fake_mod}), \
             patch("research.loop.research_loop.acquire_lock", return_value=True), \
             patch("research.loop.research_loop.release_lock"), \
             patch("research.loop.research_loop.write_state") as mock_state, \
             patch("research.loop.research_loop.notify_telegram_warn") as mock_notify:
            with self.assertRaises(SystemExit) as ctx:
                rl.main()
            self.assertEqual(ctx.exception.code, 0)
            # Verify WARN was written
            warn_calls = [c for c in mock_state.call_args_list if c.args[0] == "WARN"]
            self.assertGreater(len(warn_calls), 0)
            mock_notify.assert_called_once()


class TestSchemaInvalidFallback(unittest.TestCase):

    def test_invalid_proposal_schema_exits_zero_and_writes_warn(self):
        """Invalid proposal fields → loop writes WARN state and exits 0."""
        bad_data = {
            "experiment_id": "EXP_BAD",
            # Missing required fields: hypothesis, strategy, symbol, etc.
        }
        fake_mod = _fake_snapshot_module(payload={})
        with patch.dict(sys.modules, {"_local.telegram_cp.tg_cp_server": fake_mod}), \
             patch("research.loop.research_loop.acquire_lock", return_value=True), \
             patch("research.loop.research_loop.release_lock"), \
             patch("research.loop.research_loop.write_state") as mock_state, \
             patch("research.loop.research_loop.notify_telegram_warn"), \
             patch("research.loop.research_loop.load_registry", return_value={"allowed_strategies": []}), \
             patch("research.loop.research_loop.ResearchProposal", side_effect=ValueError("Missing fields")):
            # Patch proposal creation to inject a bad dict
            with self.assertRaises(SystemExit) as ctx:
                rl.main()
            self.assertEqual(ctx.exception.code, 0)
            warn_calls = [c for c in mock_state.call_args_list if c.args[0] == "WARN"]
            self.assertGreater(len(warn_calls), 0)


if __name__ == "__main__":
    unittest.main()
