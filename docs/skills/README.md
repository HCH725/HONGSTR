# Skills Docs Packs

Skill packs in this directory are documentation-only guidance for agents.

## Install to local cache

Use the installer script to copy `docs/skills/*` into a local skills cache:

```bash
bash scripts/install_hongstr_skills.sh --dry-run
bash scripts/install_hongstr_skills.sh
bash scripts/install_hongstr_skills.sh --dest ~/.hongstr/skills --force
```

### Options

- `--dry-run`: print source/destination and file list without copying.
- `--dest <path>`: destination directory override.
- `--force`: allow copying into a non-empty destination.

### Default destination

If `git` reports `_local/skills_cache/` is ignored, installer uses `_local/skills_cache/`.
Otherwise it falls back to `~/.hongstr/skills`.

## Included packs

- `global_red_lines.md`
- `hongstr-dev/`
- `hongstr-research/`
- `skill_specs/`
- `skills_storage_and_deploy.md`
