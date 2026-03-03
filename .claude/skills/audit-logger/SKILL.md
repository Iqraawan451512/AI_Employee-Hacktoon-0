---
name: audit-logger
description: |
  Comprehensive audit logging for all AI Employee actions. Every operation (inbox processing,
  social posts, emails, approvals, errors, system events) is logged with full context.
  Provides structured JSON logs in /Logs with retrieval and error counting utilities.
user_invocable: false
---

# Audit Logger

## What This Skill Does
- Provides centralized logging for ALL AI Employee actions
- Writes structured JSON entries to daily log files in `/Logs`
- Tracks: action type, actor, target, parameters, result, approval info
- Offers helper methods for common log types (social, email, approval, error)
- Supports log retrieval and error counting for briefings

## Usage in Code

```python
from audit_logger import AuditLogger

logger = AuditLogger(vault_path)

# General logging
logger.log("inbox_processed", actor="process-inbox", target="invoice.pdf")

# Social media
logger.log_social_post("linkedin", content_length=450, dry_run=False)

# Email
logger.log_email("received", subject="Partnership Inquiry", sender="client@example.com")

# Approvals
logger.log_approval("LINKEDIN_POST_001.md", status="approved")

# Errors
logger.log_error("gmail_watcher", "Connection timeout", action="fetch_emails")

# System events
logger.log_system("watchdog_restart", "filesystem_watcher restarted (attempt #2)")
```

## CLI Usage

```bash
# Log a manual entry
uv run python watchers/audit_logger.py --vault-path AI_Employee_Vault --action "manual_test" --actor "human"

# View recent logs
uv run python watchers/audit_logger.py --vault-path AI_Employee_Vault --show-logs --days 3
```

## Log Format
Each entry in `/Logs/YYYY-MM-DD.json`:
```json
{
  "timestamp": "2026-02-27T10:00:00Z",
  "action_type": "inbox_processed",
  "actor": "process-inbox",
  "target": "invoice.pdf",
  "parameters": {"priority": "high"},
  "result": "success"
}
```
