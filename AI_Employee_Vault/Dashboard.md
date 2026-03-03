---
last_updated: 2026-03-03T00:00:00Z
version: 0.4
tier: platinum
---

# AI Employee Dashboard

## System Status
| Component | Location | Status | Last Check |
|-----------|----------|--------|------------|
| File Watcher | Local | Ready | 2026-03-03 |
| Gmail Watcher | Cloud | Authenticated | 2026-03-03 |
| WhatsApp Watcher | Local | Needs QR Login | 2026-02-27 |
| LinkedIn Poster | Local | Ready | 2026-02-27 |
| Twitter Poster | Local | Ready | 2026-02-27 |
| Facebook/Instagram Poster | Local | Ready | 2026-02-27 |
| Watchdog | Local | Ready | 2026-02-27 |
| Orchestrator (Local) | Local | Ready | 2026-03-03 |
| Cloud Orchestrator | Cloud | Pending Setup | 2026-03-03 |
| Vault Sync | Cloud+Local | Pending Setup | 2026-03-03 |
| Health Monitor | Cloud | Pending Setup | 2026-03-03 |
| Dashboard Merger | Local | Ready | 2026-03-03 |
| Claim Manager | Cloud+Local | Ready | 2026-03-03 |
| Ralph Wiggum Loop | Local | Ready | 2026-02-27 |
| Approval Workflow | Local | Active | 2026-02-27 |
| Scheduler | Local | Ready | 2026-02-27 |
| Audit Logger | Cloud+Local | Active | 2026-02-27 |
| CEO Briefing | Local | Ready | 2026-02-27 |
| Odoo ERP | Cloud | Pending Setup | 2026-03-03 |
| Vault | Online | Online | 2026-03-03 |

## Cloud Status
| Service | Status | Detail |
|---------|--------|--------|
| Cloud Orchestrator | Pending | Awaiting cloud VM deployment |
| Gmail Watcher (Cloud) | Pending | Awaiting cloud VM deployment |
| Vault Sync | Pending | Awaiting Git remote setup |
| Health Monitor | Pending | Awaiting cloud VM deployment |
| Odoo | Pending | Awaiting Docker setup |

_Cloud health signals merge here automatically via dashboard_merger.py_

## System Health: [GREEN] Excellent

## Pending Actions
- 1 LinkedIn post draft in `/Pending_Approval/`

## Pending Approvals
| File | Action | Created | Expires |
|------|--------|---------|---------|
| LINKEDIN_POST_20260226_005604.md | LinkedIn Post | 2026-02-26 | 2026-02-27 |

## Recent Activity
- [2026-03-03 00:00] Platinum tier upgrade complete (v0.4)
- [2026-03-03 00:00] Cloud/Local orchestrator split implemented
- [2026-03-03 00:00] Vault sync, claim manager, dashboard merger created
- [2026-03-03 00:00] Odoo integration added (docker-compose + JSON-RPC client)
- [2026-03-03 00:00] Health monitor and systemd services created
- [2026-03-03 00:00] 6 new skills added (24 total)
- [2026-02-27 12:00] Gold tier upgrade complete (v0.3)
- [2026-02-27 02:45] Gmail watcher authenticated and started polling
- [2026-02-27 00:19] LinkedIn post published (dry run)
- [2026-02-26 00:56] LinkedIn post draft created
- [2026-02-25 01:25] Processed `test_task.md` from Inbox -> Done

## Statistics
| Metric | Today | This Week | This Month |
|--------|-------|-----------|------------|
| Files Processed | 0 | 4 | 4 |
| Emails Detected | 0 | 0 | 0 |
| Social Posts | 0 | 1 | 1 |
| Plans Created | 0 | 1 | 1 |
| Actions Completed | 0 | 4 | 4 |
| Approvals Pending | 1 | 1 | 1 |
| Errors | 0 | 0 | 0 |
| Process Restarts | 0 | 0 | 0 |

## Folder Summary
| Folder | Count |
|--------|-------|
| Inbox | 0 |
| Needs_Action | 0 |
| In_Progress/cloud | 0 |
| In_Progress/local | 0 |
| Plans | 1 |
| Pending_Approval | 1 |
| Approved | 0 |
| Rejected | 0 |
| Done | 7 |
| Briefings | 1 |
| Updates | 0 |
| Signals | 0 |

## Platinum Tier Features
- Cloud/Local agent split with domain ownership
- Git-synced vault (30s interval, auto-merge)
- Claim-by-move protocol for conflict-free task processing
- Dashboard merger (Local-only writes Dashboard.md)
- Cloud orchestrator (draft-only, email + social domains)
- Odoo ERP integration (draft invoices + posting)
- Health monitoring with systemd services
- 24 Agent Skills (18 Gold + 6 Platinum)

## Quick Links
- [[Company_Handbook]] - Rules of engagement
- [[Business_Goals]] - Revenue targets and content strategy
- [[Approval_Policy]] - HITL approval workflow
- [[Watchers_Status]] - Watcher configuration
- [[Scheduling_Config]] - Scheduled tasks
- [[Bank_Transactions]] - Financial tracking
- [[Error_Recovery_Playbook]] - Error handling procedures
- [[Sync_Config]] - Vault Git sync configuration
- [[Cloud_Status]] - Cloud VM status
- [[Odoo_Config]] - Odoo ERP connection details
- [[Architecture]] - System architecture
