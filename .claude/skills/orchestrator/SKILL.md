---
name: orchestrator
description: |
  Cross-domain orchestrator that coordinates actions across email, social media,
  file system, and approvals. Scans vault folders, classifies tasks by domain,
  routes to appropriate handlers, and checks scheduled tasks. The central brain
  of the AI Employee system.
user_invocable: true
---

# Cross-Domain Orchestrator

## What This Skill Does
- Scans `/Inbox`, `/Needs_Action`, and `/Approved` for pending work
- Classifies each item by domain (email, social, finance, etc.)
- Routes items to the correct handler script
- Checks for scheduled tasks (e.g., Monday CEO briefing)
- Logs all routing decisions to `/Logs`

## How to Use

### Run Once
```bash
uv run python watchers/orchestrator.py --vault-path AI_Employee_Vault --once
```

### Continuous Loop
```bash
uv run python watchers/orchestrator.py --vault-path AI_Employee_Vault --interval 60
```

## Domain Routing
| Keywords | Domain | Handler |
|----------|--------|---------|
| email, gmail | gmail | gmail_watcher.py |
| linkedin | linkedin | linkedin_poster.py |
| twitter, tweet | twitter | twitter_poster.py |
| facebook | facebook | facebook_instagram_poster.py |
| instagram | instagram | facebook_instagram_poster.py |
| whatsapp | whatsapp | whatsapp_watcher.py |
| invoice, payment, budget | finance | Manual review |
| briefing, report, summary | briefing | ceo_briefing.py |

## Scheduled Tasks
- Monday 7-9 AM: Auto-generate CEO Briefing if not already created

## Architecture
```
Orchestrator
  ├── Scan /Inbox → Classify → Move to /Needs_Action
  ├── Scan /Approved → Route to poster script
  ├── Scan /Needs_Action → Classify for Claude processing
  └── Check scheduled tasks → Run scripts if due
```
