---
name: approval-workflow
description: |
  Human-in-the-loop approval workflow for sensitive actions. Creates approval request files
  in /Pending_Approval, monitors /Approved and /Rejected folders, and triggers or cancels
  actions based on human decisions. Use for payments, emails, social posts, and any action
  requiring human sign-off.
user_invocable: true
---

# Approval Workflow Skill (Human-in-the-Loop)

Manage the complete approval lifecycle for sensitive actions.

## Purpose

The AI Employee must **never take irreversible or sensitive actions** without human approval. This skill implements the file-based HITL pattern from the architecture document.

## How It Works

```
Claude detects sensitive action needed
        │
        ▼
Creates approval file in /Pending_Approval/
        │
        ▼
Human reviews in Obsidian
        │
        ├── Moves to /Approved/  → Action executes
        │
        ├── Moves to /Rejected/  → Action cancelled, logged
        │
        └── Edits then moves to /Approved/ → Modified action executes
```

## Workflow

### Step 1: Create Approval Request

When Claude determines an action needs approval (per Company Handbook thresholds), create a file:

```markdown
# AI_Employee_Vault/Pending_Approval/<ACTION>_<target>_<date>.md
---
type: approval_request
action: <email_send|payment|social_post|file_delete|external_api>
created: 2026-02-26T10:30:00Z
expires: 2026-02-27T10:30:00Z
status: pending
priority: <critical|high|medium|low>
source: <originating file or task>
---

# Approval Required: <Action Description>

## Details
<Full description of what will happen if approved>

## Parameters
| Field | Value |
|-------|-------|
| Action | <what will be done> |
| Target | <who/what is affected> |
| Amount | <if financial> |
| Risk | <low/medium/high> |

## Preview
<Show exactly what the user will see — email body, post text, payment details>

## To Approve
Move this file to the `/Approved` folder.

## To Reject
Move this file to the `/Rejected` folder.

## To Edit
Modify the content above, then move to `/Approved`.

## Expiry
This request expires on <expiry date>. If not acted upon, it will be auto-cancelled.
```

### Step 2: Check for Decisions

Periodically scan `/Approved/` and `/Rejected/` folders:

```bash
# Check for approved items
ls AI_Employee_Vault/Approved/

# Check for rejected items
ls AI_Employee_Vault/Rejected/
```

### Step 3: Execute Approved Actions

For each file found in `/Approved/`:
1. Read the approval file to get action parameters
2. Execute the action using the appropriate skill:
   - `email_send` → use `gmail-sender` skill
   - `social_post` → use `linkedin-poster` skill
   - `payment` → use `browsing-with-playwright` skill
3. Log the execution to `/Logs/`
4. Move the approval file to `/Done/`
5. Update Dashboard

### Step 4: Handle Rejected Actions

For each file found in `/Rejected/`:
1. Read the rejection
2. Log the rejection to `/Logs/`
3. Move the file to `/Done/` with status `rejected`
4. Update Dashboard

### Step 5: Handle Expired Requests

Check `/Pending_Approval/` for expired items:
1. Compare `expires` timestamp with current time
2. If expired, move to `/Done/` with status `expired`
3. Log the expiration

## Approval Thresholds (from Company Handbook)

| Action Category | Auto-Approve | Always Require Approval |
|----------------|-------------|------------------------|
| File processing | Read, categorize | Delete, send externally |
| Email replies | Draft only | Send to any recipient |
| Payments | None | All payments |
| Social media | Draft posts | Publish posts |
| File operations | Create, read | Delete, move outside vault |

## Approval File Naming Convention

Format: `<ACTION_TYPE>_<target>_<YYYY-MM-DD>.md`

Examples:
- `EMAIL_SEND_client_a_2026-02-26.md`
- `PAYMENT_vendor_xyz_2026-02-26.md`
- `LINKEDIN_POST_2026-02-26.md`
- `FILE_DELETE_old_reports_2026-02-26.md`

## Logging Format

### Approval Granted
```json
{
  "timestamp": "2026-02-26T11:00:00Z",
  "action_type": "approval_granted",
  "actor": "human",
  "target": "EMAIL_SEND_client_a_2026-02-26.md",
  "parameters": {
    "original_action": "email_send",
    "was_edited": false
  },
  "result": "approved"
}
```

### Approval Rejected
```json
{
  "timestamp": "2026-02-26T11:00:00Z",
  "action_type": "approval_rejected",
  "actor": "human",
  "target": "PAYMENT_vendor_xyz_2026-02-26.md",
  "parameters": {
    "original_action": "payment",
    "reason": "rejected by user"
  },
  "result": "rejected"
}
```

## Integration with Other Skills

This skill is called by:
- **`gmail-sender`**: Before sending any email
- **`linkedin-poster`**: Before publishing any post
- **`process-inbox`**: When processing items that need sensitive actions

## Security Notes

1. **Never bypass approval** — even if the action seems safe
2. **Expiry is mandatory** — approval requests must have a TTL
3. **Audit trail** — every approval/rejection is logged
4. **Modified approvals** — if user edits the file before approving, use the modified content
5. **No auto-escalation** — expired requests are cancelled, not auto-approved
