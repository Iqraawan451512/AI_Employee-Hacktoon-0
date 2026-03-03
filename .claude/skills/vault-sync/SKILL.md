---
name: vault-sync
description: |
  Git-based vault synchronization between Cloud and Local agents.
  Runs a 30-second loop: add → commit → pull --rebase → push.
  Dashboard.md always keeps Local's version (single-writer rule).
user_invocable: true
---

# Vault Sync (Platinum Tier)

## What This Skill Does
- Synchronizes AI_Employee_Vault between Cloud and Local via Git
- Runs in a 30-second loop: `git add -A → commit → pull --rebase → push`
- Conflict resolution: Dashboard.md always keeps Local's version
- Other conflicts: keep remote (Cloud), save local as `.conflict`
- Writes sync signals to `Updates/`

## How to Use

### Single Sync
```bash
uv run python scripts/vault_sync.py --vault AI_Employee_Vault --once --agent local
```

### Continuous Loop
```bash
uv run python scripts/vault_sync.py --vault AI_Employee_Vault --interval 30 --agent cloud
```

### As systemd Service (Cloud)
```bash
sudo systemctl start ai-vault-sync
```

## Setup
1. Run `scripts/setup_vault_repo.sh <REMOTE_URL>` to initialize vault as Git repo
2. Configure `.gitattributes` with `Dashboard.md merge=ours`
3. Start sync loop on both Cloud and Local

## Conflict Resolution
| File | Strategy | Rationale |
|------|----------|-----------|
| Dashboard.md | Local wins (ours) | Single-writer rule |
| All other files | Remote wins (theirs) | Cloud drafts take priority |
| Conflict backup | Saved as `.conflict` | Manual review possible |

## Architecture
```
vault_sync.py (30s loop)
  ├── git add -A
  ├── git commit -m "vault-sync [agent] timestamp"
  ├── git pull --rebase --autostash
  │   └── On conflict → resolve per rules above
  └── git push
```
