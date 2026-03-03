---
last_updated: 2026-02-27
platform: windows
---

# Scheduling Configuration

## Scheduled Tasks Overview

| Task | Frequency | Time | Skill Used | Status |
|------|-----------|------|------------|--------|
| Process Inbox | Daily | 08:00 AM | `process-inbox` | Ready |
| Gmail Check | Every 2 hours | Business hours | `gmail-watcher` | Ready |
| Dashboard Update | Every 4 hours | All day | `update-dashboard` | Ready |
| Approval Check | Hourly | Business hours | `approval-workflow` | Ready |
| LinkedIn Post | Weekly | Tue 10:00 AM | `linkedin-poster` | Ready |
| Weekly Planning | Weekly | Sun 8:00 PM | `create-plan` | Ready |

## Windows Task Scheduler Commands

### Setup All Tasks
```bash
# Daily inbox processing at 8 AM
schtasks /create /tn "AI_Employee_Daily_Inbox" /tr "claude -p 'Run the process-inbox skill'" /sc daily /st 08:00 /f

# Dashboard update every 4 hours
schtasks /create /tn "AI_Employee_Dashboard" /tr "claude -p 'Run the update-dashboard skill'" /sc hourly /mo 4 /f

# Approval check every hour
schtasks /create /tn "AI_Employee_Approvals" /tr "claude -p 'Run the approval-workflow skill'" /sc hourly /f

# LinkedIn post every Tuesday at 10 AM
schtasks /create /tn "AI_Employee_LinkedIn" /tr "claude -p 'Run the linkedin-poster skill'" /sc weekly /d TUE /st 10:00 /f

# Weekly planning every Sunday at 8 PM
schtasks /create /tn "AI_Employee_Planning" /tr "claude -p 'Run the create-plan skill'" /sc weekly /d SUN /st 20:00 /f
```

### Manage Tasks
```bash
# List all AI Employee tasks
schtasks /query /fo TABLE | findstr "AI_Employee"

# Run a task manually
schtasks /run /tn "AI_Employee_Daily_Inbox"

# Disable a task
schtasks /change /tn "AI_Employee_Daily_Inbox" /disable

# Enable a task
schtasks /change /tn "AI_Employee_Daily_Inbox" /enable

# Delete a task
schtasks /delete /tn "AI_Employee_Daily_Inbox" /f
```

## Continuous Watchers (Process Manager)

For always-on watchers, use PM2:

```bash
# Install PM2
npm install -g pm2

# Start watchers
pm2 start watchers/filesystem_watcher.py --interpreter python --name "file-watcher"
pm2 start watchers/gmail_watcher.py --interpreter python --name "gmail-watcher" -- --credentials ../credentials.json

# Save and auto-start on boot
pm2 save
pm2 startup
```

## Schedule Notes

- All times are in local timezone
- Scheduled Claude invocations use restricted tool permissions
- Failed tasks retry at the next scheduled interval
- Use `DRY_RUN=true` environment variable during testing
