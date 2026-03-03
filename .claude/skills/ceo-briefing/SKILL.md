---
name: ceo-briefing
description: |
  Generate weekly "Monday Morning" CEO briefings summarizing all AI Employee activity.
  Covers social media performance, inbox volume, tasks completed, system health,
  approval pipeline status, and actionable recommendations. Output goes to /Briefings.
user_invocable: true
---

# CEO Briefing Generator

## What This Skill Does
- Scans all daily log files for the specified period
- Aggregates metrics: social posts, emails, tasks, errors, restarts
- Checks current vault state (inbox, pending, approvals)
- Determines system health (GREEN/YELLOW/RED)
- Generates a formatted briefing in `/Briefings`

## How to Use

### Generate Briefing (default: last 7 days)
```bash
uv run python watchers/ceo_briefing.py --vault-path AI_Employee_Vault
```

### Custom Period
```bash
uv run python watchers/ceo_briefing.py --vault-path AI_Employee_Vault --days 14
```

### As Claude Skill
When the user says "generate a CEO briefing" or "Monday morning report":
1. Run `uv run python watchers/ceo_briefing.py --vault-path AI_Employee_Vault`
2. Read the generated file from `/Briefings`
3. Present key highlights to the user

## Output Location
`AI_Employee_Vault/Briefings/YYYY-MM-DD_CEO_Briefing.md`

## Metrics Covered
- Total actions logged
- Social media posts by platform (LinkedIn, Twitter, Facebook, Instagram)
- Emails processed
- Tasks completed
- System errors and process restarts
- Approval pipeline (pending/approved/rejected)
- Current backlog (inbox + needs action)
