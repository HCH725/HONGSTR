# Skills Storage & Deploy SOP

Policy SSOT: `docs/skills/global_red_lines.md`

This SOP defines how skill docs are stored, deployed to local cache, and verified before agent tasks.

## 1) Canonical SSOT Paths

The canonical repository sources for skills/rules are:

- `docs/skills/global_red_lines.md`
- `docs/skills/hongstr-dev/*`
- `docs/skills/hongstr-research/*`

Only these repo paths are SSOT for skill guidance. Runtime cache copies are deployment outputs, not source-of-truth.

## 2) Deploy To Cache (Installer)

Use installer only:

```bash
bash scripts/install_hongstr_skills.sh --force
```

Destination selection rule:

1. Use `_local/skills_cache/` when that path exists and is gitignored.
2. Otherwise fallback to `~/.hongstr/skills`.

Supported installer options:

- `--dry-run`
- `--dest <path>`
- `--force`

## 3) Preflight Before Task Execution

### Requested command block (verbatim)

```bash
cd /Users/hong/Projects/HONGSTR
git checkout main
git pull –ff-only
bash scripts/install_hongstr_skills.sh –force
./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py
git diff –name-only origin/main…HEAD | rg ‘^src/hongstr/’ && exit 1 || true
rg -n ‘subprocess|os.system|Popen’ _local/telegram_cp/tg_cp_server.py && exit 1 || true
git status –porcelain | rg ‘^.. data/’ && exit 1 || true
echo “OK: preflight pass (skills+smoke+red-lines)”
```

### Shell-safe equivalent (same semantics)

```bash
cd /Users/hong/Projects/HONGSTR
git checkout main
git pull --ff-only
bash scripts/install_hongstr_skills.sh --force
./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py
git diff --name-only origin/main...HEAD | rg '^src/hongstr/' && exit 1 || true
rg -n 'subprocess|os\.system|Popen' _local/telegram_cp/tg_cp_server.py && exit 1 || true
git status --porcelain | rg '^.. data/' && exit 1 || true
echo "OK: preflight pass (skills+smoke+red-lines)"
```

## 4) Prohibitions

- Do not manually edit cache content under `_local/skills_cache/` or `~/.hongstr/skills`.
- Cache must only be overwritten via `scripts/install_hongstr_skills.sh`.
- Do not treat cache files as SSOT.

## 5) Runtime Skills vs Docs Skills

Docs skills are guidance artifacts. They inject standards, red lines, and workflow instructions into agent behavior, and their SSOT lives under `docs/skills/*` in the repository.

Runtime skills are code behavior implemented by services and scripts (for example tg_cp and research loop). Runtime behavior changes require normal GitHub PR flow and become active only after deployment/restart (such as launchd restart for affected services).
