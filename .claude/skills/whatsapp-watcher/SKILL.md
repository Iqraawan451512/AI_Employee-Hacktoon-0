---
name: whatsapp-watcher
description: |
  Monitor WhatsApp Web for new unread messages containing business keywords.
  Uses Playwright browser automation to check WhatsApp Web periodically.
  Creates action items in /Needs_Action when urgent or business-related messages arrive.
user_invocable: true
---

# WhatsApp Watcher Skill

Monitor WhatsApp Web for unread messages with business-relevant keywords.

## Prerequisites

1. **Playwright** installed: `uv add playwright && uv run playwright install chromium`
2. **WhatsApp Web session**: First run requires QR code scan to authenticate
3. **Persistent browser context**: Session is saved so you only scan QR once

### Setup Steps

```bash
# 1. Install dependencies
cd watchers && uv add playwright
uv run playwright install chromium

# 2. First run (headed mode - scan QR code)
cd watchers && uv run python whatsapp_watcher.py \
  --vault-path ../AI_Employee_Vault \
  --session-path ./whatsapp_session \
  --headed

# 3. Scan the QR code with your phone
# 4. After login, session is saved. Future runs can be headless.
```

## Start the WhatsApp Watcher

```bash
cd watchers && uv run python whatsapp_watcher.py \
  --vault-path ../AI_Employee_Vault \
  --session-path ./whatsapp_session
```

Polls every 30 seconds by default.

## How It Works

1. **Launches** Chromium with a persistent session (WhatsApp stays logged in)
2. **Navigates** to WhatsApp Web
3. **Scans** for unread message indicators
4. **Filters** messages by business keywords
5. **Creates** action files in `/Needs_Action/` for matching messages

## Business Keywords (per Company Handbook)

Messages containing any of these keywords are captured:
- **Urgent**: `urgent`, `asap`, `emergency`, `critical`
- **Financial**: `invoice`, `payment`, `price`, `pricing`, `quote`, `budget`
- **Action**: `help`, `need`, `request`, `order`, `deadline`

## Output Format

```markdown
---
type: whatsapp_message
from: Contact Name
received: 2026-02-26T10:30:00Z
priority: high
status: pending
keywords_matched: [invoice, urgent]
---

## WhatsApp Message
**From**: Contact Name
**Time**: 2026-02-26 10:30 AM
**Message**: "Hey, can you send me the invoice for February? It's urgent."

## Suggested Actions
- [ ] Reply to sender
- [ ] Create invoice if requested
- [ ] Forward to relevant team member
- [ ] Log interaction
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--vault-path` | `../AI_Employee_Vault` | Path to Obsidian vault |
| `--session-path` | `./whatsapp_session` | Path for persistent browser session |
| `--interval` | `30` | Poll interval in seconds |
| `--headed` | `false` | Run browser in visible mode |

## Important Notes

- **Terms of Service**: WhatsApp's ToS may restrict automation. Use responsibly.
- **Session persistence**: The `--session-path` directory stores browser cookies. Never commit this to git.
- **Add to .gitignore**: `whatsapp_session/`

## Stop the Watcher

```bash
ps aux | grep whatsapp_watcher | grep -v grep | awk '{print $2}' | xargs kill
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| QR code keeps appearing | Session expired; delete session folder and re-scan |
| Browser crashes | Reduce poll interval; ensure enough RAM |
| No messages detected | Check keyword list; verify WhatsApp Web is logged in |
| Headless fails | Try `--headed` first to ensure login works |
