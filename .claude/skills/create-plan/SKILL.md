---
name: create-plan
description: |
  Claude reasoning loop that analyzes tasks in /Needs_Action and creates structured Plan.md
  files with step-by-step action items. Implements the Read → Think → Plan pattern from the
  AI Employee architecture. Use when tasks need multi-step planning before execution.
user_invocable: true
---

# Create Plan Skill

Analyze pending tasks and create structured Plan.md files in the vault.

## Purpose

This skill implements the **Reasoning Layer** of the AI Employee architecture:
1. **Read**: Check `/Needs_Action` and understand pending items
2. **Think**: Analyze what needs to be done, identify dependencies and risks
3. **Plan**: Create a `Plan.md` with checkboxes for each step

## Workflow

### Step 1: Gather Context

Read these files to understand the current state:
- `AI_Employee_Vault/Company_Handbook.md` — rules and thresholds
- `AI_Employee_Vault/Business_Goals.md` — current objectives (if exists)
- `AI_Employee_Vault/Dashboard.md` — current system state
- All files in `AI_Employee_Vault/Needs_Action/` — pending items

### Step 2: Analyze and Reason

For each item in `/Needs_Action`:
1. Determine the **type** (email, file_drop, whatsapp_message, task)
2. Assess **priority** using Company Handbook rules
3. Check for **urgent keywords**: urgent, asap, emergency, critical
4. Identify **dependencies** (does this task need something else first?)
5. Determine if **human approval** is needed (per approval thresholds)
6. Estimate **complexity** (simple / medium / complex)

### Step 3: Create Plan.md

Write a structured plan file to `AI_Employee_Vault/Plans/`:

```markdown
# AI_Employee_Vault/Plans/PLAN_<descriptive_name>_<date>.md
---
created: 2026-02-26T10:30:00Z
status: pending
priority: high
source: /Needs_Action/<source_file>.md
estimated_steps: 5
requires_approval: true
---

# Plan: <Descriptive Title>

## Objective
<Clear statement of what this plan accomplishes>

## Context
- **Source**: <what triggered this plan>
- **Priority**: <critical/high/medium/low>
- **Approval Required**: <yes/no — which steps>

## Steps
- [ ] Step 1: <action description>
- [ ] Step 2: <action description>
- [ ] Step 3: <action description> *(requires approval)*
- [ ] Step 4: <action description>
- [ ] Step 5: <action description>

## Dependencies
- <any prerequisite tasks or information needed>

## Risks
- <potential issues and mitigations>

## Expected Outcome
<what success looks like>

## Approval Items
<list any steps that need human approval, with files to create in /Pending_Approval>
```

### Step 4: Link and Log

1. **Update** the source file in `/Needs_Action/` to reference the plan
2. **Log** plan creation to `/Logs/YYYY-MM-DD.json`
3. **Update** Dashboard with the new plan

## Reasoning Rules

### Priority Assessment
| Condition | Priority |
|-----------|----------|
| Contains urgent keywords | Critical |
| From known client | High |
| Financial action needed | High |
| Regular task | Medium |
| Informational only | Low |

### Approval Requirements (from Company Handbook)
| Action | Auto-Approve | Needs Approval |
|--------|-------------|----------------|
| File processing | Read, categorize | Delete, send externally |
| Email | Draft replies | Send to any recipient |
| Payments | None | All payments |
| Social media | Draft posts | Publish posts |

### Plan Complexity Guide
| Complexity | Steps | Example |
|------------|-------|---------|
| Simple | 1-3 | File categorization, read and summarize |
| Medium | 4-7 | Draft email reply, create invoice |
| Complex | 8+ | Multi-step client engagement, project setup |

## Multi-Item Planning

When multiple items are in `/Needs_Action/`:
1. Group related items (e.g., emails from same sender)
2. Create separate plans for unrelated items
3. Order by priority (Critical → High → Medium → Low)
4. Note cross-dependencies between plans

## Example: Email Requesting Invoice

**Input** (`/Needs_Action/EMAIL_abc123.md`):
```
type: email
from: client@example.com
subject: January Invoice Request
```

**Output** (`/Plans/PLAN_invoice_client_2026-02-26.md`):
```markdown
---
created: 2026-02-26T10:30:00Z
status: pending
priority: high
source: /Needs_Action/EMAIL_abc123.md
estimated_steps: 5
requires_approval: true
---

# Plan: Generate and Send January Invoice to Client

## Objective
Create the January invoice and send it to client@example.com

## Steps
- [ ] Look up client rates in /Accounting/Rates.md
- [ ] Calculate total for January work
- [ ] Generate invoice document
- [ ] Draft email with invoice attached (requires approval)
- [ ] Send email after approval
- [ ] Log transaction and update Dashboard
```

## Logging Format

```json
{
  "timestamp": "2026-02-26T10:30:00Z",
  "action_type": "plan_created",
  "actor": "claude_code",
  "target": "PLAN_invoice_client_2026-02-26.md",
  "parameters": {
    "source": "EMAIL_abc123.md",
    "priority": "high",
    "steps": 5,
    "requires_approval": true
  },
  "result": "success"
}
```
