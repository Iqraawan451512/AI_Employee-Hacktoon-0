---
type: architecture
version: "0.4"
tier: platinum
last_updated: 2026-03-03
---

# AI Employee Architecture - Platinum Tier

## System Overview

```
                    ┌──────────────────────────────────────┐
                    │       Human (CEO / Operator)          │
                    └────────┬──────────────┬───────────────┘
                             │              │
                    Obsidian Vault      Approve / Reject
                             │              │
    ┌────────────────────────▼──────────────▼──────────────────────┐
    │                    AI Employee Vault (Git-synced)             │
    │                                                              │
    │  ┌─────────────────────────────────────────────────────┐    │
    │  │  Needs_Action/                                       │    │
    │  │    ├── email/    (Cloud owns)                       │    │
    │  │    ├── social/   (Cloud owns)                       │    │
    │  │    ├── finance/  (Local owns)                       │    │
    │  │    └── general/  (Local owns)                       │    │
    │  ├─────────────────────────────────────────────────────┤    │
    │  │  Plans/<domain>/          Pending_Approval/<domain>/ │    │
    │  │  In_Progress/cloud/       In_Progress/local/         │    │
    │  │  Approved/    Rejected/   Done/                      │    │
    │  ├─────────────────────────────────────────────────────┤    │
    │  │  Updates/   Signals/   Logs/   Briefings/           │    │
    │  └─────────────────────────────────────────────────────┘    │
    └───────────────────┬────────────────────┬─────────────────────┘
                        │                    │
              ┌─────────▼─────────┐ ┌───────▼──────────┐
              │   CLOUD AGENT     │ │   LOCAL AGENT     │
              │   (Always-on VM)  │ │   (User machine)  │
              │                   │ │                    │
              │ ┌───────────────┐ │ │ ┌────────────────┐│
              │ │Cloud Orch.    │ │ │ │Local Orch.     ││
              │ │(draft only)   │ │ │ │(execute+approve)││
              │ ├───────────────┤ │ │ ├────────────────┤│
              │ │Gmail Watcher  │ │ │ │Playwright MCP  ││
              │ │Health Monitor │ │ │ │Dashboard Merger││
              │ │Vault Sync     │ │ │ │Vault Sync      ││
              │ │Odoo (draft)   │ │ │ │Odoo (post)     ││
              │ └───────────────┘ │ │ └────────────────┘│
              │                   │ │                    │
              │ ┌───────────────┐ │ │ ┌────────────────┐│
              │ │  Odoo 19      │ │ │ │ Ralph Wiggum   ││
              │ │  PostgreSQL 16│ │ │ │ Watchdog       ││
              │ │  Nginx (HTTPS)│ │ │ │ File Watcher   ││
              │ └───────────────┘ │ │ └────────────────┘│
              └───────────────────┘ └────────────────────┘
                        │                    │
                        └────── Git Sync ────┘
                             (30s interval)
```

## Core Components

### 1. Obsidian Vault (Data Layer)
The central file-based database, synced via Git between Cloud and Local.

| Folder | Purpose |
|--------|---------|
| `/Inbox` | Drop zone for new files (auto-detected by file watcher) |
| `/Needs_Action/<domain>` | Tasks awaiting processing, split by domain |
| `/In_Progress/cloud` | Tasks claimed by Cloud agent |
| `/In_Progress/local` | Tasks claimed by Local agent |
| `/Plans/<domain>` | Multi-step plans and drafts, split by domain |
| `/Pending_Approval/<domain>` | Items needing human sign-off, split by domain |
| `/Approved` | Human-approved items ready for execution |
| `/Rejected` | Items rejected by human |
| `/Done` | Completed tasks (archive) |
| `/Updates` | Cloud → Local status signals (merged into Dashboard) |
| `/Signals` | Cloud → Local event signals |
| `/Logs` | Daily JSON audit logs |
| `/Briefings` | CEO briefings and summaries |

### 2. Claude Code (Reasoning Engine)
The brain of the system. Uses 24 Agent Skills to process tasks.

**Bronze Skills**: process-inbox, update-dashboard, file-watcher
**Silver Skills**: gmail-watcher, whatsapp-watcher, linkedin-poster, create-plan, gmail-sender, approval-workflow, scheduler
**Gold Skills**: facebook-instagram-poster, twitter-poster, ceo-briefing, error-recovery, audit-logger, ralph-wiggum-loop, orchestrator
**Platinum Skills**: cloud-orchestrator, vault-sync, claim-manager, dashboard-merger, odoo-accounting, health-monitor
**MCP Skill**: browsing-with-playwright

### 3. Cloud Agent (Always-on VM)
Runs on an Ubuntu cloud VM. Draft-only — never sends or posts.

| Component | Script | systemd Unit |
|-----------|--------|-------------|
| Cloud Orchestrator | `cloud_orchestrator.py` | `ai-cloud-orchestrator.service` |
| Gmail Watcher | `gmail_watcher.py` | `ai-gmail-watcher.service` |
| Vault Sync | `vault_sync.py` | `ai-vault-sync.service` |
| Health Monitor | `health_monitor.py` | `ai-health-monitor.service` |
| Odoo ERP | Docker (odoo:19 + postgres:16 + nginx) | Docker Compose |

### 4. Local Agent (User Machine)
Runs on the user's local machine. Handles approvals and executes actions.

| Component | Script |
|-----------|--------|
| Local Orchestrator | `orchestrator.py --mode local` |
| Dashboard Merger | `dashboard_merger.py` (integrated in orchestrator) |
| Vault Sync | `vault_sync.py --agent local` |
| Playwright MCP | Browser automation for sends/posts |
| File Watcher | `filesystem_watcher.py` |
| Watchdog | `watchdog.py` |

### 5. Claim-by-Move (Coordination)
Prevents Cloud and Local from processing the same task.
```
try_claim(file, agent) → atomic rename to In_Progress/<agent>/
  ├── Success → process → release(dest)
  └── Failure → skip (other agent claimed it)
```

### 6. Odoo ERP (Accounting)
Odoo 19 + PostgreSQL 16 + Nginx running on Cloud VM via Docker.

| Operation | Cloud | Local |
|-----------|-------|-------|
| Create draft invoice | YES | YES |
| Post invoice | NO | YES |
| List invoices | YES | YES |

## Data Flow

### Cloud Agent Flow
```
External Source → Gmail Watcher detects → Needs_Action/email/
  → Cloud Orchestrator claims → Drafts reply → Pending_Approval/email/
  → Vault Sync pushes to Git
```

### Local Agent Flow
```
Git pull → Pending_Approval/<domain>/ appears in Obsidian
  → Human approves (moves to Approved/)
  → Local Orchestrator detects → Executes via Playwright MCP
  → Moves to Done/ → Vault Sync pushes
```

### Dashboard Updates
```
Cloud services write signals → Updates/*.md
  → Vault Sync delivers to Local
  → Dashboard Merger reads → Appends to Dashboard.md → Deletes signals
```

### Autonomous Loop (Ralph Wiggum)
```
Claude finishes task → Stop hook checks vault → Items remain? → Re-prompt Claude → Process next
```

## HITL (Human-in-the-Loop) Pattern
Every sensitive action follows this path:
1. Cloud creates a draft in `Plans/<domain>/`
2. Cloud creates approval request in `Pending_Approval/<domain>/`
3. Vault syncs to Local via Git
4. Human reviews in Obsidian
5. Human moves to `/Approved/` or `/Rejected/`
6. Local Orchestrator detects and executes
7. Result logged to `/Logs/` and moved to `/Done/`

## Error Recovery Strategy
```
Error occurs → Classify (transient/auth/data/system/sync)
  ├── Transient → Retry with exponential backoff (3 attempts)
  ├── Auth → Alert human immediately
  ├── Data → Log, skip, alert human
  ├── System → Alert human immediately
  └── Sync conflict → Auto-resolve per conflict rules

Process crash → Watchdog detects → Restart (max 10)
  └── Max restarts → Alert in /Needs_Action

VM outage → Health monitor stops → Local detects stale sync
  └── Local operates independently until VM recovers
```

## Technology Stack
| Component | Technology |
|-----------|-----------|
| Reasoning | Claude Code (Claude Opus 4.6) |
| Dashboard | Obsidian (local markdown vault) |
| Watchers | Python 3.13 with UV |
| Browser automation | Playwright via MCP server |
| Gmail | Google Gmail API (OAuth2) |
| ERP | Odoo 19 + PostgreSQL 16 |
| Reverse proxy | Nginx (HTTPS with Let's Encrypt) |
| Sync | Git (30s loop, pull --rebase) |
| Cloud services | systemd (Ubuntu) |
| Scheduling | Windows Task Scheduler (Local) / systemd timers (Cloud) |
| Process management | Watchdog (custom) |

## File Structure
```
Hacktoon-0-AI-employee/
├── AI_Employee_Vault/          # Obsidian vault (Git-synced data layer)
│   ├── Inbox/                  # File drop zone
│   ├── Needs_Action/           # Pending tasks
│   │   ├── email/              # Cloud-owned domain
│   │   ├── social/             # Cloud-owned domain
│   │   ├── finance/            # Local-owned domain
│   │   └── general/            # Local-owned domain
│   ├── In_Progress/
│   │   ├── cloud/              # Cloud agent claims
│   │   └── local/              # Local agent claims
│   ├── Plans/<domain>/         # Drafts split by domain
│   ├── Pending_Approval/<domain>/ # HITL queue by domain
│   ├── Approved/               # Ready for execution
│   ├── Rejected/               # Declined items
│   ├── Done/                   # Completed tasks (archive)
│   ├── Updates/                # Cloud → Local status signals
│   ├── Signals/                # Cloud → Local event signals
│   ├── Logs/                   # Daily JSON logs
│   ├── Briefings/              # CEO briefings
│   ├── Dashboard.md            # System status (Local-only writes)
│   ├── Architecture.md         # This document
│   ├── Company_Handbook.md     # Rules of engagement
│   ├── Approval_Policy.md      # HITL workflow details
│   ├── Sync_Config.md          # Git sync configuration
│   ├── Cloud_Status.md         # Cloud VM status
│   ├── Odoo_Config.md          # Odoo connection details
│   └── ...
├── watchers/                   # Python scripts
│   ├── orchestrator.py         # Local orchestrator (--mode local)
│   ├── cloud_orchestrator.py   # Cloud orchestrator (draft-only)
│   ├── claim_manager.py        # Claim-by-move protocol
│   ├── dashboard_merger.py     # Updates/ → Dashboard.md (Local-only)
│   ├── health_monitor.py       # Cloud health checks
│   ├── odoo_mcp.py             # Odoo JSON-RPC client
│   ├── gmail_watcher.py        # Gmail API watcher
│   ├── base_watcher.py         # Abstract base class
│   ├── filesystem_watcher.py   # File system watcher
│   ├── whatsapp_watcher.py     # WhatsApp Web watcher
│   ├── linkedin_poster.py      # LinkedIn poster
│   ├── twitter_poster.py       # Twitter/X poster
│   ├── facebook_instagram_poster.py  # FB & IG poster
│   ├── ceo_briefing.py         # CEO briefing generator
│   ├── audit_logger.py         # Centralized audit logger
│   ├── watchdog.py             # Process monitor
│   ├── retry_handler.py        # Retry logic
│   ├── ralph_wiggum_hook.py    # Autonomous loop
│   └── pyproject.toml          # UV project config
├── scripts/
│   ├── vault_sync.py           # Git sync script (30s loop)
│   ├── setup_vault_repo.sh     # One-time vault Git init
│   ├── cloud_setup.sh          # Cloud VM setup script
│   └── systemd/                # systemd service files
│       ├── ai-cloud-orchestrator.service
│       ├── ai-gmail-watcher.service
│       ├── ai-vault-sync.service
│       └── ai-health-monitor.service
├── odoo/
│   ├── docker-compose.yml      # Odoo 19 + PostgreSQL 16 + Nginx
│   ├── nginx/conf.d/odoo.conf  # Reverse proxy config
│   └── backup.sh               # Daily pg_dump backup
├── .claude/
│   └── skills/                 # 24 Agent Skills
└── .gitattributes              # Dashboard.md merge=ours
```

## Tier Progression
| Tier | Features |
|------|----------|
| Bronze | Vault structure, file watcher, inbox processing, dashboard |
| Silver | Gmail, WhatsApp, LinkedIn, planning, email sending, approvals, scheduling |
| Gold | Multi-platform social, error recovery, watchdog, CEO briefings, audit logging, autonomous loop, orchestrator |
| Platinum | Cloud/Local split, Git vault sync, claim-by-move, Odoo ERP, health monitoring, systemd services, 24 skills |
