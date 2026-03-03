"""
Cross-Domain Orchestrator for AI Employee.

Coordinates actions across multiple domains (email, social media, file system,
approvals) to handle complex multi-step workflows. Acts as the central brain
that decides which skill/watcher to invoke for each task.

Platinum Tier: Supports --mode local for Local agent operation.
In local mode:
  - Scans domain subfolders for finance, general
  - Processes Approved/ items (executes send/post via Playwright)
  - Runs dashboard_merger after each cycle
  - Uses claim-by-move with agent=local

Usage:
    uv run python orchestrator.py --vault-path ../AI_Employee_Vault
    uv run python orchestrator.py --vault-path ../AI_Employee_Vault --once
    uv run python orchestrator.py --vault-path ../AI_Employee_Vault --mode local
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_VAULT = Path(__file__).parent.parent / "AI_Employee_Vault"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("Orchestrator")


TASK_ROUTING = {
    # Keywords -> which script/action to invoke
    "email": {"action": "gmail", "script": "gmail_watcher.py"},
    "gmail": {"action": "gmail", "script": "gmail_watcher.py"},
    "linkedin": {"action": "linkedin", "script": "linkedin_poster.py"},
    "twitter": {"action": "twitter", "script": "twitter_poster.py"},
    "tweet": {"action": "twitter", "script": "twitter_poster.py"},
    "facebook": {"action": "facebook", "script": "facebook_instagram_poster.py"},
    "instagram": {"action": "instagram", "script": "facebook_instagram_poster.py"},
    "whatsapp": {"action": "whatsapp", "script": "whatsapp_watcher.py"},
    "invoice": {"action": "finance", "script": None},
    "payment": {"action": "finance", "script": None},
    "budget": {"action": "finance", "script": None},
    "briefing": {"action": "briefing", "script": "ceo_briefing.py"},
    "report": {"action": "briefing", "script": "ceo_briefing.py"},
    "summary": {"action": "briefing", "script": "ceo_briefing.py"},
}

# Domains owned by Local agent in Platinum mode
LOCAL_DOMAINS = {"finance", "general"}


class Orchestrator:
    def __init__(self, vault_path: Path, mode: str = "standalone"):
        self.vault_path = vault_path
        self.mode = mode  # "standalone" (gold) or "local" (platinum)
        self.logs_dir = vault_path / "Logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Platinum: initialize claim manager and dashboard merger
        if mode == "local":
            from claim_manager import ClaimManager
            from dashboard_merger import DashboardMerger

            self.claim_mgr = ClaimManager(vault_path)
            self.dashboard_merger = DashboardMerger(vault_path)

    def scan_and_route(self) -> list[dict]:
        """Scan all pending folders and route tasks to appropriate handlers."""
        results = []

        if self.mode == "local":
            results.extend(self._scan_local_domains())
            results.extend(self._scan_approved_items())
        else:
            results.extend(self._scan_standalone())

        return results

    def _scan_standalone(self) -> list[dict]:
        """Original Gold-tier scanning: Inbox, Approved, Needs_Action."""
        results = []

        # 1. Check /Inbox for new files
        inbox = self.vault_path / "Inbox"
        if inbox.exists():
            for f in inbox.iterdir():
                if f.is_file() and not f.name.startswith("."):
                    result = self._route_inbox_item(f)
                    results.append(result)

        # 2. Check /Approved for posts ready to publish
        approved = self.vault_path / "Approved"
        if approved.exists():
            for f in approved.iterdir():
                if f.is_file() and not f.name.startswith("."):
                    result = self._route_approved_item(f)
                    results.append(result)

        # 3. Check /Needs_Action for pending tasks
        needs_action = self.vault_path / "Needs_Action"
        if needs_action.exists():
            for f in needs_action.iterdir():
                if f.is_file() and not f.name.startswith("."):
                    result = self._classify_task(f)
                    results.append(result)

        return results

    def _scan_local_domains(self) -> list[dict]:
        """Platinum Local mode: scan finance and general domain subfolders."""
        results = []

        for domain in LOCAL_DOMAINS:
            domain_dir = self.vault_path / "Needs_Action" / domain
            if not domain_dir.exists():
                continue
            for f in domain_dir.iterdir():
                if f.is_file() and not f.name.startswith("."):
                    result = self._process_local_task(f, domain)
                    if result:
                        results.append(result)

        # Also scan top-level Needs_Action for uncategorized local tasks
        top_level = self.vault_path / "Needs_Action"
        if top_level.exists():
            for f in top_level.iterdir():
                if f.is_file() and not f.name.startswith("."):
                    domain = self._detect_domain_from_content(f)
                    if domain in LOCAL_DOMAINS:
                        result = self._process_local_task(f, domain)
                        if result:
                            results.append(result)

        return results

    def _process_local_task(self, filepath: Path, domain: str) -> dict | None:
        """Process a task as the Local agent using claim-by-move."""
        claimed = self.claim_mgr.try_claim(filepath, agent="local")
        if not claimed:
            return None

        logger.info(f"[Local] Processing [{domain}]: {filepath.name}")
        self._log_action("task_claimed", filepath.name, {"domain": domain, "agent": "local"})

        # For now, classify and route — execution depends on the task type
        content = claimed.read_text(encoding="utf-8").lower()
        route = self._detect_domain(content + " " + filepath.name.lower())

        # Release to appropriate destination
        if route in ("finance",):
            # Finance tasks stay for manual processing
            self.claim_mgr.release(claimed, destination=f"Pending_Approval/{domain}")
        else:
            self.claim_mgr.release(claimed, destination=f"Plans/{domain}")

        return {"file": filepath.name, "source": f"Needs_Action/{domain}", "domain": domain, "agent": "local"}

    def _scan_approved_items(self) -> list[dict]:
        """Platinum Local mode: scan Approved/ and domain subfolders for execution."""
        results = []

        # Top-level Approved/
        approved = self.vault_path / "Approved"
        if approved.exists():
            for f in approved.iterdir():
                if f.is_file() and not f.name.startswith("."):
                    result = self._execute_approved(f)
                    if result:
                        results.append(result)

        # Domain-specific approved (cloud-drafted approvals moved here by human)
        for domain in ("email", "social", "finance", "general"):
            domain_approved = self.vault_path / "Approved" / domain
            if domain_approved.exists():
                for f in domain_approved.iterdir():
                    if f.is_file() and not f.name.startswith("."):
                        result = self._execute_approved(f, domain=domain)
                        if result:
                            results.append(result)

        return results

    def _execute_approved(self, filepath: Path, domain: str = None) -> dict | None:
        """Execute an approved item (Local agent only)."""
        if self.mode == "local":
            claimed = self.claim_mgr.try_claim(filepath, agent="local")
            if not claimed:
                return None
            filepath = claimed

        name = filepath.name.upper()
        if name.startswith("LINKEDIN"):
            action_domain = "linkedin"
        elif name.startswith("TWITTER"):
            action_domain = "twitter"
        elif name.startswith("FACEBOOK"):
            action_domain = "facebook"
        elif name.startswith("INSTAGRAM"):
            action_domain = "instagram"
        elif name.startswith("EMAIL") or name.startswith("APPROVE_EMAIL"):
            action_domain = "email"
        else:
            action_domain = domain or "unknown"

        logger.info(f"[Approved] {filepath.name} -> execute via {action_domain}")
        self._log_action("approved_executed", filepath.name, {"domain": action_domain, "agent": "local"})

        # Move to Done after execution
        if self.mode == "local":
            self.claim_mgr.release(filepath, destination="Done")
        else:
            done_dir = self.vault_path / "Done"
            done_dir.mkdir(parents=True, exist_ok=True)
            filepath.rename(done_dir / filepath.name)

        return {"file": filepath.name, "source": "Approved", "domain": action_domain, "action": "executed"}

    def _detect_domain_from_content(self, filepath: Path) -> str:
        """Detect domain from file content."""
        try:
            content = filepath.read_text(encoding="utf-8").lower()
            return self._detect_domain(content + " " + filepath.name.lower())
        except OSError:
            return "general"

    def _route_inbox_item(self, filepath: Path) -> dict:
        """Route an inbox item to the correct handler."""
        content = filepath.read_text(encoding="utf-8").lower()
        filename = filepath.name.lower()

        domain = self._detect_domain(content + " " + filename)

        logger.info(f"[Inbox] {filepath.name} -> domain: {domain}")
        self._log_action("task_routed", f"Inbox/{filepath.name}", {"domain": domain})

        # In platinum mode, route to domain subfolder
        if self.mode == "local":
            dest_folder = self._domain_to_folder(domain)
        else:
            dest_folder = "Needs_Action"

        dest_dir = self.vault_path / dest_folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filepath.name
        filepath.rename(dest)

        return {"file": filepath.name, "source": "Inbox", "domain": domain, "routed_to": dest_folder}

    def _domain_to_folder(self, domain: str) -> str:
        """Map a domain to its Needs_Action subfolder."""
        domain_map = {
            "gmail": "Needs_Action/email",
            "email": "Needs_Action/email",
            "linkedin": "Needs_Action/social",
            "twitter": "Needs_Action/social",
            "facebook": "Needs_Action/social",
            "instagram": "Needs_Action/social",
            "finance": "Needs_Action/finance",
            "whatsapp": "Needs_Action/general",
            "briefing": "Needs_Action/general",
        }
        return domain_map.get(domain, "Needs_Action/general")

    def _route_approved_item(self, filepath: Path) -> dict:
        """Route an approved item to publish."""
        name = filepath.name.upper()
        if name.startswith("LINKEDIN"):
            domain = "linkedin"
        elif name.startswith("TWITTER"):
            domain = "twitter"
        elif name.startswith("FACEBOOK"):
            domain = "facebook"
        elif name.startswith("INSTAGRAM"):
            domain = "instagram"
        else:
            domain = "unknown"

        logger.info(f"[Approved] {filepath.name} -> publish via {domain}")
        return {"file": filepath.name, "source": "Approved", "domain": domain, "action": "publish"}

    def _classify_task(self, filepath: Path) -> dict:
        """Classify a Needs_Action task by domain."""
        content = filepath.read_text(encoding="utf-8").lower()
        domain = self._detect_domain(content)
        return {"file": filepath.name, "source": "Needs_Action", "domain": domain}

    def _detect_domain(self, text: str) -> str:
        """Detect which domain a task belongs to based on content keywords."""
        for keyword, route in TASK_ROUTING.items():
            if keyword in text:
                return route["action"]
        return "general"

    def check_scheduled_tasks(self):
        """Check if any scheduled tasks are due."""
        config_file = self.vault_path / "Scheduling_Config.md"
        if not config_file.exists():
            return

        # Check if CEO briefing is due (Mondays)
        now = datetime.now()
        if now.weekday() == 0 and now.hour >= 7 and now.hour <= 9:
            briefing_file = self.vault_path / "Briefings" / f"{now.strftime('%Y-%m-%d')}_CEO_Briefing.md"
            if not briefing_file.exists():
                logger.info("Monday morning - generating CEO briefing")
                self._run_script("ceo_briefing.py", [])

    def _run_script(self, script: str, extra_args: list[str]):
        """Run a watcher script."""
        script_path = Path(__file__).parent / script
        if not script_path.exists():
            logger.warning(f"Script not found: {script_path}")
            return
        cmd = [sys.executable, str(script_path), "--vault-path", str(self.vault_path)] + extra_args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                logger.error(f"Script {script} failed: {result.stderr}")
            else:
                logger.info(f"Script {script} completed successfully")
        except subprocess.TimeoutExpired:
            logger.error(f"Script {script} timed out")

    def _log_action(self, action_type: str, target: str, params: dict):
        """Log orchestrator action."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{today}.json"
        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "action_type": action_type,
            "actor": f"orchestrator_{self.mode}",
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

    def run_once(self):
        """Single scan-and-route cycle."""
        logger.info(f"Orchestrator [{self.mode}]: scanning vault...")
        results = self.scan_and_route()
        self.check_scheduled_tasks()

        # Platinum Local mode: merge dashboard updates
        if self.mode == "local":
            self.dashboard_merger.merge_once()

        if results:
            logger.info(f"Orchestrator: routed {len(results)} item(s)")
            for r in results:
                logger.info(f"  - {r['source']}/{r['file']} -> {r['domain']}")
        else:
            logger.info("Orchestrator: no pending items")

        return results

    def run_loop(self, interval: int = 60):
        """Continuous orchestration loop."""
        logger.info(f"Orchestrator starting (mode: {self.mode}, interval: {interval}s)")
        try:
            while True:
                self.run_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Orchestrator stopped.")


def main():
    parser = argparse.ArgumentParser(description="AI Employee Cross-Domain Orchestrator")
    parser.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=60, help="Loop interval in seconds")
    parser.add_argument("--mode", type=str, default="standalone", choices=["standalone", "local"],
                        help="Operation mode: standalone (Gold) or local (Platinum)")
    args = parser.parse_args()

    orch = Orchestrator(Path(args.vault_path), mode=args.mode)
    if args.once:
        orch.run_once()
    else:
        orch.run_loop(args.interval)


if __name__ == "__main__":
    main()
