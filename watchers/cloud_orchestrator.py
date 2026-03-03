"""
Cloud Orchestrator for AI Employee (Platinum Tier).

Runs on the cloud VM. Owns email and social domains ONLY.
Draft-only: creates drafts in Plans/<domain>/ and approval requests
in Pending_Approval/<domain>/. NEVER sends/posts directly.

Writes signals to Updates/ so the Local agent can merge them into Dashboard.md.
Uses claim-by-move before processing any task.
Triggers vault sync after each cycle.

Usage:
    uv run python cloud_orchestrator.py --vault-path ../AI_Employee_Vault
    uv run python cloud_orchestrator.py --vault-path ../AI_Employee_Vault --once
    uv run python cloud_orchestrator.py --vault-path ../AI_Employee_Vault --interval 60
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from claim_manager import ClaimManager

DEFAULT_VAULT = Path(__file__).parent.parent / "AI_Employee_Vault"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("CloudOrchestrator")

# Cloud only handles these domains
CLOUD_DOMAINS = {"email", "social"}

# Keywords for domain detection
DOMAIN_KEYWORDS = {
    "email": ["email", "gmail", "inbox", "reply", "forward", "subject:"],
    "social": ["linkedin", "twitter", "tweet", "facebook", "instagram", "post", "social"],
}


class CloudOrchestrator:
    """Cloud-side orchestrator — draft-only, never executes sends/posts."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.claim_mgr = ClaimManager(vault_path)
        self.logs_dir = vault_path / "Logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def scan_and_draft(self) -> list[dict]:
        """Scan cloud-owned domain folders and create drafts."""
        results = []

        for domain in CLOUD_DOMAINS:
            # Scan Needs_Action/<domain>/
            domain_dir = self.vault_path / "Needs_Action" / domain
            if not domain_dir.exists():
                continue

            for f in domain_dir.iterdir():
                if f.is_file() and not f.name.startswith("."):
                    result = self._process_task(f, domain)
                    if result:
                        results.append(result)

        # Also scan top-level Needs_Action for uncategorized items we own
        top_level = self.vault_path / "Needs_Action"
        if top_level.exists():
            for f in top_level.iterdir():
                if f.is_file() and not f.name.startswith("."):
                    domain = self._detect_domain(f)
                    if domain in CLOUD_DOMAINS:
                        result = self._process_task(f, domain)
                        if result:
                            results.append(result)

        return results

    def _process_task(self, filepath: Path, domain: str) -> dict | None:
        """Claim a task, create a draft, and request approval."""
        # Try to claim
        claimed = self.claim_mgr.try_claim(filepath, agent="cloud")
        if not claimed:
            return None  # Another agent got it

        logger.info(f"Processing [{domain}]: {filepath.name}")

        try:
            content = claimed.read_text(encoding="utf-8")

            if domain == "email":
                draft = self._draft_email_reply(content, filepath.name)
            elif domain == "social":
                draft = self._draft_social_post(content, filepath.name)
            else:
                draft = self._draft_generic(content, filepath.name)

            # Write draft to Plans/<domain>/
            plans_dir = self.vault_path / "Plans" / domain
            plans_dir.mkdir(parents=True, exist_ok=True)
            draft_file = plans_dir / f"DRAFT_{filepath.name}"
            draft_file.write_text(draft, encoding="utf-8")
            logger.info(f"Draft created: Plans/{domain}/{draft_file.name}")

            # Create approval request in Pending_Approval/<domain>/
            approval = self._create_approval_request(filepath.name, domain, draft)
            approval_dir = self.vault_path / "Pending_Approval" / domain
            approval_dir.mkdir(parents=True, exist_ok=True)
            approval_file = approval_dir / f"APPROVE_{filepath.name}"
            approval_file.write_text(approval, encoding="utf-8")
            logger.info(f"Approval request: Pending_Approval/{domain}/{approval_file.name}")

            # Release claimed file to Done
            self.claim_mgr.release(claimed, destination="Done")

            # Write update signal
            self._write_update_signal(domain, filepath.name, "drafted")

            # Log action
            self._log_action("task_drafted", filepath.name, {"domain": domain, "agent": "cloud"})

            return {
                "file": filepath.name,
                "domain": domain,
                "action": "drafted",
                "draft": draft_file.name,
                "approval": approval_file.name,
            }

        except Exception as e:
            logger.error(f"Error processing {filepath.name}: {e}")
            # Release back to Needs_Action on failure
            self.claim_mgr.release(claimed, destination=f"Needs_Action/{domain}")
            return None

    def _detect_domain(self, filepath: Path) -> str:
        """Detect domain from file content and name."""
        try:
            text = (filepath.read_text(encoding="utf-8") + " " + filepath.name).lower()
        except OSError:
            return "general"

        for domain, keywords in DOMAIN_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return domain
        return "general"

    def _draft_email_reply(self, content: str, filename: str) -> str:
        """Create an email reply draft. Cloud drafts only — never sends."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return f"""---
type: email_draft
agent: cloud
created: {ts}
source: {filename}
status: draft
---

# Email Reply Draft

**Source**: {filename}
**Drafted by**: Cloud Agent
**Status**: Awaiting local approval to send

## Original Email Summary
{content[:500]}

## Draft Reply
> [Cloud agent drafted this reply — Local agent must approve before sending]

Thank you for your email. I've reviewed the contents and will respond shortly.

## Next Steps
- [ ] Local agent reviews draft
- [ ] Human approves sending
- [ ] Local agent sends via Gmail
"""

    def _draft_social_post(self, content: str, filename: str) -> str:
        """Create a social media post draft. Cloud drafts only — never publishes."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return f"""---
type: social_draft
agent: cloud
created: {ts}
source: {filename}
status: draft
---

# Social Post Draft

**Source**: {filename}
**Drafted by**: Cloud Agent
**Status**: Awaiting local approval to publish

## Content Brief
{content[:500]}

## Draft Post
> [Cloud agent drafted this post — Local agent must approve before publishing]

[Post content to be generated by Claude based on the brief above]

## Next Steps
- [ ] Local agent reviews draft
- [ ] Human approves publishing
- [ ] Local agent publishes via Playwright MCP
"""

    def _draft_generic(self, content: str, filename: str) -> str:
        """Create a generic task draft."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return f"""---
type: task_draft
agent: cloud
created: {ts}
source: {filename}
status: draft
---

# Task Draft

**Source**: {filename}
**Drafted by**: Cloud Agent

## Content
{content[:1000]}
"""

    def _create_approval_request(self, filename: str, domain: str, draft: str) -> str:
        """Create an approval request file."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        expires = datetime.now(timezone.utc).strftime("%Y-%m-%d")  # same day
        return f"""---
type: approval_request
action: {domain}_draft
agent: cloud
created: {ts}
expires: {expires}T23:59:59Z
status: pending
priority: medium
domain: {domain}
---

# Approval Required: Cloud-Drafted {domain.title()} Action

## Source
File: `{filename}`
Drafted by: Cloud Agent

## What Will Happen
The Local agent will execute this {domain} action after your approval.

## Draft Preview
{draft[:800]}

## To Approve
Move this file to `/Approved/` folder.

## To Reject
Move this file to `/Rejected/` folder.
"""

    def _write_update_signal(self, domain: str, filename: str, action: str):
        """Write a signal to Updates/ for the dashboard merger."""
        updates_dir = self.vault_path / "Updates"
        updates_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        signal = updates_dir / f"CLOUD_{domain.upper()}_{ts}.md"
        signal.write_text(
            f"""---
type: cloud_update
agent: cloud
domain: {domain}
action: {action}
source: {filename}
timestamp: {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
---

# Cloud Update: {action.title()}

- **Domain**: {domain}
- **File**: {filename}
- **Action**: {action}
- **Agent**: Cloud
""",
            encoding="utf-8",
        )

    def _log_action(self, action_type: str, target: str, params: dict):
        """Log action to daily log file."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{today}.json"
        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "action_type": action_type,
            "actor": "cloud_orchestrator",
            "target": target,
            "parameters": params,
            "result": "success",
        }
        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                logs = []
        logs.append(entry)
        log_file.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")

    def trigger_vault_sync(self):
        """Trigger a vault sync after processing."""
        sync_script = Path(__file__).parent.parent / "scripts" / "vault_sync.py"
        if sync_script.exists():
            try:
                subprocess.run(
                    [sys.executable, str(sync_script), "--vault", str(self.vault_path),
                     "--once", "--agent", "cloud"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                logger.info("Vault sync triggered")
            except (subprocess.TimeoutExpired, OSError) as e:
                logger.error(f"Vault sync failed: {e}")

    def run_once(self):
        """Single scan-and-draft cycle."""
        logger.info("Cloud orchestrator: scanning owned domains...")
        results = self.scan_and_draft()

        if results:
            logger.info(f"Cloud orchestrator: drafted {len(results)} item(s)")
            for r in results:
                logger.info(f"  - [{r['domain']}] {r['file']} -> {r['action']}")
        else:
            logger.info("Cloud orchestrator: no pending items in owned domains")

        self.trigger_vault_sync()
        return results

    def run_loop(self, interval: int = 60):
        """Continuous cloud orchestration loop."""
        logger.info(f"Cloud orchestrator starting (interval: {interval}s)")
        logger.info(f"Owned domains: {', '.join(CLOUD_DOMAINS)}")
        try:
            while True:
                self.run_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Cloud orchestrator stopped.")


def main():
    parser = argparse.ArgumentParser(description="AI Employee Cloud Orchestrator (Platinum)")
    parser.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=60, help="Loop interval in seconds")
    args = parser.parse_args()

    orch = CloudOrchestrator(Path(args.vault_path))
    if args.once:
        orch.run_once()
    else:
        orch.run_loop(args.interval)


if __name__ == "__main__":
    main()
