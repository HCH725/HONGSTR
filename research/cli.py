import argparse
import sys
import logging
from pathlib import Path

# Setup simple logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("research.cli")

def main():
    parser = argparse.ArgumentParser("HONGSTR Research SDK Feature Builder")
    parser.add_argument("--freq", required=True, help="e.g. 1h or 4h")
    parser.add_argument("--symbols", required=True, help="Space-separated symbols, e.g. 'BTCUSDT ETHUSDT'")
    parser.add_argument("--start", required=True, help="Start date, e.g. 2020-01-01")
    parser.add_argument("--end", required=True, help="End date, e.g. now")
    parser.add_argument("--factor_set", default="trend_mvp", help="FactorRegistry set name")
    parser.add_argument("--out_dir", default="reports/research", help="Output directory root")

    args = parser.parse_args()

    # Import modules late to ensure path is right
    try:
        from research.panel.spec import PanelSpec
        from research.panel.builder import build_panel
        from research.datasets.features import make_features, save_manifest, compute_hash
        import research.factors.trend_mvp  # Trigger registration
    except ImportError as e:
        logger.error(f"Failed to import research modules: {e}")
        sys.exit(1)

    sym_list = args.symbols.strip().split()
    
    spec = PanelSpec(
        freq=args.freq,
        symbols=sym_list,
        start=args.start,
        end=args.end
    )
    
    logger.info(f"Building panel for {sym_list} at {args.freq}...")
    panel = build_panel(spec)
    
    if panel is None or len(panel) == 0:
        logger.warning("Panel is empty or failed to build. Exiting successfully (stability-first).")
        sys.exit(0)
        
    logger.info(f"Panel built! Shape: {panel.shape}")
    
    # Ensure directories exist
    out_path = Path(args.out_dir)
    panels_dir = out_path / "panels"
    features_dir = out_path / "features"
    panels_dir.mkdir(parents=True, exist_ok=True)
    features_dir.mkdir(parents=True, exist_ok=True)
    
    panel_file = panels_dir / f"panel_{args.freq}.parquet"
    panel.to_parquet(panel_file)
    logger.info(f"Saved panel to {panel_file}")
    
    logger.info(f"Generating features using factor set '{args.factor_set}'...")
    features = make_features(panel, set_name=args.factor_set, strict_index=True)
    
    feat_file = features_dir / f"features_{args.freq}.parquet"
    features.to_parquet(feat_file)
    logger.info(f"Saved features to {feat_file}")
    
    f_hash = compute_hash(feat_file)
    save_manifest(str(features_dir), args.freq, len(features), f_hash)
    logger.info("Saved manifest.json. Done.")

if __name__ == "__main__":
    main()
