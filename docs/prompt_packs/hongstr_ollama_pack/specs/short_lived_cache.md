# Short-lived Cache Spec (v1)

Purpose: reduce repeated expensive reads/formatting when generating reports.

Design:
- Cache key: (block_name, ssot_ts_utc, model_overlay_id, pack_version)
- TTL: 30-180 seconds
- Storage: data/state/_tg_cp/cache/*.json (runtime) or /tmp (non-repo)
- Must be safe to delete; cache is best-effort only.

Rules:
- Cache must not contain secrets.
- If cache read fails, regenerate normally.
