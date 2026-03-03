---
last_updated: 2026-03-03
review_frequency: monthly
tier: platinum
---

# Approval Policy

## Human-in-the-Loop (HITL) Rules

This document defines when the AI Employee can act autonomously and when it must request human approval.

## Approval Flow

```
AI detects action needed
    │
    ├── Auto-Approved? → Execute immediately, log to /Logs/
    │
    └── Requires Approval?
            │
            ├── Create file in /Pending_Approval/
            │
            ├── Human moves to /Approved/ → Execute, move to /Done/
            │
            └── Human moves to /Rejected/ → Cancel, move to /Done/
```

## Action Categories

### Auto-Approved (No Human Needed)
| Action | Scope | Limit |
|--------|-------|-------|
| Read files | Any vault file | Unlimited |
| Categorize files | Inbox → Needs_Action | Unlimited |
| Create plans | Write Plan.md | Unlimited |
| Draft emails | Save draft only | Unlimited |
| Draft social posts | Save draft only | Unlimited |
| Update Dashboard | Dashboard.md | Unlimited |
| Log actions | /Logs/ | Unlimited |
| Generate reports | /Briefings/ | Unlimited |

### Requires Human Approval
| Action | Condition | Expiry |
|--------|-----------|--------|
| Send email | All recipients | 24 hours |
| Publish LinkedIn post | All posts | 24 hours |
| Send WhatsApp reply | All messages | 12 hours |
| Delete files | Any file | 24 hours |
| Make payment | Any amount | 24 hours |
| External API calls | Non-read operations | 12 hours |
| Move files outside vault | Any file | 24 hours |

### Always Blocked (Never Auto-Approve)
- Payments to new recipients
- Bulk email sends (> 5 recipients)
- Deleting vault structure folders
- Modifying Company_Handbook.md without approval
- Sharing credentials or tokens
- Actions on behalf of unknown contacts

## Approval File Format

All approval requests must follow this format:

```markdown
---
type: approval_request
action: <action_type>
created: <ISO timestamp>
expires: <ISO timestamp>
status: pending
priority: <critical|high|medium|low>
---

# Approval Required: <Description>

## What Will Happen
<Clear explanation of the action>

## Details
<Specifics - recipient, amount, content, etc.>

## To Approve
Move this file to /Approved folder.

## To Reject
Move this file to /Rejected folder.
```

## Naming Convention

`<ACTION_TYPE>_<target>_<YYYY-MM-DD>.md`

Examples:
- `EMAIL_SEND_john_doe_2026-02-27.md`
- `LINKEDIN_POST_2026-02-27.md`
- `PAYMENT_vendor_abc_2026-02-27.md`

## Expiry Rules

- Expired requests are automatically cancelled (not auto-approved)
- Expired files are moved to `/Done/` with status `expired`
- Default expiry: 24 hours
- Critical items: 12 hours
- Payments: 24 hours (fresh approval required each time)

## Cloud-Drafted Approvals (Platinum)

When the Cloud agent creates approval requests, they include `agent: cloud` in frontmatter:

```markdown
---
type: approval_request
action: email_draft
agent: cloud
created: 2026-03-03T12:00:00Z
expires: 2026-03-03T23:59:59Z
status: pending
priority: medium
domain: email
---
```

### Cloud Approval Flow
```
Cloud agent drafts → Pending_Approval/<domain>/
  → Vault syncs to Local
  → Human reviews in Obsidian
  → Human moves to /Approved/
  → Local orchestrator detects → Executes action
```

### Cloud vs Local Approval Rules
| Source | Creates Approval In | Executed By |
|--------|-------------------|-------------|
| Cloud (email draft) | `Pending_Approval/email/` | Local |
| Cloud (social draft) | `Pending_Approval/social/` | Local |
| Cloud (Odoo invoice) | `Pending_Approval/finance/` | Local |
| Local (any action) | `Pending_Approval/` | Local |

## Escalation

If an action is rejected:
1. Log the rejection with reason
2. Do NOT retry the same action
3. Wait for new instructions or a modified request
4. Never attempt to circumvent a rejection
