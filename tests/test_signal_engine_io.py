import pytest
import shutil
import asyncio
from pathlib import Path
from hongstr.signal.engine import SignalEngine
from hongstr.signal.types import EngineConfig

def test_engine_io(tmp_path):
    async def _run_test():
        input_dir = tmp_path / "input" / "2024-01-01"
        input_dir.mkdir(parents=True)
        
        output_dir = tmp_path / "output"
        state_dir = tmp_path / "state"
        
        # Create valid kline jsonl
        kline_file = input_dir / "kline_BTCUSDT_1m.jsonl"
        with open(kline_file, "w") as f:
            # Write 30 lines (minutes)
            for i in range(30):
                ts = 1704103200000 + (i * 60000) # 2024-01-01 10:00
                line = f'{{"stream":"btcusdt@kline_1m","data":{{"k":{{"t":{ts},"s":"BTCUSDT","i":"1m","o":"100","h":"100","l":"100","c":"{100+(i%2)}","v":"10","x":true}}}}}}'
                f.write(line + "\n")
                
        config = EngineConfig(
            symbols=["BTCUSDT"],
            timeframes=["1m", "5m"],
            input_root=str(tmp_path / "input"),
            output_root=str(output_dir),
            state_root=str(state_dir),
            mode="tail_jsonl",
            max_bars=100
        )
        
        engine = SignalEngine(config)
        
        await engine._init_storage()
        
        with open(kline_file, "r") as f:
            for line in f:
                engine._process_jsonl_line(line)
                await engine.on_new_1m_bar_async("BTCUSDT")
                
        if engine.signal_file:
            await engine.signal_file.close()
            
        signal_file = state_dir / "signal_events.jsonl"
        # Since we use append mode, file should exist if we initialized storage
        assert signal_file.exists()
        
    asyncio.run(_run_test())
