"""
Dashboard Merger for AI Employee (Platinum Tier).

Local-only script that reads signal files from Updates/, appends their
information to the "Recent Activity" section of Dashboard.md, and
deletes the source signal files after merging.

This ensures Dashboard.md is only written by Local (single-writer rule).

Usage:
    uv run python dashboard_merger.py --vault-path ../AI_Employee_Vault
    uv run python dashboard_merger.py --vault-path ../AI_Employee_Vault --once
"""

import argparse
import logging
import re
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
logger = logging.getLogger("DashboardMerger")


class DashboardMerger:
    """Reads Updates/ signals and merges them into Dashboard.md."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.updates_dir = vault_path / "Updates"
        self.dashboard = vault_path / "Dashboard.md"

    def merge_once(self) -> int:
        """Process all signal files in Updates/ and merge into Dashboard.md.

        Returns the number of signals processed.
        """
        if not self.updates_dir.exists():
            return 0

        signals = sorted(self.updates_dir.glob("*.md"))
        if not signals:
            return 0

        # Read each signal and build activity entries
        entries = []
        for signal_file in signals:
            if signal_file.name == ".gitkeep":
                continue
            try:
                entry = self._parse_signal(signal_file)
                if entry:
                    entries.append(entry)
                # Delete signal after reading
                signal_file.unlink()
                logger.info(f"Processed and deleted: {signal_file.name}")
            except Exception as e:
                logger.error(f"Error processing {signal_file.name}: {e}")

        if not entries:
            return 0

        # Append entries to Dashboard.md
        self._append_to_dashboard(entries)
        logger.info(f"Merged {len(entries)} update(s) into Dashboard.md")
        return len(entries)

    def _parse_signal(self, signal_file: Path) -> str | None:
        """Parse a signal file and return a dashboard activity line."""
        content = signal_file.read_text(encoding="utf-8")

        # Extract frontmatter fields
        agent = self._extract_field(content, "agent") or "unknown"
        action = self._extract_field(content, "action") or "update"
        domain = self._extract_field(content, "domain") or ""
        signal_type = self._extract_field(content, "type") or "signal"

        ts = datetime.now().strftime("%Y-%m-%d %H:%M")

        if "health" in signal_type.lower():
            return f"- [{ts}] Health check: {action} (agent: {agent})"
        elif "sync" in signal_type.lower():
            return f"- [{ts}] Vault sync: {action} (agent: {agent})"
        elif domain:
            return f"- [{ts}] [{domain}] {action} by {agent} agent"
        else:
            return f"- [{ts}] {action} (agent: {agent})"

    def _extract_field(self, content: str, field: str) -> str | None:
        """Extract a YAML frontmatter field value."""
        match = re.search(rf"^{field}:\s*(.+)$", content, re.MULTILINE)
        return match.group(1).strip() if match else None

    def _append_to_dashboard(self, entries: list[str]):
        """Append activity entries to the Recent Activity section of Dashboard.md."""
        if not self.dashboard.exists():
            logger.warning("Dashboard.md not found")
            return

        content = self.dashboard.read_text(encoding="utf-8")

        # Find "## Recent Activity" section and insert after it
        marker = "## Recent Activity"
        if marker in content:
            idx = content.index(marker) + len(marker)
            # Find the next line after the heading
            next_newline = content.index("\n", idx)
            # Insert new entries right after the heading
            new_entries = "\n".join(entries)
            content = (
                content[: next_newline + 1]
                + new_entries
                + "\n"
                + content[next_newline + 1:]
            )
        else:
            # If section doesn't exist, append it
            content += f"\n{marker}\n" + "\n".join(entries) + "\n"

        # Update last_updated in frontmatter
        content = re.sub(
            r"last_updated:\s*.+",
            f"last_updated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
            content,
        )

        self.dashboard.write_text(content, encoding="utf-8")

    def run_loop(self, interval: int = 30):
        """Continuous merge loop."""
        logger.info(f"Dashboard merger starting (interval: {interval}s)")
        try:
            while True:
                self.merge_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Dashboard merger stopped.")


def main():
    parser = argparse.ArgumentParser(description="AI Employee Dashboard Merger (Local-only)")
    parser.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=30, help="Loop interval in seconds")
    args = parser.parse_args()

    merger = DashboardMerger(Path(args.vault_path))
    if args.once:
        count = merger.merge_once()
        print(f"Merged {count} signal(s)")
    else:
        merger.run_loop(args.interval)


if __name__ == "__main__":
    main()
