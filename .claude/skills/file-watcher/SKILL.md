---
name: file-watcher
description: |
  Start or stop the file system watcher that monitors the Inbox folder for new files.
  The watcher automatically creates action items in /Needs_Action when files are dropped
  into /Inbox. Use to manage the watcher lifecycle.
user_invocable: true
---

# File Watcher Skill

Manage the file system watcher that monitors the AI Employee Vault's `/Inbox` folder.

## Start the Watcher

```bash
cd watchers && uv run python filesystem_watcher.py --vault-path ../AI_Employee_Vault
```

Run this in the background. The watcher will:
1. Monitor `AI_Employee_Vault/Inbox/` for new files
2. Copy new files to `AI_Employee_Vault/Needs_Action/`
3. Create a metadata `.md` file with file details
4. Log the detection to `AI_Employee_Vault/Logs/YYYY-MM-DD.json`

## Stop the Watcher

Find and stop the running watcher process:

```bash
# On Windows (Git Bash)
taskkill //F //FI "WINDOWTITLE eq *filesystem_watcher*" 2>/dev/null
# Or find the PID and kill it
ps aux | grep filesystem_watcher | grep -v grep | awk '{print $2}' | xargs kill
```

## Check Watcher Status

```bash
ps aux | grep filesystem_watcher | grep -v grep
```

If output is empty, the watcher is not running.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Watcher not detecting files | Ensure the Inbox folder exists and has write permissions |
| Duplicate action files | Check if watcher is running multiple instances |
| Permission errors | Run with appropriate file system permissions |
