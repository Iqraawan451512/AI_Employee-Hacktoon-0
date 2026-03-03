"""
Ralph Wiggum Loop - Stop Hook for Autonomous Task Processing.

This script runs as a Claude Code stop hook. When Claude finishes a task,
this hook checks if there's more work in /Inbox or /Needs_Action.
If work remains, it outputs a prompt to re-engage Claude.

Usage (as stop hook):
    python watchers/ralph_wiggum_hook.py --vault-path AI_Employee_Vault

Setup in .claude/settings.json:
    "hooks": { "Stop": [{"type": "command", "command": "python watchers/ralph_wiggum_hook.py --vault-path AI_Employee_Vault"}] }
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_VAULT = Path(__file__).parent.parent / "AI_Employee_Vault"
MAX_ITERATIONS = 20
COUNTER_FILE = Path(__file__).parent / ".ralph_counter.json"


def get_pending_items(vault_path: Path) -> list[dict]:
    """Find all pending work items across vault folders."""
    items = []

    # Check /Inbox
    inbox = vault_path / "Inbox"
    if inbox.exists():
        for f in inbox.iterdir():
            if f.is_file() and not f.name.startswith("."):
                items.append({"folder": "Inbox", "file": f.name, "path": str(f)})

    # Check /Needs_Action
    needs_action = vault_path / "Needs_Action"
    if needs_action.exists():
        for f in needs_action.iterdir():
            if f.is_file() and not f.name.startswith("."):
                items.append({"folder": "Needs_Action", "file": f.name, "path": str(f)})

    # Check /Approved (posts waiting to be published)
    approved = vault_path / "Approved"
    if approved.exists():
        for f in approved.iterdir():
            if f.is_file() and not f.name.startswith("."):
                items.append({"folder": "Approved", "file": f.name, "path": str(f)})

    return items


def get_iteration_count() -> int:
    """Get current iteration count from counter file."""
    if COUNTER_FILE.exists():
        try:
            data = json.loads(COUNTER_FILE.read_text())
            # Reset counter if it's from a different day
            if data.get("date") != datetime.now().strftime("%Y-%m-%d"):
                return 0
            return data.get("count", 0)
        except (json.JSONDecodeError, OSError):
            return 0
    return 0


def increment_counter():
    """Increment the iteration counter."""
    count = get_iteration_count() + 1
    COUNTER_FILE.write_text(json.dumps({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "count": count,
        "last_run": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }))
    return count


def reset_counter():
    """Reset the iteration counter."""
    if COUNTER_FILE.exists():
        COUNTER_FILE.unlink()


def main():
    parser = argparse.ArgumentParser(description="Ralph Wiggum Loop - Stop Hook")
    parser.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))
    args = parser.parse_args()

    vault_path = Path(args.vault_path)
    items = get_pending_items(vault_path)

    if not items:
        # No work remaining - reset counter and exit cleanly
        reset_counter()
        sys.exit(0)

    # Check iteration limit
    iteration = get_iteration_count()
    if iteration >= MAX_ITERATIONS:
        print(f"Ralph Wiggum Loop: Max iterations ({MAX_ITERATIONS}) reached today. Stopping to prevent runaway.", file=sys.stderr)
        reset_counter()
        sys.exit(0)

    # Increment counter
    count = increment_counter()

    # Build the re-prompt
    item = items[0]
    remaining = len(items) - 1

    prompt = f"""[Ralph Wiggum Loop - Iteration {count}/{MAX_ITERATIONS}]

There are {len(items)} pending item(s) in the vault. Processing next item:

- **Folder**: {item['folder']}
- **File**: {item['file']}

Please process this item following Company Handbook rules:
1. Read the file from /{item['folder']}/{item['file']}
2. Analyze and take appropriate action
3. Move completed item to /Done
4. Log the action to /Logs
5. Update the Dashboard

{f"({remaining} more item(s) remaining after this one)" if remaining > 0 else "(This is the last item)"}"""

    # Output the prompt (Claude Code reads this from stdout)
    print(prompt)


if __name__ == "__main__":
    main()
