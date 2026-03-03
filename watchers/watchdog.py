"""
Watchdog Process Monitor for AI Employee.

Monitors critical watcher processes and restarts them if they crash.
Logs all restarts and alerts the human via vault files.

Usage:
    uv run python watchdog.py --vault-path ../AI_Employee_Vault --config watchdog_config.json
    uv run python watchdog.py --vault-path ../AI_Employee_Vault   # uses default config
"""

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_VAULT = Path(__file__).parent.parent / "AI_Employee_Vault"
PID_DIR = Path(__file__).parent / ".pids"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("Watchdog")

# Default processes to monitor
DEFAULT_PROCESSES = {
    "filesystem_watcher": {
        "command": [sys.executable, "filesystem_watcher.py", "--vault-path", "../AI_Employee_Vault"],
        "cwd": str(Path(__file__).parent),
        "restart_delay": 5,
        "max_restarts": 10,
    },
    "gmail_watcher": {
        "command": [sys.executable, "gmail_watcher.py", "--vault-path", "../AI_Employee_Vault", "--credentials", "../credentials.json"],
        "cwd": str(Path(__file__).parent),
        "restart_delay": 10,
        "max_restarts": 5,
    },
}


class ProcessMonitor:
    def __init__(self, name: str, config: dict, vault_path: Path):
        self.name = name
        self.command = config["command"]
        self.cwd = config.get("cwd", ".")
        self.restart_delay = config.get("restart_delay", 5)
        self.max_restarts = config.get("max_restarts", 10)
        self.vault_path = vault_path
        self.logs_dir = vault_path / "Logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self.process: subprocess.Popen | None = None
        self.restart_count = 0
        self.last_start: float = 0

    def start(self) -> bool:
        if self.process and self.process.poll() is None:
            logger.info(f"[{self.name}] Already running (PID {self.process.pid})")
            return True

        if self.restart_count >= self.max_restarts:
            logger.error(f"[{self.name}] Max restarts ({self.max_restarts}) reached. Alerting human.")
            self._alert_human(f"{self.name} has crashed {self.max_restarts} times. Manual intervention required.")
            return False

        try:
            logger.info(f"[{self.name}] Starting: {' '.join(self.command)}")
            self.process = subprocess.Popen(
                self.command,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.last_start = time.time()
            self._save_pid()
            logger.info(f"[{self.name}] Started with PID {self.process.pid}")
            self._log_action("process_started", f"PID {self.process.pid}")
            return True
        except Exception as e:
            logger.error(f"[{self.name}] Failed to start: {e}")
            self._log_action("process_start_failed", str(e))
            return False

    def check(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None

    def restart(self):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

        self.restart_count += 1
        uptime = time.time() - self.last_start if self.last_start else 0
        logger.warning(f"[{self.name}] Process died after {uptime:.0f}s. Restart #{self.restart_count}")
        self._log_action("process_restarted", f"Restart #{self.restart_count}, uptime was {uptime:.0f}s")

        # Reset restart count if process ran for > 5 minutes (stable)
        if uptime > 300:
            self.restart_count = 0

        time.sleep(self.restart_delay)
        return self.start()

    def stop(self):
        if self.process and self.process.poll() is None:
            logger.info(f"[{self.name}] Stopping PID {self.process.pid}")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self._log_action("process_stopped", f"PID {self.process.pid}")

    def _save_pid(self):
        PID_DIR.mkdir(parents=True, exist_ok=True)
        pid_file = PID_DIR / f"{self.name}.pid"
        pid_file.write_text(str(self.process.pid))

    def _alert_human(self, message: str):
        alert_dir = self.vault_path / "Needs_Action"
        alert_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        alert_file = alert_dir / f"ALERT_{timestamp}_{self.name}.md"
        alert_file.write_text(f"""---
type: system_alert
source: watchdog
component: {self.name}
created: {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
priority: critical
status: pending
---

# System Alert: {self.name}

{message}

## Suggested Actions
- [ ] Check logs for error details
- [ ] Manually restart the process
- [ ] Investigate root cause
""", encoding="utf-8")

    def _log_action(self, action_type: str, detail: str):
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{today}.json"
        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "action_type": action_type,
            "actor": "watchdog",
            "target": self.name,
            "parameters": {"detail": detail},
            "result": "success",
        }
        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logs = []
        logs.append(entry)
        log_file.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="AI Employee Watchdog Process Monitor")
    parser.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))
    parser.add_argument("--config", type=str, default=None, help="JSON config file for processes")
    parser.add_argument("--check-interval", type=int, default=30, help="Health check interval (seconds)")
    args = parser.parse_args()

    vault_path = Path(args.vault_path)

    # Load config
    if args.config and Path(args.config).exists():
        processes_config = json.loads(Path(args.config).read_text())
    else:
        processes_config = DEFAULT_PROCESSES

    monitors = {name: ProcessMonitor(name, cfg, vault_path) for name, cfg in processes_config.items()}

    logger.info(f"Watchdog starting. Monitoring {len(monitors)} process(es).")
    logger.info(f"Check interval: {args.check_interval}s")

    # Start all processes
    for m in monitors.values():
        m.start()

    # Monitor loop
    try:
        while True:
            for name, monitor in monitors.items():
                if not monitor.check():
                    monitor.restart()
            time.sleep(args.check_interval)
    except KeyboardInterrupt:
        logger.info("Watchdog shutting down...")
        for m in monitors.values():
            m.stop()
        logger.info("All processes stopped.")


if __name__ == "__main__":
    main()
