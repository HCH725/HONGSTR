# tg_cp watchdog (L2 self-heal milestone)

## Goal

Ensure tg_cp is restarted automatically when it is not healthy. Health is determined by SSOT heartbeat freshness (services_heartbeat.json).

## Design

- External watchdog via launchd: com.hongstr.tg_cp_watchdog
- tg_cp remains no-exec/read-only; watchdog owns restart using launchctl kickstart -k
- No auto-merge; changes tracked via PR

## Deployment notes (macOS launchd)

- StandardOutPath/StandardErrorPath should be absolute paths (avoid $HOME; launchd may not expand it)
- Ensure the log directory exists before bootstrap (e.g., /Users/<user>/Library/Logs/hongstr)
- Repo root should be an absolute path (e.g., /Users/<user>/Projects/HONGSTR) or a clearly documented configurable location
- Python invocation should prefer repo venv (./.venv/bin/python) and fall back to python3 when venv is unavailable

## Install (local)

- Copy _local/launchd/com.hongstr.tg_cp_watchdog.plist to ~/Library/LaunchAgents/
- launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hongstr.tg_cp_watchdog.plist
- launchctl enable gui/$(id -u)/com.hongstr.tg_cp_watchdog

## Tune

- TG_CP_MAX_AGE_SEC environment variable (default 600)
- StartInterval (default 120s)
