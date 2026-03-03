---
name: dashboard-merger
description: |
  Local-only script that reads signal files from Updates/, appends activity
  entries to Dashboard.md "Recent Activity" section, and deletes processed
  signals. Ensures Dashboard.md is only written by the Local agent.
user_invocable: true
---

# Dashboard Merger (Platinum Tier)

## What This Skill Does
- Reads signal files from `Updates/` (written by Cloud agent and services)
- Parses each signal's frontmatter (type, agent, action, domain)
- Appends formatted entries to Dashboard.md "Recent Activity" section
- Deletes processed signal files to prevent re-processing
- Updates `last_updated` timestamp in Dashboard.md frontmatter

## How to Use

### Run Once
```bash
uv run python watchers/dashboard_merger.py --vault-path AI_Employee_Vault --once
```

### Continuous Loop
```bash
uv run python watchers/dashboard_merger.py --vault-path AI_Employee_Vault --interval 30
```

### Integrated with Local Orchestrator
The dashboard merger is automatically called by `orchestrator.py --mode local`
after each scan cycle.

## Signal File Format
Signal files in `Updates/` follow this pattern:
```markdown
---
type: cloud_update | health_status | sync_status | odoo_update
agent: cloud | local
domain: email | social | finance
action: drafted | health_ok | synced
timestamp: ISO-8601
---
```

## Signal Types
| Prefix | Source | Content |
|--------|--------|---------|
| CLOUD_* | Cloud orchestrator | Task drafting activity |
| HEALTH_* | Health monitor | Service health checks |
| SYNC_* | Vault sync | Git sync status |
| ODOO_* | Odoo client | Invoice actions |

## Architecture
```
Updates/
├── CLOUD_EMAIL_20260303_120000.md  → Dashboard merger reads
├── HEALTH_20260303_120100.md       → Parses frontmatter
└── SYNC_20260303_120030.md         → Appends to Recent Activity
                                    → Deletes signal files
```
