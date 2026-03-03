---
last_updated: 2026-03-03
review_frequency: monthly
tier: platinum
---

# Company Handbook - Rules of Engagement

## General Principles
1. **Safety First**: Never take irreversible actions without human approval
2. **Transparency**: Log every action taken by the AI Employee
3. **Privacy**: Keep all data local; minimize external API calls
4. **Accuracy**: When unsure, ask for clarification rather than guessing
5. **Plan Before Acting**: For multi-step tasks, create a Plan.md before executing
6. **Resilience**: Retry transient errors, escalate permanent failures

## Communication Rules
- Always be professional and polite in all communications
- Never send messages on behalf of the user without explicit approval
- Flag urgent messages (containing keywords: urgent, asap, emergency, critical)
- Respond to known contacts only; flag unknown contacts for review

## File Processing Rules
- Files dropped in `/Inbox` are automatically moved to `/Needs_Action`
- Each file gets a metadata `.md` companion with processing instructions
- Processed files are moved to `/Done` with a completion timestamp
- Never delete original files; always move them

## Approval Thresholds
| Action | Auto-Approve | Requires Human Approval |
|--------|-------------|------------------------|
| File processing | Read, categorize | Delete, send externally |
| Email | Draft replies | Send to any recipient |
| Payments | None | All payments |
| Social media | Draft posts | Publish posts |
| WhatsApp | Read messages | Send any reply |

See [[Approval_Policy]] for the full HITL workflow details.

## Priority Levels
| Priority | Response Time | Examples |
|----------|--------------|---------|
| Critical | Immediate | System errors, security alerts, urgent keywords |
| High | Within 1 hour | Client messages, financial keywords, urgent emails |
| Medium | Within 4 hours | Regular tasks, follow-ups |
| Low | Within 24 hours | Reports, non-urgent updates |

## Watcher Rules
- **Gmail Watcher**: Polls every 120 seconds for `is:unread is:important`
- **WhatsApp Watcher**: Polls every 30 seconds for keyword matches
- **File Watcher**: Continuous monitoring of `/Inbox`
- All watchers log detections to `/Logs/`
- See [[Watchers_Status]] for full configuration

## Planning Rules (Reasoning Loop)
- For any task with 3+ steps, create a `Plan.md` in `/Plans/` before executing
- Plans must include: objective, steps with checkboxes, dependencies, and approval items
- Reference source items from `/Needs_Action/`
- Update plans as steps are completed
- Move completed plans to `/Done/`

## Social Media Posting Rules
- All posts must be drafted first and saved to `/Plans/`
- Publishing requires human approval via `/Pending_Approval/`
- **LinkedIn**: Post 2-3x/week, max 1300 chars, 3-5 hashtags + CTA
- **Twitter/X**: Max 280 chars, draft via twitter_poster.py
- **Facebook**: Business-focused content, engage with comments within 24h
- **Instagram**: Visual content preferred, use relevant hashtags (up to 30)
- Content must align with [[Business_Goals]]

## Email Rules
- Draft replies are auto-approved (saved to vault only)
- Sending any email requires approval via `/Pending_Approval/`
- Maximum 10 emails per hour (rate limit)
- New recipients always flagged for extra review
- Log every sent email to `/Logs/`

## Financial Rules
- All payments require human approval regardless of amount
- Invoices must be logged in [[Bank_Transactions]]
- Monthly budget review on 1st of each month
- Flag transactions over $50 for priority review

## Scheduling
- See [[Scheduling_Config]] for the full schedule
- Daily inbox processing at 8:00 AM
- Dashboard updates every 4 hours
- Approval checks every hour
- Social media posts per weekly schedule
- CEO Briefing every Monday at 7:00 AM
- Weekly planning session (Sunday 8:00 PM)

## Error Handling
1. Log all errors to `/Logs/` via [[audit-logger]]
2. Retry transient errors up to 3 times with exponential backoff
3. Alert human on authentication failures immediately
4. Quarantine corrupted or unprocessable files
5. Watchdog auto-restarts crashed processes (max 10 restarts)
6. Max restarts exceeded -> alert in `/Needs_Action/`
7. See [[Error_Recovery_Playbook]] for detailed procedures

## Ralph Wiggum Loop (Autonomous Mode)
- When enabled, Claude processes items continuously until inbox is clear
- Maximum 20 iterations per day (safety limit)
- All HITL rules still apply during autonomous mode
- Human can interrupt at any time with Ctrl+C

## Orchestrator Rules
- Orchestrator classifies tasks by domain (email, social, finance, etc.)
- Routes to appropriate handler script automatically
- Scheduled tasks checked on each scan cycle
- All routing decisions logged to `/Logs/`

## Work-Zone Ownership (Platinum)
| Domain | Cloud Agent (draft-only) | Local Agent (execute) |
|--------|-------------------------|----------------------|
| Email triage + draft replies | YES | — |
| Social post drafts | YES | — |
| Odoo draft invoices | YES | — |
| Approvals | — | YES |
| WhatsApp | — | YES |
| Payments/Banking | — | YES |
| Send email | — | YES |
| Publish social post | — | YES |
| Post Odoo invoices | — | YES |

**Rule**: Cloud agent NEVER sends, posts, or makes payments. All Cloud outputs are drafts.

## Claim-by-Move Protocol
- Before processing a task, the agent must claim it via `claim_manager.try_claim()`
- Claiming atomically moves the file to `In_Progress/<agent>/`
- If the file is gone (claimed by other agent), the claim returns None — move on
- After processing, release the file to the destination folder
- Both Cloud and Local agents MUST use this protocol for all task processing

## Vault Sync Rules
- Vault syncs via Git every 30 seconds on both Cloud and Local
- **Single-writer rule**: Only Local writes `Dashboard.md`
- Cloud writes signals to `Updates/` and `Signals/` — never edits Dashboard directly
- Dashboard merger (Local-only) reads `Updates/` and appends to Dashboard.md
- On merge conflicts: `Dashboard.md` keeps Local's version; other files keep remote
- See [[Sync_Config]] for full Git sync configuration

## Security
- Never store credentials in the vault (use `.env` or OS credential manager)
- Add `credentials.json`, `token.json`, `whatsapp_session/` to `.gitignore`
- Rotate credentials monthly
- All actions are logged for audit trail

## Audit Requirements
- All actions logged in JSON format to `/Logs/YYYY-MM-DD.json`
- Retain logs for minimum 90 days
- Weekly log review recommended
- CEO Briefing includes error/restart metrics
- See [[Approval_Policy]] for approval audit trail

## Related Documents
- [[Dashboard]] - Real-time system status
- [[Business_Goals]] - Revenue targets and content strategy
- [[Approval_Policy]] - Full HITL approval workflow
- [[Watchers_Status]] - Watcher configuration and status
- [[Scheduling_Config]] - Scheduled task setup
- [[Bank_Transactions]] - Financial tracking
- [[Error_Recovery_Playbook]] - Error handling procedures
- [[Sync_Config]] - Vault Git sync configuration
- [[Cloud_Status]] - Cloud VM status
- [[Odoo_Config]] - Odoo ERP connection details
- [[Architecture]] - System architecture
