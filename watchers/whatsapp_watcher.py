"""
WhatsApp Watcher for AI Employee.

Monitors WhatsApp Web for new unread messages containing business keywords
using Playwright browser automation with a persistent session.

First run requires --headed mode to scan the QR code. After login the session
is saved and subsequent runs can be headless.

Usage:
    # First run (headed - scan QR code)
    uv run python whatsapp_watcher.py --vault-path ../AI_Employee_Vault --session-path ./whatsapp_session --headed

    # Normal headless run
    uv run python whatsapp_watcher.py --vault-path ../AI_Employee_Vault --session-path ./whatsapp_session

    # Custom interval and keywords
    uv run python whatsapp_watcher.py --vault-path ../AI_Employee_Vault --interval 60 --extra-keywords "project,meeting"
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from base_watcher import BaseWatcher

DEFAULT_VAULT = Path(__file__).parent.parent / "AI_Employee_Vault"
DEFAULT_SESSION = Path(__file__).parent / "whatsapp_session"

# Keywords from Company Handbook
URGENT_KEYWORDS = ["urgent", "asap", "emergency", "critical"]
FINANCIAL_KEYWORDS = ["invoice", "payment", "price", "pricing", "quote", "budget", "overdue"]
ACTION_KEYWORDS = ["help", "need", "request", "order", "deadline"]
ALL_KEYWORDS = URGENT_KEYWORDS + FINANCIAL_KEYWORDS + ACTION_KEYWORDS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("WhatsAppWatcher")


class WhatsAppWatcher(BaseWatcher):
    """Watches WhatsApp Web for unread messages with business keywords."""

    def __init__(
        self,
        vault_path: str,
        session_path: str,
        headed: bool = False,
        check_interval: int = 30,
        extra_keywords: list[str] | None = None,
    ):
        super().__init__(vault_path, check_interval)
        self.session_path = Path(session_path)
        self.session_path.mkdir(parents=True, exist_ok=True)
        self.headed = headed
        self.keywords = ALL_KEYWORDS + (extra_keywords or [])
        self.logs_dir = self.vault_path / "Logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Track processed messages to avoid duplicates
        self._processed_hashes: set[str] = set()
        self._load_processed()

        # Playwright objects (created in run())
        self._playwright = None
        self._browser = None
        self._page = None

    # ── State persistence ──────────────────────────

    def _state_file(self) -> Path:
        return self.vault_path / ".whatsapp_processed.json"

    def _load_processed(self):
        sf = self._state_file()
        if sf.exists():
            try:
                data = json.loads(sf.read_text(encoding="utf-8"))
                self._processed_hashes = set(data.get("hashes", []))
                logger.info(f"Loaded {len(self._processed_hashes)} previously seen messages")
            except (json.JSONDecodeError, KeyError):
                pass

    def _save_processed(self):
        # Keep last 500 hashes
        hashes = list(self._processed_hashes)[-500:]
        self._state_file().write_text(
            json.dumps({"hashes": hashes, "updated": datetime.now(timezone.utc).isoformat()}),
            encoding="utf-8",
        )

    @staticmethod
    def _hash_msg(contact: str, text: str) -> str:
        """Simple dedup hash from contact + first 80 chars of message."""
        return f"{contact}::{text[:80]}"

    # ── Browser lifecycle ──────────────────────────

    def _ensure_browser(self):
        """Launch (or reuse) the persistent Chromium context."""
        if self._page is not None:
            return

        logger.info("Launching browser with persistent session...")
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.session_path),
            headless=not self.headed,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        self._page = self._browser.pages[0] if self._browser.pages else self._browser.new_page()

    def _close_browser(self):
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
        self._browser = None
        self._page = None
        self._playwright = None

    # ── WhatsApp Web interaction ───────────────────

    def _navigate_to_whatsapp(self):
        """Navigate to WhatsApp Web and wait for the chat list to load."""
        page = self._page
        current_url = page.url or ""

        if "web.whatsapp.com" not in current_url:
            logger.info("Navigating to WhatsApp Web...")
            page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=60000)

        # Wait for either the chat list (logged in) or the QR code
        try:
            page.wait_for_selector(
                '[aria-label="Chat list"], [aria-label="Chats"], canvas[aria-label="Scan this QR code to link a device!"], [data-testid="qrcode"]',
                timeout=30000,
            )
        except PlaywrightTimeout:
            logger.warning("WhatsApp Web did not load in time. Retrying next cycle.")
            return False

        # Check if QR code is showing (not logged in)
        qr = page.query_selector('canvas[aria-label="Scan this QR code to link a device!"]') or page.query_selector('[data-testid="qrcode"]')
        if qr:
            if self.headed:
                logger.info("QR code detected. Please scan it with your phone.")
                logger.info("Waiting up to 60 seconds for login...")
                try:
                    page.wait_for_selector(
                        '[aria-label="Chat list"], [aria-label="Chats"]',
                        timeout=60000,
                    )
                    logger.info("Login successful!")
                except PlaywrightTimeout:
                    logger.error("Login timed out. Please try again.")
                    return False
            else:
                logger.error(
                    "QR code detected but running headless. "
                    "Run with --headed first to scan the QR code."
                )
                return False

        return True

    def _scrape_unread_chats(self) -> list[dict]:
        """Scrape unread chat previews from the sidebar."""
        page = self._page
        messages: list[dict] = []

        try:
            # WhatsApp shows unread counts as badge spans inside each chat row
            # We look for chat list items that have an unread badge
            chat_rows = page.query_selector_all('[aria-label="Chat list"] > div > div, [data-testid="cell-frame-container"]')

            if not chat_rows:
                # Fallback: try a broader selector
                chat_rows = page.query_selector_all('div[role="listitem"], div[role="row"]')

            for row in chat_rows:
                try:
                    # Check for unread indicator (green badge with number)
                    unread_badge = row.query_selector('[data-testid="icon-unread-count"], span[aria-label*="unread"]')
                    if not unread_badge:
                        # Also check for a span containing just a number (unread count)
                        badges = row.query_selector_all("span.aumms1qt, span[data-icon='unread-count']")
                        if not badges:
                            continue

                    # Extract contact name
                    title_el = row.query_selector("span[title], span[dir='auto']")
                    contact = title_el.get_attribute("title") if title_el else ""
                    if not contact:
                        contact = title_el.inner_text().strip() if title_el else "Unknown"

                    # Extract last message preview
                    preview_el = row.query_selector("span.ggj6brxn, span[title][dir='ltr'], div[role='gridcell'] span[title]")
                    if not preview_el:
                        # Broader fallback
                        spans = row.query_selector_all("span[title]")
                        preview_el = spans[-1] if len(spans) > 1 else None

                    preview_text = ""
                    if preview_el:
                        preview_text = preview_el.get_attribute("title") or preview_el.inner_text()
                    if not preview_text:
                        preview_text = row.inner_text()

                    messages.append({
                        "contact": contact.strip(),
                        "preview": preview_text.strip(),
                    })

                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Error scraping chat list: {e}")

        return messages

    def _open_chat_and_read(self, contact_name: str) -> list[dict]:
        """Click into a chat and read the last few messages."""
        page = self._page
        messages: list[dict] = []

        try:
            # Click on the chat with this contact name
            chat_el = page.query_selector(f'span[title="{contact_name}"]')
            if not chat_el:
                return messages
            chat_el.click()
            page.wait_for_timeout(1500)

            # Read visible messages in the conversation pane
            msg_elements = page.query_selector_all(
                'div.message-in div[data-pre-plain-text], '
                'div.message-in div.copyable-text'
            )

            # Fallback selector
            if not msg_elements:
                msg_elements = page.query_selector_all('[data-testid="msg-container"]')

            for el in msg_elements[-10:]:  # last 10 messages
                meta = el.get_attribute("data-pre-plain-text") or ""
                text = el.inner_text().strip()
                messages.append({
                    "contact": contact_name,
                    "meta": meta,
                    "text": text,
                })

        except Exception as e:
            logger.debug(f"Error reading chat for {contact_name}: {e}")

        return messages

    # ── BaseWatcher interface ──────────────────────

    def check_for_updates(self) -> list:
        """Check WhatsApp Web for new unread messages with matching keywords."""
        self._ensure_browser()

        if not self._navigate_to_whatsapp():
            return []

        # Scrape unread chats from the sidebar
        unread_chats = self._scrape_unread_chats()
        if not unread_chats:
            return []

        logger.info(f"Found {len(unread_chats)} unread chat(s), checking for keywords...")

        matched: list[dict] = []
        for chat in unread_chats:
            combined = f"{chat['preview']}".lower()

            # Check if any keyword matches
            found_keywords = [kw for kw in self.keywords if kw in combined]
            if not found_keywords:
                continue

            # Dedup
            msg_hash = self._hash_msg(chat["contact"], chat["preview"])
            if msg_hash in self._processed_hashes:
                continue

            # Optionally open the chat and read more context
            full_messages = self._open_chat_and_read(chat["contact"])
            last_messages_text = ""
            if full_messages:
                last_messages_text = "\n".join(
                    f"- {m['text']}" for m in full_messages[-5:]
                )

            matched.append({
                "contact": chat["contact"],
                "preview": chat["preview"],
                "keywords": found_keywords,
                "full_messages": last_messages_text,
                "hash": msg_hash,
            })

        return matched

    def create_action_file(self, item: dict) -> Path:
        """Create an action file in /Needs_Action for a matched WhatsApp message."""
        contact = item["contact"]
        preview = item["preview"]
        keywords = item["keywords"]
        full_messages = item.get("full_messages", "")
        msg_hash = item["hash"]

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        date_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
        priority = self._assess_priority(keywords)

        safe_contact = "".join(c if c.isalnum() or c in " _-" else "_" for c in contact)[:30]
        filename = f"WHATSAPP_{date_prefix}_{safe_contact}.md"

        content = f"""---
type: whatsapp_message
from: "{contact}"
received: {timestamp}
priority: {priority}
status: pending
keywords_matched: {json.dumps(keywords)}
---

## WhatsApp Message
- **From**: {contact}
- **Time**: {datetime.now().strftime("%Y-%m-%d %H:%M")}
- **Priority**: {priority}
- **Keywords**: {", ".join(keywords)}

## Message Preview
{preview}

## Recent Messages
{full_messages if full_messages else "_Could not retrieve full conversation._"}

## Suggested Actions
- [ ] Reply to sender
- [ ] Create task based on message
- [ ] Forward to relevant team member
- [ ] Log interaction
"""

        filepath = self.needs_action / filename
        filepath.write_text(content, encoding="utf-8")

        # Mark as processed
        self._processed_hashes.add(msg_hash)
        self._save_processed()

        # Log
        self._log_action(contact, preview, priority, keywords, timestamp)

        logger.info(f"[{priority.upper()}] WhatsApp from {contact}: {preview[:60]}...")
        return filepath

    def _assess_priority(self, keywords: list[str]) -> str:
        if any(kw in URGENT_KEYWORDS for kw in keywords):
            return "critical"
        if any(kw in FINANCIAL_KEYWORDS for kw in keywords):
            return "high"
        return "medium"

    def _log_action(self, contact: str, preview: str, priority: str, keywords: list, timestamp: str):
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{today}.json"

        entry = {
            "timestamp": timestamp,
            "action_type": "whatsapp_message_detected",
            "actor": "whatsapp_watcher",
            "target": contact,
            "parameters": {
                "preview": preview[:100],
                "priority": priority,
                "keywords_matched": keywords,
                "source": "WhatsApp",
            },
            "result": "action_file_created",
        }

        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logs = []

        logs.append(entry)
        log_file.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Override run() to manage browser lifecycle ─

    def run(self):
        """Main loop with browser lifecycle management."""
        self.logger.info(f"Starting {self.__class__.__name__}")
        self.logger.info(f"Session path: {self.session_path}")
        self.logger.info(f"Keywords: {', '.join(self.keywords)}")
        self.logger.info(f"Poll interval: {self.check_interval}s")
        self.logger.info(f"Headless: {not self.headed}")

        try:
            while True:
                try:
                    items = self.check_for_updates()
                    for item in items:
                        path = self.create_action_file(item)
                        self.logger.info(f"Created action file: {path}")
                    if not items:
                        self.logger.debug("No new keyword-matching messages.")
                except PlaywrightTimeout as e:
                    self.logger.warning(f"Playwright timeout: {e}")
                    # Restart browser on timeout
                    self._close_browser()
                except Exception as e:
                    self.logger.error(f"Error: {e}")
                    # On repeated errors, restart browser
                    self._close_browser()

                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            self.logger.info("Stopping WhatsApp watcher...")
        finally:
            self._close_browser()
            self.logger.info("WhatsApp watcher stopped.")


def main():
    parser = argparse.ArgumentParser(description="AI Employee WhatsApp Watcher")
    parser.add_argument(
        "--vault-path",
        type=str,
        default=str(DEFAULT_VAULT),
        help="Path to the Obsidian vault",
    )
    parser.add_argument(
        "--session-path",
        type=str,
        default=str(DEFAULT_SESSION),
        help="Path for persistent browser session data",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Poll interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in visible (headed) mode for QR code scanning",
    )
    parser.add_argument(
        "--extra-keywords",
        type=str,
        default="",
        help="Comma-separated extra keywords to watch for",
    )
    args = parser.parse_args()

    extra_kw = [k.strip() for k in args.extra_keywords.split(",") if k.strip()] if args.extra_keywords else []

    watcher = WhatsAppWatcher(
        vault_path=args.vault_path,
        session_path=args.session_path,
        headed=args.headed,
        check_interval=args.interval,
        extra_keywords=extra_kw,
    )

    watcher.run()


if __name__ == "__main__":
    main()
