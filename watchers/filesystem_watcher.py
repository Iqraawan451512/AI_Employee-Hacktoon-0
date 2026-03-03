"""
File System Watcher for AI Employee.

Monitors the /Inbox folder for new files and creates action entries
in /Needs_Action with metadata for Claude to process.

Usage:
    uv run python filesystem_watcher.py [--vault-path PATH]
"""

import argparse
import json
import logging
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Default vault path (relative to project root)
DEFAULT_VAULT = Path(__file__).parent.parent / "AI_Employee_Vault"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("FileSystemWatcher")


class InboxHandler(FileSystemEventHandler):
    """Handles new files dropped into the Inbox folder."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.needs_action = vault_path / "Needs_Action"
        self.logs_dir = vault_path / "Logs"
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._processed = set()

    def _should_skip(self, path: Path) -> bool:
        """Check if a file should be skipped."""
        name = path.name
        if name.startswith(".") or name.startswith("~"):
            return True
        if ".tmp." in name:
            return True
        if not path.exists():
            return True
        if str(path) in self._processed:
            return True
        return False

    def on_created(self, event):
        self._handle(event)

    def on_moved(self, event):
        """Handle file moves/renames (Windows writes often use temp+rename)."""
        if event.is_directory:
            return
        dest = Path(event.dest_path)
        if self._should_skip(dest):
            return
        logger.info(f"New file detected (moved): {dest.name}")
        try:
            self._processed.add(str(dest))
            self._process_file(dest)
        except Exception as e:
            logger.error(f"Error processing {dest.name}: {e}")

    def _handle(self, event):
        if event.is_directory:
            return

        source = Path(event.src_path)

        if self._should_skip(source):
            return

        logger.info(f"New file detected: {source.name}")

        try:
            self._processed.add(str(source))
            self._process_file(source)
        except Exception as e:
            logger.error(f"Error processing {source.name}: {e}")

    def _process_file(self, source: Path):
        """Process a new file: copy to Needs_Action and create metadata."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        date_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = source.stem.replace(" ", "_")

        # Copy the file to Needs_Action
        dest_name = f"FILE_{date_prefix}_{source.name}"
        dest = self.needs_action / dest_name
        shutil.copy2(source, dest)

        # Create metadata markdown file
        meta_path = self.needs_action / f"FILE_{date_prefix}_{safe_name}.md"
        file_size = source.stat().st_size
        file_ext = source.suffix.lower()

        # Determine file type category
        category = self._categorize_file(file_ext)

        metadata_content = f"""---
type: file_drop
original_name: {source.name}
size: {file_size}
extension: {file_ext}
category: {category}
received: {timestamp}
priority: medium
status: pending
---

## File Drop Details
- **File**: {source.name}
- **Size**: {self._format_size(file_size)}
- **Type**: {category} ({file_ext})
- **Received**: {timestamp}

## Suggested Actions
- [ ] Review file contents
- [ ] Categorize and process
- [ ] Move to appropriate location
- [ ] Update Dashboard
"""
        meta_path.write_text(metadata_content, encoding="utf-8")

        # Log the action
        self._log_action(source.name, timestamp)

        logger.info(f"Action file created: {meta_path.name}")

    def _categorize_file(self, ext: str) -> str:
        categories = {
            "document": [".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt"],
            "spreadsheet": [".csv", ".xlsx", ".xls", ".ods"],
            "image": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp"],
            "data": [".json", ".xml", ".yaml", ".yml", ".toml"],
            "code": [".py", ".js", ".ts", ".html", ".css", ".sh", ".bat"],
            "archive": [".zip", ".tar", ".gz", ".rar", ".7z"],
        }
        for category, extensions in categories.items():
            if ext in extensions:
                return category
        return "other"

    def _format_size(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _log_action(self, filename: str, timestamp: str):
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{today}.json"

        log_entry = {
            "timestamp": timestamp,
            "action_type": "file_drop_detected",
            "actor": "filesystem_watcher",
            "target": filename,
            "parameters": {"source": "Inbox"},
            "result": "action_file_created",
        }

        # Append to daily log
        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logs = []

        logs.append(log_entry)
        log_file.write_text(
            json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def main():
    parser = argparse.ArgumentParser(description="AI Employee File System Watcher")
    parser.add_argument(
        "--vault-path",
        type=str,
        default=str(DEFAULT_VAULT),
        help="Path to the Obsidian vault",
    )
    args = parser.parse_args()

    vault_path = Path(args.vault_path)
    inbox = vault_path / "Inbox"
    inbox.mkdir(parents=True, exist_ok=True)

    logger.info(f"Vault path: {vault_path}")
    logger.info(f"Watching: {inbox}")
    logger.info("Drop files into the Inbox folder to trigger processing.")
    logger.info("Press Ctrl+C to stop.\n")

    handler = InboxHandler(vault_path)
    observer = Observer()
    observer.schedule(handler, str(inbox), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping file watcher...")
        observer.stop()

    observer.join()
    logger.info("File watcher stopped.")


if __name__ == "__main__":
    main()
