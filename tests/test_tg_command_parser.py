from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_tg_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts" / "tg_text_dashboard.py"
    spec = importlib.util.spec_from_file_location("tg_text_dashboard_script", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_runs_with_explicit_n():
    module = _load_tg_module()
    parsed = module.parse_command("/runs 20")
    assert parsed == {"name": "runs", "n": 20}


def test_parse_runs_default_and_cap():
    module = _load_tg_module()
    assert module.parse_command("/runs") == {"name": "runs", "n": module.DEFAULT_RUNS_N}
    assert module.parse_command("/runs 999") == {"name": "runs", "n": module.MAX_RUNS_N}


def test_parse_command_with_bot_suffix():
    module = _load_tg_module()
    assert module.parse_command("/health@hongstr_bot") == {"name": "health"}
