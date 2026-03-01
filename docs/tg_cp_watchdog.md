# tg_cp watchdog (L2 self-heal milestone)

## Goal
Ensure tg_cp is restarted automatically when it is not healthy. Health is determined by SSOT heartbeat freshness (services_heartbeat.json).

## Design
- External watchdog via launchd: com.hongstr.tg_cp_watchdog
- tg_cp remains no-exec/read-only; watchdog owns restart using launchctl kickstart -k
- No auto-merge; changes tracked via PR

## Install (local)
- Copy _local/launchd/com.hongstr.tg_cp_watchdog.plist to ~/Library/LaunchAgents/
- launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hongstr.tg_cp_watchdog.plist
- launchctl enable gui/$(id -u)/com.hongstr.tg_cp_watchdog

## Tune
- TG_CP_MAX_AGE_SEC environment variable (default 600)
- StartInterval (default 120s)
