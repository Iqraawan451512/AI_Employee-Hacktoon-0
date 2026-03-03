---
name: process-inbox
description: |
  Process pending action items in the AI Employee vault. Reads files from /Needs_Action,
  analyzes their content, takes appropriate action, and moves completed items to /Done.
  Use when you need to process the inbox or handle pending tasks.
user_invocable: true
---

# Process Inbox Skill

Scan the `/Needs_Action` folder in the AI Employee Vault and process each pending item.

## Workflow

1. **Read** the Company_Handbook.md for current rules and thresholds
2. **List** all files in `AI_Employee_Vault/Needs_Action/`
3. **For each `.md` file** (metadata files):
   a. Read the frontmatter to understand the item type, priority, and status
   b. If status is already "processed", skip it
   c. Based on the `type` field:
      - `file_drop`: Review the associated file, categorize it, summarize its contents
      - `email`: Draft a response or flag for human review
      - `task`: Create a plan in `/Plans/`
   d. Update the `.md` file's status to "processed"
   e. Move both the `.md` file and any associated files to `/Done/`
4. **Log** all actions taken to `AI_Employee_Vault/Logs/YYYY-MM-DD.json`
5. **Run** the `update-dashboard` skill to refresh the Dashboard

## Processing Rules

- Follow all rules defined in `Company_Handbook.md`
- Never delete files — always move them
- For items requiring approval, move to `/Pending_Approval/` instead of `/Done/`
- Log every action in JSON format

## File Paths

- Vault: `AI_Employee_Vault/`
- Input: `AI_Employee_Vault/Needs_Action/`
- Output: `AI_Employee_Vault/Done/`
- Approval: `AI_Employee_Vault/Pending_Approval/`
- Logs: `AI_Employee_Vault/Logs/`

## Example Log Entry

```json
{
  "timestamp": "2026-02-25T10:30:00Z",
  "action_type": "file_processed",
  "actor": "claude_code",
  "target": "FILE_20260225_report.md",
  "parameters": {"category": "document", "action": "categorized_and_archived"},
  "result": "success"
}
```
