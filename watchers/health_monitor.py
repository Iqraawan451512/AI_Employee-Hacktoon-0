"""
Health Monitor for AI Employee (Platinum Tier).

Checks the health of all cloud-side services and writes status signals
to Updates/HEALTH_<timestamp>.md for the dashboard merger.

Checks:
  - Cloud orchestrator process
  - Gmail watcher process
  - Vault sync (last sync age)
  - Odoo HTTP endpoint
  - Disk usage

Runs as a systemd service, checking every 60 seconds.

Usage:
    uv run python health_monitor.py --vault-path ../AI_Employee_Vault
    uv run python health_monitor.py --vault-path ../AI_Employee_Vault --once
    uv run python health_monitor.py --vault-path ../AI_Employee_Vault --interval 60
"""

import argparse
import logging
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

DEFAULT_VAULT = Path(__file__).parent.parent / "AI_Employee_Vault"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("HealthMonitor")


class HealthCheck:
    """Individual health check result."""

    def __init__(self, name: str, status: str, detail: str = ""):
        self.name = name
        self.status = status  # "ok", "warn", "error"
        self.detail = detail


class HealthMonitor:
    """Monitors health of all cloud-side AI Employee services."""

    def __init__(self, vault_path: Path, odoo_url: str = "http://localhost:8069"):
        self.vault_path = vault_path
        self.odoo_url = odoo_url
        self.updates_dir = vault_path / "Updates"
        self.updates_dir.mkdir(parents=True, exist_ok=True)

    def check_all(self) -> list[HealthCheck]:
        """Run all health checks and return results."""
        checks = []
        checks.append(self._check_process("cloud_orchestrator", "cloud_orchestrator.py"))
        checks.append(self._check_process("gmail_watcher", "gmail_watcher.py"))
        checks.append(self._check_vault_sync())
        checks.append(self._check_odoo())
        checks.append(self._check_disk_usage())
        return checks

    def _check_process(self, name: str, script_name: str) -> HealthCheck:
        """Check if a Python process is running."""
        try:
            result = subprocess.run(
                ["pgrep", "-f", script_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split("\n")
                return HealthCheck(name, "ok", f"Running (PID: {', '.join(pids)})")
            else:
                return HealthCheck(name, "error", "Process not running")
        except FileNotFoundError:
            # pgrep not available (e.g., Windows) — try tasklist
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq python*"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if script_name.lower() in result.stdout.lower():
                    return HealthCheck(name, "ok", "Running")
                else:
                    return HealthCheck(name, "warn", "Cannot verify (tasklist fallback)")
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return HealthCheck(name, "warn", "Cannot check process status")
        except subprocess.TimeoutExpired:
            return HealthCheck(name, "warn", "Process check timed out")

    def _check_vault_sync(self) -> HealthCheck:
        """Check vault sync by looking at last sync signal age."""
        updates_dir = self.vault_path / "Updates"
        if not updates_dir.exists():
            return HealthCheck("vault_sync", "warn", "Updates/ directory missing")

        sync_files = sorted(updates_dir.glob("SYNC_*.md"), reverse=True)
        if not sync_files:
            # No sync signals yet — check git log instead
            try:
                result = subprocess.run(
                    ["git", "log", "-1", "--format=%ci"],
                    cwd=str(self.vault_path),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return HealthCheck("vault_sync", "ok", f"Last commit: {result.stdout.strip()}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            return HealthCheck("vault_sync", "warn", "No sync signals found")

        # Check age of most recent sync signal
        latest = sync_files[0]
        age_seconds = time.time() - latest.stat().st_mtime
        if age_seconds < 120:
            return HealthCheck("vault_sync", "ok", f"Last sync {int(age_seconds)}s ago")
        elif age_seconds < 300:
            return HealthCheck("vault_sync", "warn", f"Last sync {int(age_seconds)}s ago (>2min)")
        else:
            return HealthCheck("vault_sync", "error", f"Last sync {int(age_seconds)}s ago (stale)")

    def _check_odoo(self) -> HealthCheck:
        """Check if Odoo is responding on HTTP."""
        try:
            response = urlopen(self.odoo_url, timeout=5)
            if response.status == 200:
                return HealthCheck("odoo", "ok", f"HTTP 200 at {self.odoo_url}")
            else:
                return HealthCheck("odoo", "warn", f"HTTP {response.status}")
        except URLError as e:
            return HealthCheck("odoo", "error", f"Unreachable: {e.reason}")
        except Exception as e:
            return HealthCheck("odoo", "error", f"Error: {e}")

    def _check_disk_usage(self) -> HealthCheck:
        """Check disk usage on the vault partition."""
        try:
            usage = shutil.disk_usage(str(self.vault_path))
            percent_used = (usage.used / usage.total) * 100
            free_gb = usage.free / (1024 ** 3)

            if percent_used > 90:
                return HealthCheck("disk", "error", f"{percent_used:.1f}% used ({free_gb:.1f}GB free)")
            elif percent_used > 80:
                return HealthCheck("disk", "warn", f"{percent_used:.1f}% used ({free_gb:.1f}GB free)")
            else:
                return HealthCheck("disk", "ok", f"{percent_used:.1f}% used ({free_gb:.1f}GB free)")
        except OSError as e:
            return HealthCheck("disk", "error", f"Cannot check: {e}")

    def write_health_signal(self, checks: list[HealthCheck]):
        """Write health status to Updates/HEALTH_<timestamp>.md."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        overall = "ok"
        for c in checks:
            if c.status == "error":
                overall = "error"
                break
            elif c.status == "warn" and overall != "error":
                overall = "warn"

        status_emoji = {"ok": "GREEN", "warn": "YELLOW", "error": "RED"}

        lines = [
            "---",
            "type: health_status",
            "agent: cloud",
            f"action: health_{overall}",
            f"timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
            f"overall: {overall}",
            "---",
            "",
            f"# Health Check [{status_emoji.get(overall, 'UNKNOWN')}]",
            "",
            "| Service | Status | Detail |",
            "|---------|--------|--------|",
        ]

        for c in checks:
            icon = {"ok": "OK", "warn": "WARN", "error": "ERR"}
            lines.append(f"| {c.name} | {icon.get(c.status, '?')} | {c.detail} |")

        lines.append("")
        lines.append(f"*Checked at {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}*")

        signal_file = self.updates_dir / f"HEALTH_{ts}.md"
        signal_file.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Health signal written: {signal_file.name} (overall: {overall})")

    def run_once(self) -> list[HealthCheck]:
        """Single health check cycle."""
        logger.info("Running health checks...")
        checks = self.check_all()
        self.write_health_signal(checks)

        for c in checks:
            level = {"ok": "INFO", "warn": "WARNING", "error": "ERROR"}
            logger.log(
                getattr(logging, level.get(c.status, "INFO")),
                f"  {c.name}: [{c.status.upper()}] {c.detail}",
            )

        return checks

    def run_loop(self, interval: int = 60):
        """Continuous health monitoring loop."""
        logger.info(f"Health monitor starting (interval: {interval}s)")
        try:
            while True:
                self.run_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Health monitor stopped.")


def main():
    parser = argparse.ArgumentParser(description="AI Employee Health Monitor")
    parser.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds")
    parser.add_argument("--odoo-url", type=str, default="http://localhost:8069",
                        help="Odoo HTTP URL for health checks")
    args = parser.parse_args()

    monitor = HealthMonitor(Path(args.vault_path), odoo_url=args.odoo_url)
    if args.once:
        monitor.run_once()
    else:
        monitor.run_loop(args.interval)


if __name__ == "__main__":
    main()
