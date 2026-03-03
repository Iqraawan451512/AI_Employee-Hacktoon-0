"""
Git-based Vault Sync for AI Employee.

Synchronizes the AI_Employee_Vault between Cloud and Local agents via Git.
Runs in a 30-second loop: add → commit → pull --rebase → push.

Conflict resolution:
  - Dashboard.md: Local always wins (single-writer rule via .gitattributes merge=ours)
  - Other files: Git auto-merge; on conflict, keep theirs + save ours as .conflict

Usage:
    uv run python vault_sync.py                     # continuous 30s loop
    uv run python vault_sync.py --once              # single sync cycle
    uv run python vault_sync.py --interval 60       # custom interval
    uv run python vault_sync.py --vault ../AI_Employee_Vault
"""

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("VaultSync")

DEFAULT_VAULT = Path(__file__).parent.parent / "AI_Employee_Vault"


def run_git(args: list[str], cwd: Path, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    cmd = ["git"] + args
    logger.debug(f"Running: {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def has_remote(vault_path: Path) -> bool:
    """Check if the vault repo has a remote configured."""
    result = run_git(["remote"], vault_path)
    return bool(result.stdout.strip())


def sync_once(vault_path: Path, agent: str = "local") -> dict:
    """Perform a single sync cycle: add → commit → pull --rebase → push.

    Returns a dict with sync results.
    """
    status = {"timestamp": datetime.now(timezone.utc).isoformat(), "agent": agent}

    # Stage all changes
    result = run_git(["add", "-A"], vault_path)
    if result.returncode != 0:
        logger.error(f"git add failed: {result.stderr}")
        status["error"] = f"git add: {result.stderr}"
        return status

    # Check if there's anything to commit
    result = run_git(["status", "--porcelain"], vault_path)
    if not result.stdout.strip():
        logger.info("Nothing to commit")
        status["action"] = "noop"
        return status

    # Commit with timestamp
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    msg = f"vault-sync [{agent}] {ts}"
    result = run_git(["commit", "-m", msg], vault_path)
    if result.returncode != 0:
        logger.error(f"git commit failed: {result.stderr}")
        status["error"] = f"git commit: {result.stderr}"
        return status

    logger.info(f"Committed: {msg}")
    status["committed"] = True

    # Pull with rebase (only if remote exists)
    if not has_remote(vault_path):
        logger.info("No remote configured — skipping pull/push")
        status["action"] = "commit_only"
        return status

    result = run_git(["pull", "--rebase", "--autostash"], vault_path, timeout=60)
    if result.returncode != 0:
        stderr = result.stderr
        if "CONFLICT" in stderr or "conflict" in result.stdout:
            logger.warning("Merge conflict detected — attempting resolution")
            _resolve_conflicts(vault_path)
            run_git(["rebase", "--continue"], vault_path)
            status["conflicts_resolved"] = True
        else:
            logger.error(f"git pull failed: {stderr}")
            # Abort rebase if in progress
            run_git(["rebase", "--abort"], vault_path)
            status["error"] = f"git pull: {stderr}"
            return status

    # Push
    result = run_git(["push"], vault_path, timeout=60)
    if result.returncode != 0:
        logger.error(f"git push failed: {result.stderr}")
        status["error"] = f"git push: {result.stderr}"
        return status

    logger.info("Push successful")
    status["action"] = "synced"
    return status


def _resolve_conflicts(vault_path: Path):
    """Resolve merge conflicts using the single-writer rule.

    Dashboard.md: always keep ours (Local)
    Everything else: keep theirs (remote/Cloud), save ours as .conflict
    """
    result = run_git(["diff", "--name-only", "--diff-filter=U"], vault_path)
    conflicted = [f.strip() for f in result.stdout.splitlines() if f.strip()]

    for filename in conflicted:
        filepath = vault_path / filename

        if filename == "Dashboard.md":
            # Local always wins for Dashboard.md
            run_git(["checkout", "--ours", filename], vault_path)
            logger.info(f"Conflict resolved (ours/local wins): {filename}")
        else:
            # For other files, keep theirs (cloud) and save our version
            conflict_path = filepath.with_suffix(filepath.suffix + ".conflict")
            run_git(["show", f":2:{filename}"], vault_path)  # ours
            ours_result = run_git(["show", f":2:{filename}"], vault_path)
            if ours_result.returncode == 0:
                conflict_path.write_text(ours_result.stdout, encoding="utf-8")
                logger.info(f"Saved local version as {conflict_path.name}")

            run_git(["checkout", "--theirs", filename], vault_path)
            logger.info(f"Conflict resolved (theirs/cloud wins): {filename}")

        run_git(["add", filename], vault_path)


def write_sync_signal(vault_path: Path, status: dict):
    """Write a sync status signal to Updates/ for the dashboard merger."""
    updates_dir = vault_path / "Updates"
    updates_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    signal_file = updates_dir / f"SYNC_{ts}.md"
    action = status.get("action", status.get("error", "unknown"))
    content = f"""---
type: sync_status
agent: {status.get('agent', 'unknown')}
timestamp: {status.get('timestamp', '')}
action: {action}
---

# Vault Sync Signal

- **Agent**: {status.get('agent', 'unknown')}
- **Action**: {action}
- **Time**: {status.get('timestamp', '')}
"""
    if status.get("conflicts_resolved"):
        content += "- **Conflicts**: Resolved automatically\n"
    if status.get("error"):
        content += f"- **Error**: {status['error']}\n"

    signal_file.write_text(content, encoding="utf-8")


def run_loop(vault_path: Path, interval: int = 30, agent: str = "local"):
    """Continuous sync loop."""
    logger.info(f"Vault sync starting (agent={agent}, interval={interval}s, vault={vault_path})")
    try:
        while True:
            try:
                status = sync_once(vault_path, agent=agent)
                if status.get("error"):
                    write_sync_signal(vault_path, status)
                elif status.get("action") != "noop":
                    write_sync_signal(vault_path, status)
            except Exception as e:
                logger.error(f"Sync cycle error: {e}")
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Vault sync stopped.")


def main():
    parser = argparse.ArgumentParser(description="AI Employee Vault Git Sync")
    parser.add_argument("--vault", type=str, default=str(DEFAULT_VAULT), help="Path to vault")
    parser.add_argument("--once", action="store_true", help="Single sync cycle")
    parser.add_argument("--interval", type=int, default=30, help="Sync interval in seconds")
    parser.add_argument("--agent", type=str, default="local", choices=["cloud", "local"],
                        help="Agent identity (cloud or local)")
    args = parser.parse_args()

    vault_path = Path(args.vault)
    if not vault_path.exists():
        logger.error(f"Vault path does not exist: {vault_path}")
        sys.exit(1)

    if args.once:
        status = sync_once(vault_path, agent=args.agent)
        print(f"Sync result: {status}")
    else:
        run_loop(vault_path, interval=args.interval, agent=args.agent)


if __name__ == "__main__":
    main()
