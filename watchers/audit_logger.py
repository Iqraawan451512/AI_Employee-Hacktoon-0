"""
Comprehensive Audit Logger for AI Employee.

Provides structured logging for all AI Employee actions with full audit trail.
Every action (inbox processing, social posts, emails, approvals, errors) gets logged
with timestamp, actor, action type, target, parameters, and result.

Usage:
    from audit_logger import AuditLogger
    logger = AuditLogger(vault_path)
    logger.log("inbox_processed", actor="process-inbox", target="invoice.pdf", params={"priority": "high"})
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_VAULT = Path(__file__).parent.parent / "AI_Employee_Vault"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("AuditLogger")


class AuditLogger:
    """Centralized audit logger for all AI Employee operations."""

    def __init__(self, vault_path: Path | str = DEFAULT_VAULT):
        self.vault_path = Path(vault_path)
        self.logs_dir = self.vault_path / "Logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        action_type: str,
        actor: str = "ai_employee",
        target: str = "",
        params: dict | None = None,
        result: str = "success",
        approval_status: str | None = None,
        approved_by: str | None = None,
        error: str | None = None,
    ) -> dict:
        """Log an action to the daily audit log file."""
        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "action_type": action_type,
            "actor": actor,
            "target": target,
            "parameters": params or {},
            "result": result,
        }
        if approval_status:
            entry["approval_status"] = approval_status
        if approved_by:
            entry["approved_by"] = approved_by
        if error:
            entry["error"] = error
            entry["result"] = "failed"

        self._write_entry(entry)
        log.info(f"[AUDIT] {action_type} by {actor} -> {target}: {result}")
        return entry

    def log_social_post(self, platform: str, content_length: int, dry_run: bool = False, success: bool = True):
        """Log a social media post action."""
        return self.log(
            action_type=f"{platform}_post_published" if success else f"{platform}_post_failed",
            actor=f"{platform}_poster",
            target=platform.title(),
            params={"content_length": content_length, "dry_run": dry_run},
            result="success" if success else "failed",
        )

    def log_email(self, action: str, subject: str, sender: str = "", recipient: str = ""):
        """Log an email action."""
        return self.log(
            action_type=f"email_{action}",
            actor="gmail_watcher" if action == "received" else "gmail_sender",
            target=subject,
            params={"sender": sender, "recipient": recipient},
        )

    def log_approval(self, item: str, status: str, approved_by: str = "human"):
        """Log an approval decision."""
        return self.log(
            action_type=f"approval_{status}",
            actor="approval_workflow",
            target=item,
            approval_status=status,
            approved_by=approved_by,
        )

    def log_error(self, component: str, error_msg: str, action: str = ""):
        """Log an error event."""
        return self.log(
            action_type=f"{component}_error",
            actor=component,
            target=action,
            error=error_msg,
        )

    def log_system(self, action_type: str, detail: str):
        """Log a system event (start, stop, restart, etc.)."""
        return self.log(
            action_type=action_type,
            actor="system",
            target="ai_employee",
            params={"detail": detail},
        )

    def get_logs(self, days: int = 1) -> list[dict]:
        """Retrieve log entries for the specified number of days."""
        from datetime import timedelta
        entries = []
        for i in range(days):
            day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            log_file = self.logs_dir / f"{day}.json"
            if not log_file.exists():
                continue
            try:
                data = json.loads(log_file.read_text(encoding="utf-8"))
                entries.extend(data)
            except (json.JSONDecodeError, OSError):
                continue
        return entries

    def get_error_count(self, days: int = 1) -> int:
        """Count errors in the specified period."""
        return sum(1 for e in self.get_logs(days) if e.get("result") == "failed" or "error" in e.get("action_type", ""))

    def _write_entry(self, entry: dict):
        """Append entry to today's log file."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{today}.json"
        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                logs = []
        logs.append(entry)
        log_file.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")


# CLI for manual testing
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AI Employee Audit Logger")
    parser.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))
    parser.add_argument("--action", type=str, default="test_log")
    parser.add_argument("--actor", type=str, default="manual")
    parser.add_argument("--target", type=str, default="test")
    parser.add_argument("--days", type=int, default=1, help="Days to show logs for")
    parser.add_argument("--show-logs", action="store_true", help="Display recent logs")
    args = parser.parse_args()

    al = AuditLogger(Path(args.vault_path))

    if args.show_logs:
        logs = al.get_logs(args.days)
        print(json.dumps(logs, indent=2))
    else:
        al.log(args.action, actor=args.actor, target=args.target)
