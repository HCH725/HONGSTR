import json
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("aiofiles")

from hongstr.bridge.signal_to_execution import SignalExecutionBridge


@pytest.fixture
def mock_executor():
    executor = MagicMock()
    executor.execute_signal = MagicMock()
    return executor


@pytest.mark.asyncio
async def test_bridge_process_signal_line(mock_executor):
    bridge = SignalExecutionBridge(executor=mock_executor)

    # Valid signal line
    line = json.dumps(
        {
            "ts": "2024-01-01T12:00:00",
            "symbol": "BTCUSDT",
            "portfolio_id": "HONG",
            "strategy_id": "test_strat",
            "direction": "LONG",
            "timeframe": "1h",
            "regime": "TREND",
            "confidence": 0.95,
        }
    )

    await bridge.process_signal_line(line)

    # Check executor called
    mock_executor.execute_signal.assert_called_once()
    args = mock_executor.execute_signal.call_args[0]
    evt = args[0]
    assert evt.symbol == "BTCUSDT"
    assert evt.direction == "LONG"
    assert evt.strategy_id == "test_strat"


@pytest.mark.asyncio
async def test_bridge_idempotency(mock_executor):
    bridge = SignalExecutionBridge(executor=mock_executor)

    line = json.dumps(
        {
            "ts": "2024-01-01T12:00:00",
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "strategy_id": "strat1",
        }
    )

    # First call
    await bridge.process_signal_line(line)
    mock_executor.execute_signal.assert_called_once()

    # Second call (duplicate)
    await bridge.process_signal_line(line)
    mock_executor.execute_signal.assert_called_once()  # Count should not increase


@pytest.mark.asyncio
async def test_bridge_offline_mode(mock_executor):
    with patch("hongstr.bridge.signal_to_execution.OFFLINE_MODE", True):
        bridge = SignalExecutionBridge(executor=mock_executor)
        line = json.dumps({"ts": "...", "symbol": "ETHUSDT", "direction": "SHORT"})

        await bridge.process_signal_line(line)
        mock_executor.execute_signal.assert_not_called()
