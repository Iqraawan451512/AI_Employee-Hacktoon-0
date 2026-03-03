---
name: scheduler
description: |
  Set up and manage scheduled tasks using Windows Task Scheduler (or cron on Linux/Mac).
  Schedule recurring AI Employee operations like daily inbox processing, LinkedIn posting,
  Gmail checking, and weekly briefings. Use to automate the AI Employee on a time basis.
user_invocable: true
---

# Scheduler Skill

Set up automated scheduling for the AI Employee using Windows Task Scheduler.

## Purpose

The AI Employee needs to run tasks on a schedule without manual intervention:
- **Continuous**: Watchers run 24/7 (managed by process managers)
- **Scheduled**: Recurring tasks at specific times (managed by this skill)
- **Project-Based**: One-time tasks triggered manually

## Available Scheduled Tasks

### 1. Daily Inbox Processing (Morning)
Process all pending items at the start of the workday.

```bash
# Windows Task Scheduler (via PowerShell)
schtasks /create /tn "AI_Employee_Daily_Inbox" /tr "claude -p 'Run the process-inbox skill. Process all items in AI_Employee_Vault/Needs_Action/ following Company_Handbook.md rules. Update the dashboard when done.' --allowedTools 'Read,Write,Edit,Glob,Grep,Bash'" /sc daily /st 08:00

# Linux/Mac (cron)
# 0 8 * * * claude -p 'Run the process-inbox skill...' --allowedTools 'Read,Write,Edit,Glob,Grep,Bash'
```

### 2. Gmail Check (Every 2 Hours)
Poll Gmail for new important emails during business hours.

```bash
# Start the Gmail watcher as a background service
schtasks /create /tn "AI_Employee_Gmail_Watcher" /tr "cd /d E:\Hacktoon-0-AI-employee\watchers && uv run python gmail_watcher.py --vault-path ..\AI_Employee_Vault" /sc onstart

# Or schedule periodic checks
schtasks /create /tn "AI_Employee_Gmail_Check" /tr "claude -p 'Run the gmail-watcher skill. Check for new emails and create action items.' --allowedTools 'Read,Write,Edit,Glob,Grep,Bash'" /sc hourly /mo 2
```

### 3. LinkedIn Post (Weekly)
Generate and schedule a business post every Tuesday at 10 AM.

```bash
schtasks /create /tn "AI_Employee_LinkedIn_Post" /tr "claude -p 'Run the linkedin-poster skill. Generate a business post based on recent achievements in AI_Employee_Vault/Done/ and Business_Goals.md. Create draft and approval file.' --allowedTools 'Read,Write,Edit,Glob,Grep,Bash'" /sc weekly /d TUE /st 10:00
```

### 4. Dashboard Update (Every 4 Hours)
Keep the dashboard fresh during business hours.

```bash
schtasks /create /tn "AI_Employee_Dashboard_Update" /tr "claude -p 'Run the update-dashboard skill.' --allowedTools 'Read,Write,Edit,Glob,Grep,Bash'" /sc hourly /mo 4
```

### 5. Approval Check (Hourly)
Check for approved/rejected items and process them.

```bash
schtasks /create /tn "AI_Employee_Approval_Check" /tr "claude -p 'Run the approval-workflow skill. Check /Approved and /Rejected folders. Execute approved actions and log rejected ones.' --allowedTools 'Read,Write,Edit,Glob,Grep,Bash'" /sc hourly
```

### 6. Weekly Planning Session (Sunday Evening)
Generate plans for the upcoming week.

```bash
schtasks /create /tn "AI_Employee_Weekly_Planning" /tr "claude -p 'Run the create-plan skill. Review all items in /Needs_Action and /In_Progress. Create plans for the upcoming week. Review Business_Goals.md for alignment.' --allowedTools 'Read,Write,Edit,Glob,Grep,Bash'" /sc weekly /d SUN /st 20:00
```

## Managing Scheduled Tasks

### List All AI Employee Tasks
```bash
schtasks /query /fo TABLE | grep "AI_Employee"
```

### View Task Details
```bash
schtasks /query /tn "AI_Employee_Daily_Inbox" /v /fo LIST
```

### Delete a Task
```bash
schtasks /delete /tn "AI_Employee_Daily_Inbox" /f
```

### Disable a Task (Temporarily)
```bash
schtasks /change /tn "AI_Employee_Daily_Inbox" /disable
```

### Enable a Task
```bash
schtasks /change /tn "AI_Employee_Daily_Inbox" /enable
```

### Run a Task Manually
```bash
schtasks /run /tn "AI_Employee_Daily_Inbox"
```

## Recommended Schedule (Full Setup)

| Task | Frequency | Time | Description |
|------|-----------|------|-------------|
| Inbox Processing | Daily | 08:00 | Process all /Needs_Action items |
| Gmail Check | Every 2 hours | Business hours | Poll for new emails |
| Dashboard Update | Every 4 hours | All day | Refresh dashboard stats |
| Approval Check | Hourly | Business hours | Process /Approved and /Rejected |
| LinkedIn Post | Weekly | Tue 10:00 | Generate business post draft |
| Weekly Planning | Weekly | Sun 20:00 | Create plans for upcoming week |
| File Watcher | On startup | - | Continuous Inbox monitoring |

## Quick Setup Script

Run this to set up all scheduled tasks at once:

```bash
# Create a setup script
cat > setup_scheduler.bat << 'BATCH'
@echo off
echo Setting up AI Employee scheduled tasks...

schtasks /create /tn "AI_Employee_Daily_Inbox" /tr "claude -p \"Run the process-inbox skill\"" /sc daily /st 08:00 /f
schtasks /create /tn "AI_Employee_Dashboard_Update" /tr "claude -p \"Run the update-dashboard skill\"" /sc hourly /mo 4 /f
schtasks /create /tn "AI_Employee_Approval_Check" /tr "claude -p \"Run the approval-workflow skill\"" /sc hourly /f
schtasks /create /tn "AI_Employee_LinkedIn_Post" /tr "claude -p \"Run the linkedin-poster skill\"" /sc weekly /d TUE /st 10:00 /f
schtasks /create /tn "AI_Employee_Weekly_Planning" /tr "claude -p \"Run the create-plan skill\"" /sc weekly /d SUN /st 20:00 /f

echo Done! Use 'schtasks /query /fo TABLE' to verify.
BATCH
```

## Notes

- All scheduled Claude invocations use `--allowedTools` to restrict permissions
- Tasks log output to the vault's `/Logs/` directory
- Failed tasks are retried at the next scheduled interval
- Use `DRY_RUN=true` environment variable during testing
- On Windows, scheduled tasks run under the current user account
