import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

# Import dashboard (need to mock streamlit potentially or just import the function if possible)
# Since dashboard.py is a script with top-level code, importing it might run it.
# We will cheat by reading the file and extracting the function code or
# better: refactoring dashboard.py is hard now.
# However, we can use runpy or exec to test the logic if we extract it,
# OR we can just mock streamlit config and import.
# But dashboard.py has `st.set_page_config` at top level which errors if run twice or without context.
# Strategy: We will mock `streamlit` module before importing.

sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit"].columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
sys.modules["streamlit"].sidebar.selectbox.return_value = "No Runs Found"

# Now we can import
import scripts.dashboard as dashboard


class TestDashboardMode(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.test_dir) / "data"
        self.data_dir.mkdir(parents=True)
        (self.data_dir / "state").mkdir()
        (self.data_dir / "realtime" / "state").mkdir(parents=True)

        # Patch PROJECT_ROOT in dashboard module
        self.original_root = dashboard.PROJECT_ROOT
        dashboard.PROJECT_ROOT = Path(self.test_dir)

        # Clear env vars
        if "HONGSTR_EXEC_MODE" in os.environ:
            del os.environ["HONGSTR_EXEC_MODE"]
        if "EXECUTION_MODE" in os.environ:
            del os.environ["EXECUTION_MODE"]

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        dashboard.PROJECT_ROOT = self.original_root

        # Restore env
        if "HONGSTR_EXEC_MODE" in os.environ:
            del os.environ["HONGSTR_EXEC_MODE"]

    def test_default_mode(self):
        # No env, no files
        self.assertEqual(dashboard.detect_execution_mode(), "LOCAL")

    def test_env_var_precedence(self):
        # Env var > Files
        os.environ["HONGSTR_EXEC_MODE"] = "PAPER"
        # Create a state file that would trigger LOCAL_SERVICES
        (self.data_dir / "state" / "heartbeat.json").touch()

        self.assertEqual(dashboard.detect_execution_mode(), "PAPER")
        del os.environ["HONGSTR_EXEC_MODE"]

    def test_state_file_detection(self):
        # 1. data/state/*.json
        f = self.data_dir / "state" / "service.json"
        f.touch()
        self.assertEqual(dashboard.detect_execution_mode(), "LOCAL_SERVICES")
        f.unlink()

        # 2. logs/*heartbeat*.json (need to mock logs dir relative to root)
        logs_dir = Path(self.test_dir) / "logs"
        logs_dir.mkdir()
        f = logs_dir / "my_heartbeat.json"
        f.touch()
        self.assertEqual(dashboard.detect_execution_mode(), "LOCAL_SERVICES")


if __name__ == "__main__":
    unittest.main()
