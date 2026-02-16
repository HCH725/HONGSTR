import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "src"))

import pandas as pd
from hongstr.regime.baseline import RegimeLabeler
from hongstr.config import DATA_DIR
import hongstr.data.aggregate as agg

def demo_regime():
    print("--- Regime Labeling Demo ---")
    parquet_path = DATA_DIR / "BTCUSDT_1m.parquet"
    if not parquet_path.exists():
        print("No data.")
        return

    df_1m = pd.read_parquet(parquet_path)
    df_4h = agg.resample_klines(df_1m, "4h")
    
    labeler = RegimeLabeler()
    labels = labeler.label_regime(df_4h)
    
    df_4h['regime'] = labels
    
    print("\nRecent Regimes:")
    print(df_4h[['close', 'regime']].tail(10))
    
    print("\nRegime Distribution:")
    print(labels.value_counts(normalize=True))

if __name__ == "__main__":
    demo_regime()
