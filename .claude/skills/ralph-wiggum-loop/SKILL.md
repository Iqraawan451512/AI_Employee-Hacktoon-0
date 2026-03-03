---
name: ralph-wiggum-loop
description: |
  Autonomous multi-step task completion loop. When Claude finishes one task, the stop hook
  checks for remaining work in /Needs_Action and /Inbox. If tasks remain, it re-prompts
  Claude to continue working. Named after the "I'm in danger" meme — Claude keeps going
  until the inbox is clear. Implements the autonomous FTE behavior from Gold tier.
user_invocable: true
---

# Ralph Wiggum Loop (Autonomous Task Loop)

## What This Skill Does
The Ralph Wiggum Loop makes the AI Employee truly autonomous by:
1. After Claude finishes a task, the stop hook checks `/Needs_Action` and `/Inbox`
2. If pending work exists, it automatically re-prompts Claude to continue
3. Claude processes the next item, completes it, and the cycle repeats
4. The loop stops when all folders are empty (no more work)

## How It Works

### Architecture
```
Claude completes task → Stop Hook fires → Check vault folders
                                            ↓
                                    Items remaining?
                                    YES → Re-prompt Claude
                                    NO  → Stop (all done)
```

### The Stop Hook Script
Located at `watchers/ralph_wiggum_hook.py`, this script:
- Scans `/Inbox` and `/Needs_Action` for pending items
- If items exist, outputs a prompt telling Claude to process the next one
- If empty, exits cleanly (Claude stops)

### Setup
Add to `.claude/settings.json` hooks config:
```json
{
  "hooks": {
    "Stop": [
      {
        "type": "command",
        "command": "python watchers/ralph_wiggum_hook.py --vault-path AI_Employee_Vault"
      }
    ]
  }
}
```

### Manual Trigger
To manually start the loop:
1. Drop files into `/Inbox` or `/Needs_Action`
2. Tell Claude: "Process all inbox items using the Ralph Wiggum loop"
3. Claude will process each item one by one until the inbox is clear

### Safety
- Respects all Company Handbook rules (HITL for sensitive actions)
- Maximum 20 iterations per loop to prevent runaway
- Each action is logged via audit logger
- Human can interrupt at any time by pressing Ctrl+C

## When to Use
- Batch processing multiple inbox items
- End-of-day cleanup of all pending tasks
- Autonomous operation during unattended hours
- Processing a backlog of action items
