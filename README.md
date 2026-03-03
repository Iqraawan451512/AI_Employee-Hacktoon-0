# AI Employee - Personal Autonomous FTE

> A fully autonomous AI employee that works 168 hours/week, handling email, social media, invoicing, and business operations with human-in-the-loop safety.

Built for [Hacktoon 0: Building Autonomous FTEs in 2026](Personal%20AI%20Employee%20Hackathon%200_%20Building%20Autonomous%20FTEs%20in%202026.md).

## Current Tier: Platinum (v0.4)

| Tier | Features |
|------|----------|
| Bronze | Vault structure, file watcher, inbox processing, dashboard |
| Silver | Gmail, WhatsApp, LinkedIn, planning, email sending, approvals, scheduling |
| Gold | Multi-platform social, error recovery, watchdog, CEO briefings, audit logging, autonomous loop |
| **Platinum** | **Cloud/Local split, Git vault sync, claim-by-move, Odoo ERP, health monitoring, 24 skills** |

## Architecture

The system is split into two agents communicating via a **Git-synced Obsidian vault**:

```
┌─────────────────────┐         Git Sync (30s)        ┌─────────────────────┐
│    CLOUD AGENT      │◄──────────────────────────────►│    LOCAL AGENT      │
│   (Always-on VM)    │                                │   (User machine)    │
│                     │                                │                     │
│  Cloud Orchestrator │    ┌──────────────────────┐    │  Local Orchestrator │
│  Gmail Watcher      │    │  AI Employee Vault    │    │  Playwright MCP     │
│  Health Monitor     │    │  (Obsidian + Git)     │    │  Dashboard Merger   │
│  Odoo (draft only)  │    │                       │    │  Odoo (post)        │
│  Vault Sync         │    │  Needs_Action/<domain> │    │  Vault Sync         │
│                     │    │  Pending_Approval/     │    │  Watchdog           │
│  Odoo 19 + Postgres │    │  Plans/ Updates/ Logs/ │    │  File Watcher       │
│  Nginx (HTTPS)      │    └──────────────────────┘    │  Ralph Wiggum Loop  │
└─────────────────────┘                                └─────────────────────┘
      DRAFT ONLY                                          APPROVE + EXECUTE
```

### Work-Zone Ownership

| Domain | Cloud (draft-only) | Local (execute) |
|--------|-------------------|-----------------|
| Email triage + draft replies | Yes | - |
| Social post drafts | Yes | - |
| Odoo draft invoices | Yes | - |
| Approvals | - | Yes |
| Send email / publish posts | - | Yes |
| Payments / banking | - | Yes |
| WhatsApp | - | Yes |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Reasoning engine | Claude Code (Claude Opus 4.6) |
| Dashboard | Obsidian (markdown vault) |
| Watchers & scripts | Python 3.13 + UV |
| Browser automation | Playwright MCP Server |
| Email | Gmail API (OAuth2) |
| ERP | Odoo 19 + PostgreSQL 16 |
| Reverse proxy | Nginx (HTTPS / Let's Encrypt) |
| Sync | Git (30s pull --rebase loop) |
| Cloud services | systemd (Ubuntu) |

## Project Structure

```
├── AI_Employee_Vault/           # Obsidian vault (Git-synced data layer)
│   ├── Needs_Action/{email,social,finance,general}/
│   ├── Plans/{email,social,finance,general}/
│   ├── Pending_Approval/{email,social,finance,general}/
│   ├── In_Progress/{cloud,local}/
│   ├── Approved/ Rejected/ Done/
│   ├── Updates/ Signals/ Logs/ Briefings/
│   ├── Dashboard.md             # System status (Local-only writes)
│   ├── Architecture.md          # Full system design
│   ├── Company_Handbook.md      # Rules of engagement
│   └── ...config docs
├── watchers/                    # Python automation (17 scripts)
│   ├── orchestrator.py          # Local orchestrator (--mode local)
│   ├── cloud_orchestrator.py    # Cloud orchestrator (draft-only)
│   ├── claim_manager.py         # Claim-by-move protocol
│   ├── dashboard_merger.py      # Updates/ → Dashboard.md
│   ├── gmail_watcher.py         # Gmail API poller
│   ├── health_monitor.py        # Cloud health checks
│   ├── odoo_mcp.py              # Odoo JSON-RPC client
│   ├── linkedin_poster.py       # LinkedIn publisher
│   ├── twitter_poster.py        # Twitter/X publisher
│   ├── facebook_instagram_poster.py
│   ├── whatsapp_watcher.py      # WhatsApp monitor
│   ├── ceo_briefing.py          # Weekly CEO briefing
│   ├── audit_logger.py          # Structured JSON logging
│   ├── watchdog.py              # Process monitor
│   └── ...
├── scripts/
│   ├── vault_sync.py            # Git sync (30s loop)
│   ├── cloud_setup.sh           # Ubuntu VM provisioning
│   ├── setup_vault_repo.sh      # Vault Git initialization
│   └── systemd/                 # 4 service files
├── odoo/
│   ├── docker-compose.yml       # Odoo 19 + PostgreSQL 16 + Nginx
│   ├── nginx/conf.d/odoo.conf   # Reverse proxy
│   └── backup.sh                # Daily pg_dump
└── .claude/skills/              # 24 Agent Skills
```

## 24 Agent Skills

| Tier | Skills |
|------|--------|
| Bronze | process-inbox, update-dashboard, file-watcher |
| Silver | gmail-watcher, whatsapp-watcher, linkedin-poster, create-plan, gmail-sender, approval-workflow, scheduler |
| Gold | facebook-instagram-poster, twitter-poster, ceo-briefing, error-recovery, audit-logger, ralph-wiggum-loop, orchestrator, browsing-with-playwright |
| Platinum | cloud-orchestrator, vault-sync, claim-manager, dashboard-merger, odoo-accounting, health-monitor |

## Key Protocols

### Claim-by-Move
Prevents both agents from processing the same task. An agent atomically moves a file to `In_Progress/<agent>/` before processing. If the file is gone, another agent claimed it first.

### Single-Writer Dashboard
Only the Local agent writes `Dashboard.md`. Cloud writes signals to `Updates/`, which the dashboard merger appends to Dashboard.md. Git merges always keep Local's version (`merge=ours`).

### Human-in-the-Loop
Every sensitive action (send email, publish post, make payment, post invoice) requires human approval. Cloud creates drafts in `Pending_Approval/<domain>/`, human reviews in Obsidian, moves to `Approved/`, Local executes.

## Quick Start

### Local Agent
```bash
cd watchers && uv sync
uv run python orchestrator.py --vault-path ../AI_Employee_Vault --mode local
```

### Cloud VM Setup
```bash
sudo bash scripts/cloud_setup.sh <REPO_URL> <VAULT_REMOTE_URL>
# Then: copy credentials, start systemd services
```

### Odoo
```bash
cd odoo && docker compose up -d
```

## Demo Flow

```
1. Local is OFFLINE
2. Email arrives → Cloud gmail_watcher detects
3. Cloud orchestrator claims → drafts reply → Pending_Approval/email/
4. Cloud syncs vault via Git push
5. Local comes ONLINE → Git pull → sees approval in Obsidian
6. Human approves (moves to Approved/)
7. Local orchestrator detects → sends via Playwright → Done/
```

## License

Private project - Hacktoon 0 submission.
