---
name: gmail-sender
description: |
  Send emails via Gmail using Playwright browser automation (MCP server for external action).
  Supports drafting, sending, and replying to emails through Gmail's web interface.
  All sends require human approval per Company Handbook. Includes dry-run mode.
user_invocable: true
---

# Gmail Sender Skill (Email MCP)

Send emails through Gmail using Playwright browser automation. This serves as the **MCP server for external email actions** in the Silver tier.

## Prerequisites

1. **Playwright MCP server** running (uses `browsing-with-playwright` skill)
2. **Gmail account** logged in via Playwright browser session
3. **Company Handbook** rules: all email sends require human approval

## Workflow

### Step 1: Create Draft (Auto-Approved)

Claude drafts the email and saves it to the vault:

```markdown
# AI_Employee_Vault/Plans/EMAIL_DRAFT_<recipient>_<date>.md
---
type: email_draft
to: recipient@example.com
subject: Re: Invoice Request
status: draft
created: 2026-02-26T10:30:00Z
in_reply_to: EMAIL_abc123
---

## Email Draft

**To**: recipient@example.com
**Subject**: Re: Invoice Request
**Body**:

Dear Client,

Please find attached the invoice for February 2026.

Best regards,
[Your Name]

**Attachments**: (if any)
- /Vault/Invoices/2026-02_invoice.pdf
```

### Step 2: Request Approval (HITL)

Per Company Handbook, sending emails **always requires human approval**:

```markdown
# AI_Employee_Vault/Pending_Approval/EMAIL_SEND_<recipient>_<date>.md
---
type: approval_request
action: send_email
to: recipient@example.com
subject: Re: Invoice Request
created: 2026-02-26T10:30:00Z
expires: 2026-02-27T10:30:00Z
status: pending
---

## Email to Send

**To**: recipient@example.com
**Subject**: Re: Invoice Request

### Body Preview
Dear Client,
Please find attached the invoice for February 2026.
Best regards, [Your Name]

## To Approve
Move this file to /Approved folder.

## To Reject
Move this file to /Rejected folder.

## To Edit
Modify the email content above, then move to /Approved.
```

### Step 3: Send via Playwright (After Approval)

Once the approval file appears in `/Approved/`:

```bash
# 1. Start Playwright MCP
bash .claude/skills/browsing-with-playwright/scripts/start-server.sh

# 2. Navigate to Gmail compose
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_navigate \
  -p '{"url": "https://mail.google.com/mail/u/0/#inbox?compose=new"}'

# 3. Snapshot to find compose fields
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_snapshot -p '{}'

# 4. Fill To field
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_type \
  -p '{"element": "To", "ref": "<ref>", "text": "recipient@example.com", "submit": false}'

# 5. Fill Subject field
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_type \
  -p '{"element": "Subject", "ref": "<ref>", "text": "Re: Invoice Request", "submit": false}'

# 6. Fill Body
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_type \
  -p '{"element": "Message Body", "ref": "<ref>", "text": "<email body>"}'

# 7. Click Send
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_click \
  -p '{"element": "Send", "ref": "<ref>"}'

# 8. Screenshot confirmation
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_take_screenshot \
  -p '{"type": "png", "fullPage": false}'
```

### Step 4: Log and Clean Up

```json
{
  "timestamp": "2026-02-26T10:35:00Z",
  "action_type": "email_send",
  "actor": "claude_code",
  "target": "recipient@example.com",
  "parameters": {
    "subject": "Re: Invoice Request",
    "method": "playwright_gmail"
  },
  "approval_status": "approved",
  "approved_by": "human",
  "result": "success"
}
```

Move approval file and draft to `/Done/`.

## Dry Run Mode

Set environment variable `DRY_RUN=true` to:
- Generate drafts and approval files
- Log what *would* be sent
- Skip the actual Playwright send step

```bash
export DRY_RUN=true
```

## Security Rules

1. **Never send without approval** — all sends go through `/Pending_Approval/`
2. **Never store credentials** in the vault — use environment variables
3. **Log every send** to `/Logs/` with full details
4. **Rate limit**: Maximum 10 emails per hour
5. **New recipients**: Always flag for extra review

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Gmail login required | Use Playwright headed mode to log in first |
| Compose window not found | Navigate to Gmail inbox first, then compose |
| Send button not clickable | Take fresh snapshot; check for pop-up dialogs |
| Attachment fails | Ensure file path is absolute and file exists |
