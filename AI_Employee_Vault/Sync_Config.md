---
type: config
last_updated: 2026-03-03
tier: platinum
---

# Vault Sync Configuration

## Git Remote
| Setting | Value |
|---------|-------|
| Remote URL | `<configure with setup_vault_repo.sh>` |
| Branch | `main` |
| Protocol | SSH (recommended) or HTTPS |

## Sync Intervals
| Agent | Interval | Script |
|-------|----------|--------|
| Cloud | 30s | `scripts/vault_sync.py --agent cloud` |
| Local | 30s | `scripts/vault_sync.py --agent local` |

## Conflict Resolution
| File | Rule | Rationale |
|------|------|-----------|
| `Dashboard.md` | Local wins (`merge=ours`) | Single-writer: only Local writes Dashboard |
| All other files | Remote wins (`--theirs`) | Cloud drafts take priority |
| Backup | `.conflict` suffix | Local version saved for manual review |

## Setup Instructions

### Cloud VM
```bash
# One-time setup
bash scripts/setup_vault_repo.sh git@github.com:user/vault.git

# Start sync service
sudo systemctl start ai-vault-sync
```

### Local Machine
```bash
# Clone vault repo
git clone git@github.com:user/vault.git AI_Employee_Vault

# Start sync (manual or scheduled)
uv run python scripts/vault_sync.py --vault AI_Employee_Vault --agent local
```

## .gitattributes
```
Dashboard.md merge=ours
```

## Monitoring
- Sync signals written to `Updates/SYNC_*.md`
- Health monitor checks sync freshness (warn >2min, error >5min)
- Dashboard merger appends sync events to Dashboard.md

## Related
- [[Cloud_Status]] - Cloud VM status
- [[Architecture]] - System design
- [[Dashboard]] - System dashboard
