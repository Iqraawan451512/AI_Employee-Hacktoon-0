---
name: gmail-watcher
description: |
  Monitor Gmail for new unread/important emails and create action items in the vault.
  Uses Google Gmail API with OAuth2 credentials. Polls every 2 minutes for new messages
  and writes them as markdown files to /Needs_Action for Claude to process.
user_invocable: true
---

# Gmail Watcher Skill

Monitor Gmail for unread important emails and create actionable files in the vault.

## Prerequisites

1. **Google Cloud Project** with Gmail API enabled
2. **OAuth2 credentials** (`credentials.json`) downloaded from Google Cloud Console
3. **First-time auth**: Run the watcher once interactively to complete the OAuth flow and generate `token.json`

### Setup Steps

```bash
# 1. Install dependencies
cd watchers && uv add google-auth google-auth-oauthlib google-api-python-client

# 2. Place credentials.json in watchers/ directory
# Download from: https://console.cloud.google.com/apis/credentials

# 3. First run (interactive - will open browser for OAuth)
cd watchers && uv run python gmail_watcher.py --vault-path ../AI_Employee_Vault --credentials credentials.json

# 4. After auth, token.json is saved. Future runs are non-interactive.
```

## Start the Gmail Watcher

```bash
cd watchers && uv run python gmail_watcher.py \
  --vault-path ../AI_Employee_Vault \
  --credentials credentials.json
```

Run in the background for continuous monitoring. Polls every 120 seconds by default.

## How It Works

1. **Connects** to Gmail API using OAuth2 credentials
2. **Queries** for unread important messages: `is:unread is:important`
3. **For each new email**, creates a markdown file in `/Needs_Action/`:

```markdown
---
type: email
from: sender@example.com
subject: Invoice Request
received: 2026-02-26T10:30:00Z
priority: high
status: pending
gmail_id: 18d3f2a1b4c5
---

## Email Content
<email snippet/body>

## Suggested Actions
- [ ] Reply to sender
- [ ] Forward to relevant party
- [ ] Archive after processing
```

4. **Tracks** processed message IDs to avoid duplicates
5. **Logs** each detection to `/Logs/YYYY-MM-DD.json`

## Urgent Keyword Detection

Per Company Handbook, emails containing these keywords are flagged as **high priority**:
- `urgent`, `asap`, `emergency`, `critical`
- `invoice`, `payment`, `overdue`

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--vault-path` | `../AI_Employee_Vault` | Path to Obsidian vault |
| `--credentials` | `credentials.json` | Path to Google OAuth credentials |
| `--interval` | `120` | Poll interval in seconds |
| `--query` | `is:unread is:important` | Gmail search query |

## Watcher Script

The watcher script is at `watchers/gmail_watcher.py`. It extends `BaseWatcher` and uses the Google Gmail API.

## Stop the Watcher

```bash
ps aux | grep gmail_watcher | grep -v grep | awk '{print $2}' | xargs kill
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 403 Forbidden | Enable Gmail API in Google Cloud Console |
| Token expired | Delete `token.json` and re-authenticate |
| No emails detected | Check the `--query` filter; try `is:unread` only |
| Rate limited | Increase `--interval` to 300+ seconds |
