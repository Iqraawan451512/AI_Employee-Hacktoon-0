"""
CEO Briefing Generator for AI Employee.

Generates weekly "Monday Morning" briefings that summarize all AI Employee activity,
social media performance, inbox volume, tasks completed, and system health.

Usage:
    uv run python ceo_briefing.py --vault-path ../AI_Employee_Vault
    uv run python ceo_briefing.py --vault-path ../AI_Employee_Vault --days 14
"""

import argparse
import json
import logging
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

DEFAULT_VAULT = Path(__file__).parent.parent / "AI_Employee_Vault"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("CEOBriefing")


def gather_metrics(vault_path: Path, days: int = 7) -> dict:
    """Scan logs and vault folders to collect key metrics."""
    logs_dir = vault_path / "Logs"
    metrics = {
        "period_days": days,
        "total_actions": 0,
        "actions_by_type": Counter(),
        "actions_by_actor": Counter(),
        "social_posts": {"linkedin": 0, "twitter": 0, "facebook": 0, "instagram": 0},
        "emails_processed": 0,
        "tasks_completed": 0,
        "errors": 0,
        "restarts": 0,
        "approvals": {"approved": 0, "rejected": 0, "pending": 0},
    }

    # Scan daily log files
    for i in range(days):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        log_file = logs_dir / f"{day}.json"
        if not log_file.exists():
            continue
        try:
            logs = json.loads(log_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        for entry in logs:
            metrics["total_actions"] += 1
            action = entry.get("action_type", "unknown")
            actor = entry.get("actor", "unknown")
            metrics["actions_by_type"][action] += 1
            metrics["actions_by_actor"][actor] += 1

            if "linkedin_post_published" in action:
                metrics["social_posts"]["linkedin"] += 1
            elif "twitter_post_published" in action:
                metrics["social_posts"]["twitter"] += 1
            elif "facebook_post_published" in action:
                metrics["social_posts"]["facebook"] += 1
            elif "instagram_post_published" in action:
                metrics["social_posts"]["instagram"] += 1
            elif "email" in action:
                metrics["emails_processed"] += 1
            elif action in ("task_completed", "inbox_processed", "file_processed"):
                metrics["tasks_completed"] += 1
            elif "error" in action or "failed" in action:
                metrics["errors"] += 1
            elif "restart" in action:
                metrics["restarts"] += 1

    # Count current vault state
    for folder, key in [("Pending_Approval", "pending"), ("Approved", "approved"), ("Rejected", "rejected")]:
        folder_path = vault_path / folder
        if folder_path.exists():
            metrics["approvals"][key] = len(list(folder_path.iterdir()))

    # Count Done items
    done_dir = vault_path / "Done"
    if done_dir.exists():
        metrics["tasks_completed"] = max(metrics["tasks_completed"], len(list(done_dir.iterdir())))

    # Count pending items
    needs_action = vault_path / "Needs_Action"
    metrics["pending_tasks"] = len(list(needs_action.iterdir())) if needs_action.exists() else 0

    inbox = vault_path / "Inbox"
    metrics["inbox_items"] = len(list(inbox.iterdir())) if inbox.exists() else 0

    return metrics


def generate_briefing(vault_path: Path, days: int = 7) -> Path:
    """Generate a CEO Monday Morning Briefing."""
    metrics = gather_metrics(vault_path, days)
    briefings_dir = vault_path / "Briefings"
    briefings_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = datetime.now().strftime("%Y-%m-%d")
    social = metrics["social_posts"]
    total_social = sum(social.values())

    # Determine system health
    if metrics["errors"] == 0 and metrics["restarts"] == 0:
        health = "Excellent"
        health_icon = "GREEN"
    elif metrics["errors"] <= 2 and metrics["restarts"] <= 1:
        health = "Good"
        health_icon = "YELLOW"
    else:
        health = "Needs Attention"
        health_icon = "RED"

    # Top actions
    top_actions = metrics["actions_by_type"].most_common(5)
    top_actions_md = "\n".join(f"| {action} | {count} |" for action, count in top_actions) if top_actions else "| No activity recorded | - |"

    # Recommendations
    recs = []
    if total_social < 3:
        recs.append("- Increase social media posting frequency (target: 3-5/week)")
    if metrics["pending_tasks"] > 5:
        recs.append(f"- {metrics['pending_tasks']} tasks pending in /Needs_Action - review and clear backlog")
    if metrics["inbox_items"] > 0:
        recs.append(f"- {metrics['inbox_items']} items in /Inbox awaiting processing")
    if metrics["errors"] > 0:
        recs.append(f"- {metrics['errors']} errors detected this period - investigate logs")
    if metrics["restarts"] > 0:
        recs.append(f"- {metrics['restarts']} process restarts detected - check system stability")
    if metrics["approvals"]["pending"] > 0:
        recs.append(f"- {metrics['approvals']['pending']} items awaiting approval in /Pending_Approval")
    if not recs:
        recs.append("- All systems running smoothly. Keep up the good work!")

    briefing = f"""---
type: ceo_briefing
generated: {timestamp}
period: last {days} days
system_health: {health}
---

# Monday Morning Briefing - {date_str}

## System Health: [{health_icon}] {health}

## Key Metrics
| Metric | Value |
|--------|-------|
| Total Actions Logged | {metrics['total_actions']} |
| Tasks Completed | {metrics['tasks_completed']} |
| Emails Processed | {metrics['emails_processed']} |
| System Errors | {metrics['errors']} |
| Process Restarts | {metrics['restarts']} |

## Social Media Performance
| Platform | Posts Published |
|----------|---------------|
| LinkedIn | {social['linkedin']} |
| Twitter/X | {social['twitter']} |
| Facebook | {social['facebook']} |
| Instagram | {social['instagram']} |
| **Total** | **{total_social}** |

## Approval Pipeline
| Status | Count |
|--------|-------|
| Pending | {metrics['approvals']['pending']} |
| Approved | {metrics['approvals']['approved']} |
| Rejected | {metrics['approvals']['rejected']} |

## Top Activities
| Action | Count |
|--------|-------|
{top_actions_md}

## Current Backlog
- **Inbox**: {metrics['inbox_items']} items
- **Needs Action**: {metrics['pending_tasks']} items

## Recommendations
{chr(10).join(recs)}

---
*Generated by AI Employee v0.3 (Gold Tier) | {timestamp}*
"""

    filepath = briefings_dir / f"{date_str}_CEO_Briefing.md"
    filepath.write_text(briefing, encoding="utf-8")
    logger.info(f"CEO Briefing generated: {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="AI Employee CEO Briefing Generator")
    parser.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))
    parser.add_argument("--days", type=int, default=7, help="Number of days to cover")
    args = parser.parse_args()

    generate_briefing(Path(args.vault_path), args.days)


if __name__ == "__main__":
    main()
