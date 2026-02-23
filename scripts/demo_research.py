import sys
import pandas as pd
from pathlib import Path

def main():
    out_dir = Path("reports/research")
    panels_dir = out_dir / "panels"
    features_dir = out_dir / "features"

    panel_1h = panels_dir / "panel_1h.parquet"
    feat_1h = features_dir / "features_1h.parquet"

    if not panel_1h.exists() or not feat_1h.exists():
        print("Required artifacts not found. Run scripts/build_features.sh first.")
        sys.exit(1)

    panel = pd.read_parquet(panel_1h)
    feat = pd.read_parquet(feat_1h)

    index_match = panel.index.equals(feat.index)
    rowcount_match = len(panel) == len(feat)

    summary = f"""# Research SDK End-to-End Demo

## Metadata
- **Panel Path**: `{panel_1h}`
- **Features Path**: `{feat_1h}`
- **Total Rows**: {len(panel):,}
- **Symbols**: {list(panel.index.get_level_values(1).unique())}
- **Date Range**: {panel.index.get_level_values(0).min()} to {panel.index.get_level_values(0).max()}

## Validation
- **Row Count matches**: {"PASS" if rowcount_match else "FAIL"}
- **Index equals**: {"PASS" if index_match else "FAIL"}

## Sample (First 5 Rows of Features)
```text
{feat.head(5).to_string()}
```
"""

    demo_md = out_dir / "demo_summary.md"
    with open(demo_md, "w") as f:
        f.write(summary)

    print(f"Generated {demo_md}")

    if not index_match or not rowcount_match:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
