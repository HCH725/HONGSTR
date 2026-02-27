# Worker Pack launchd Examples (macOS)

> Reference examples for running the two worker jobs continuously.

## 1) Research Worker plist

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.hongstr.worker.research</string>

    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>/Users/hong/Projects/HONGSTR/scripts/worker_run_research.sh</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/hong/Projects/HONGSTR</string>

    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/hong/Projects/HONGSTR/logs/worker_research.out.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/hong/Projects/HONGSTR/logs/worker_research.err.log</string>
  </dict>
</plist>
```

## 2) Backtests Worker plist

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.hongstr.worker.backtests</string>

    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>/Users/hong/Projects/HONGSTR/scripts/worker_run_backtests.sh</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/hong/Projects/HONGSTR</string>

    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/hong/Projects/HONGSTR/logs/worker_backtests.out.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/hong/Projects/HONGSTR/logs/worker_backtests.err.log</string>
  </dict>
</plist>
```

## 3) Load / Reload

```bash
mkdir -p ~/Library/LaunchAgents
cp /path/to/com.hongstr.worker.research.plist ~/Library/LaunchAgents/
cp /path/to/com.hongstr.worker.backtests.plist ~/Library/LaunchAgents/

launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.hongstr.worker.research.plist 2>/dev/null || true
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.hongstr.worker.backtests.plist 2>/dev/null || true

launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hongstr.worker.research.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hongstr.worker.backtests.plist

launchctl kickstart -k gui/$(id -u)/com.hongstr.worker.research
launchctl kickstart -k gui/$(id -u)/com.hongstr.worker.backtests
```

## 4) Verify

```bash
launchctl print gui/$(id -u)/com.hongstr.worker.research | head -n 40
launchctl print gui/$(id -u)/com.hongstr.worker.backtests | head -n 40

tail -n 60 /Users/hong/Projects/HONGSTR/logs/worker_research.out.log
tail -n 60 /Users/hong/Projects/HONGSTR/logs/worker_backtests.out.log
```
