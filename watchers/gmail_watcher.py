"""
Gmail Watcher for AI Employee.

Monitors Gmail for new unread/important emails and creates action items
in /Needs_Action for Claude to process.

Usage:
    # First run (interactive OAuth flow - opens browser)
    uv run python gmail_watcher.py --vault-path ../AI_Employee_Vault --credentials credentials.json

    # Subsequent runs (uses saved token)
    uv run python gmail_watcher.py --vault-path ../AI_Employee_Vault

    # Custom query and interval
    uv run python gmail_watcher.py --vault-path ../AI_Employee_Vault --query "is:unread" --interval 60
"""

import argparse
import base64
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from base_watcher import BaseWatcher

# Gmail API scopes - read-only for watching
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

DEFAULT_VAULT = Path(__file__).parent.parent / "AI_Employee_Vault"
TOKEN_FILE = Path(__file__).parent / "token.json"

# Urgent keywords from Company Handbook
URGENT_KEYWORDS = ["urgent", "asap", "emergency", "critical"]
BUSINESS_KEYWORDS = ["invoice", "payment", "overdue", "contract", "deadline", "proposal"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("GmailWatcher")


def authenticate(credentials_path: str, token_path: Path) -> Credentials:
    """Authenticate with Gmail API using OAuth2."""
    creds = None

    # Load existing token
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # Refresh or create new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired token...")
            creds.refresh(GoogleRequest())
        else:
            if not Path(credentials_path).exists():
                logger.error(
                    f"Credentials file not found: {credentials_path}\n"
                    "Download OAuth2 credentials from Google Cloud Console:\n"
                    "https://console.cloud.google.com/apis/credentials"
                )
                sys.exit(1)
            logger.info("Starting OAuth2 flow (browser will open)...")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for future runs
        token_path.write_text(creds.to_json())
        logger.info(f"Token saved to {token_path}")

    return creds


class GmailWatcher(BaseWatcher):
    """Watches Gmail for new unread important emails."""

    def __init__(self, vault_path: str, creds: Credentials, query: str, check_interval: int = 120):
        super().__init__(vault_path, check_interval)
        self.service = build("gmail", "v1", credentials=creds)
        self.query = query
        self.processed_ids: set[str] = set()
        self.logs_dir = self.vault_path / "Logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Load previously processed IDs to avoid re-processing after restart
        self._load_processed_ids()

    def _load_processed_ids(self):
        """Load processed message IDs from a state file."""
        state_file = self.vault_path / ".gmail_processed_ids.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                self.processed_ids = set(data.get("ids", []))
                logger.info(f"Loaded {len(self.processed_ids)} previously processed message IDs")
            except (json.JSONDecodeError, KeyError):
                self.processed_ids = set()

    def _save_processed_ids(self):
        """Save processed message IDs to a state file."""
        state_file = self.vault_path / ".gmail_processed_ids.json"
        # Keep only the last 1000 IDs to prevent unbounded growth
        ids_list = list(self.processed_ids)[-1000:]
        state_file.write_text(
            json.dumps({"ids": ids_list, "updated": datetime.now(timezone.utc).isoformat()}),
            encoding="utf-8",
        )

    def check_for_updates(self) -> list:
        """Query Gmail for new unread messages matching the filter."""
        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=self.query, maxResults=10)
                .execute()
            )
        except Exception as e:
            logger.error(f"Gmail API error: {e}")
            return []

        messages = results.get("messages", [])
        new_messages = [m for m in messages if m["id"] not in self.processed_ids]

        if new_messages:
            logger.info(f"Found {len(new_messages)} new message(s)")
        return new_messages

    def create_action_file(self, message: dict) -> Path:
        """Fetch full message details and create an action file in /Needs_Action."""
        msg_id = message["id"]

        # Fetch full message
        msg = (
            self.service.users()
            .messages()
            .get(userId="me", id=msg_id, format="full")
            .execute()
        )

        # Extract headers
        headers = {}
        for header in msg.get("payload", {}).get("headers", []):
            headers[header["name"].lower()] = header["value"]

        sender = headers.get("from", "Unknown")
        subject = headers.get("subject", "No Subject")
        date_str = headers.get("date", "")
        to = headers.get("to", "")
        cc = headers.get("cc", "")

        # Get email body
        body = self._extract_body(msg.get("payload", {}))
        snippet = msg.get("snippet", "")

        # Determine priority
        priority = self._assess_priority(subject, snippet, body)
        keywords_found = self._find_keywords(subject, snippet, body)

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        date_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create the action file
        content = f"""---
type: email
from: "{sender}"
subject: "{subject}"
to: "{to}"
cc: "{cc}"
received: {timestamp}
gmail_id: {msg_id}
priority: {priority}
status: pending
keywords_matched: {json.dumps(keywords_found)}
---

## Email Details
- **From**: {sender}
- **To**: {to}
- **Subject**: {subject}
- **Date**: {date_str}
- **Priority**: {priority}

## Email Content
{snippet}

## Full Body
{body[:2000] if body else "_No plain text body available._"}

## Suggested Actions
- [ ] Reply to sender
- [ ] Forward to relevant party
- [ ] Create task based on email
- [ ] Archive after processing
"""

        # Write action file
        safe_subject = "".join(c if c.isalnum() or c in " _-" else "_" for c in subject)[:50]
        filename = f"EMAIL_{date_prefix}_{safe_subject}.md"
        filepath = self.needs_action / filename
        filepath.write_text(content, encoding="utf-8")

        # Mark as processed
        self.processed_ids.add(msg_id)
        self._save_processed_ids()

        # Log the action
        self._log_action(sender, subject, priority, keywords_found, timestamp)

        logger.info(f"[{priority.upper()}] Email from {sender}: {subject}")
        return filepath

    def _extract_body(self, payload: dict) -> str:
        """Extract plain text body from email payload."""
        body_text = ""

        mime_type = payload.get("mimeType", "")

        # Single part message
        if "body" in payload and payload["body"].get("data"):
            if "text/plain" in mime_type:
                body_text = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
                return body_text

        # Multipart message
        parts = payload.get("parts", [])
        for part in parts:
            part_mime = part.get("mimeType", "")
            if part_mime == "text/plain" and part.get("body", {}).get("data"):
                body_text = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                return body_text

            # Nested multipart
            if "parts" in part:
                nested_body = self._extract_body(part)
                if nested_body:
                    return nested_body

        return body_text

    def _assess_priority(self, subject: str, snippet: str, body: str) -> str:
        """Assess email priority based on content keywords."""
        combined = f"{subject} {snippet} {body}".lower()

        # Check for urgent keywords
        for keyword in URGENT_KEYWORDS:
            if keyword in combined:
                return "critical"

        # Check for business keywords
        for keyword in BUSINESS_KEYWORDS:
            if keyword in combined:
                return "high"

        return "medium"

    def _find_keywords(self, subject: str, snippet: str, body: str) -> list[str]:
        """Find all matching keywords in the email."""
        combined = f"{subject} {snippet} {body}".lower()
        found = []
        for keyword in URGENT_KEYWORDS + BUSINESS_KEYWORDS:
            if keyword in combined:
                found.append(keyword)
        return found

    def _log_action(self, sender: str, subject: str, priority: str, keywords: list, timestamp: str):
        """Log email detection to the daily log file."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{today}.json"

        log_entry = {
            "timestamp": timestamp,
            "action_type": "email_detected",
            "actor": "gmail_watcher",
            "target": sender,
            "parameters": {
                "subject": subject,
                "priority": priority,
                "keywords_matched": keywords,
                "source": "Gmail",
            },
            "result": "action_file_created",
        }

        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logs = []

        logs.append(log_entry)
        log_file.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="AI Employee Gmail Watcher")
    parser.add_argument(
        "--vault-path",
        type=str,
        default=str(DEFAULT_VAULT),
        help="Path to the Obsidian vault",
    )
    parser.add_argument(
        "--credentials",
        type=str,
        default="credentials.json",
        help="Path to Google OAuth2 credentials.json",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=str(TOKEN_FILE),
        help="Path to save/load OAuth2 token",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="is:unread is:important",
        help="Gmail search query (default: 'is:unread is:important')",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=120,
        help="Poll interval in seconds (default: 120)",
    )
    args = parser.parse_args()

    vault_path = Path(args.vault_path)
    logger.info(f"Vault path: {vault_path}")
    logger.info(f"Gmail query: {args.query}")
    logger.info(f"Poll interval: {args.interval}s")

    # Authenticate
    creds = authenticate(args.credentials, Path(args.token))
    logger.info("Gmail authentication successful")

    # Start watching
    watcher = GmailWatcher(
        vault_path=str(vault_path),
        creds=creds,
        query=args.query,
        check_interval=args.interval,
    )

    logger.info("Gmail watcher started. Press Ctrl+C to stop.\n")
    try:
        watcher.run()
    except KeyboardInterrupt:
        logger.info("Gmail watcher stopped.")


if __name__ == "__main__":
    main()
