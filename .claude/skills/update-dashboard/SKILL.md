---
name: update-dashboard
description: |
  Update the AI Employee Dashboard.md with current vault status. Counts files in each
  folder, lists recent activity from logs, and refreshes system status.
  Use after processing inbox items or when the user wants a status overview.
user_invocable: true
---

# Update Dashboard Skill

Refresh the `AI_Employee_Vault/Dashboard.md` with the current state of the vault.

## Workflow

1. **Count files** in each folder:
   - `Inbox/` — pending intake
   - `Needs_Action/` — awaiting processing
   - `In_Progress/` — currently being worked on
   - `Pending_Approval/` — awaiting human approval
   - `Done/` — completed items
2. **Read recent logs** from `Logs/` to populate the "Recent Activity" section
   - Show the last 10 actions from today's log file
3. **Calculate statistics**:
   - Files processed today / this week / this month
   - Actions completed
   - Approvals pending
4. **Update system status**:
   - File Watcher: check if the watcher process is running
   - Vault: always "Online" if we can read files
5. **Write** the updated `Dashboard.md` preserving the frontmatter format

## Dashboard Template

The Dashboard.md should follow this structure:

```markdown
---
last_updated: <current ISO timestamp>
version: 0.1
---

# AI Employee Dashboard

## System Status
| Component | Status | Last Check |
|-----------|--------|------------|
| File Watcher | <Online/Offline> | <timestamp> |
| Vault | Online | <timestamp> |

## Pending Actions
<list items from Needs_Action>

## Recent Activity
<last 10 log entries formatted as bullet points>

## Statistics
| Metric | Today | This Week | This Month |
|--------|-------|-----------|------------|
| Files Processed | X | X | X |
| Actions Completed | X | X | X |
| Approvals Pending | X | X | X |

## Folder Summary
| Folder | Count |
|--------|-------|
| Inbox | X |
| Needs_Action | X |
| In_Progress | X |
| Pending_Approval | X |
| Done | X |
```

## File Paths

- Dashboard: `AI_Employee_Vault/Dashboard.md`
- Logs: `AI_Employee_Vault/Logs/`
- All vault folders under `AI_Employee_Vault/`
