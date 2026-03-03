---
name: cloud-orchestrator
description: |
  Cloud-side orchestrator that runs on the cloud VM. Owns email and social
  domains only. Draft-only: creates drafts in Plans/<domain>/ and approval
  requests in Pending_Approval/<domain>/. Never sends or posts directly.
  Uses claim-by-move and triggers vault sync after each cycle.
user_invocable: true
---

# Cloud Orchestrator (Platinum Tier)

## What This Skill Does
- Runs on the cloud VM as an always-on service
- Owns only `email` and `social` domains
- **Draft-only**: never sends emails or publishes posts
- Claims tasks via claim-by-move protocol
- Creates drafts in `Plans/<domain>/`
- Creates approval requests in `Pending_Approval/<domain>/`
- Writes status signals to `Updates/`
- Triggers vault Git sync after each cycle

## How to Use

### Run Once
```bash
uv run python watchers/cloud_orchestrator.py --vault-path AI_Employee_Vault --once
```

### Continuous Loop (Production)
```bash
uv run python watchers/cloud_orchestrator.py --vault-path AI_Employee_Vault --interval 60
```

### As systemd Service
```bash
sudo systemctl start ai-cloud-orchestrator
sudo systemctl status ai-cloud-orchestrator
journalctl -u ai-cloud-orchestrator -f
```

## Work-Zone Ownership
| Domain | Cloud (this) | Local |
|--------|-------------|-------|
| Email triage + draft | YES | — |
| Social post drafts | YES | — |
| Odoo draft invoices | YES | — |
| Approvals | — | YES |
| Send email | — | YES |
| Publish posts | — | YES |
| Payments | — | YES |

## Architecture
```
Cloud Orchestrator
  ├── Scan Needs_Action/email/ → Claim → Draft reply → Pending_Approval/email/
  ├── Scan Needs_Action/social/ → Claim → Draft post → Pending_Approval/social/
  ├── Write signal to Updates/
  └── Trigger vault_sync.py --once --agent cloud
```

## Safety Rules
- NEVER executes sends, posts, or payments
- All outputs are drafts requiring Local agent approval
- Uses claim-by-move to avoid conflicts with Local agent
- All actions logged to `/Logs/`
