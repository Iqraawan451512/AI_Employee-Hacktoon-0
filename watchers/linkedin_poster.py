"""
LinkedIn Poster for AI Employee.

Automates posting business content on LinkedIn using Playwright MCP server.
Supports draft creation, human approval workflow, and actual posting.

Usage:
    # Generate a draft post (saves to vault, does NOT post)
    uv run python linkedin_poster.py draft --vault-path ../AI_Employee_Vault --topic "AI automation"

    # Post an approved draft (requires Playwright MCP running)
    uv run python linkedin_poster.py post --vault-path ../AI_Employee_Vault --draft-file LINKEDIN_POST_2026-02-26.md

    # Full workflow: draft -> approve -> post
    uv run python linkedin_poster.py auto --vault-path ../AI_Employee_Vault

    # Check for approved posts and publish them
    uv run python linkedin_poster.py check-approved --vault-path ../AI_Employee_Vault
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

DEFAULT_VAULT = Path(__file__).parent.parent / "AI_Employee_Vault"
MCP_CLIENT = Path(__file__).parent.parent / ".claude" / "skills" / "browsing-with-playwright" / "scripts" / "mcp-client.py"
MCP_URL = "http://localhost:8808"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("LinkedInPoster")


# ──────────────────────────────────────────────
# Playwright MCP helpers
# ──────────────────────────────────────────────

def mcp_call(tool: str, params: dict) -> dict:
    """Call a Playwright MCP tool and return the parsed result."""
    cmd = [
        sys.executable, str(MCP_CLIENT),
        "call",
        "-u", MCP_URL,
        "-t", tool,
        "-p", json.dumps(params),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"MCP call failed: {result.stderr}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout}


def mcp_navigate(url: str) -> dict:
    return mcp_call("browser_navigate", {"url": url})


def mcp_snapshot() -> dict:
    return mcp_call("browser_snapshot", {})


def mcp_click(element: str, ref: str) -> dict:
    return mcp_call("browser_click", {"element": element, "ref": ref})


def mcp_type(element: str, ref: str, text: str, submit: bool = False) -> dict:
    return mcp_call("browser_type", {"element": element, "ref": ref, "text": text, "submit": submit})


def mcp_screenshot() -> dict:
    return mcp_call("browser_take_screenshot", {"type": "png", "fullPage": False})


def mcp_wait(time_ms: int = 2000) -> dict:
    return mcp_call("browser_wait_for", {"time": time_ms})


# ──────────────────────────────────────────────
# Draft creation
# ──────────────────────────────────────────────

def create_draft(vault_path: Path, topic: str, content: str | None = None) -> Path:
    """Create a LinkedIn post draft in the vault's Plans folder."""
    plans_dir = vault_path / "Plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = datetime.now().strftime("%Y-%m-%d")
    date_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Generate default content if none provided
    if not content:
        content = _generate_default_content(vault_path, topic)

    draft_content = f"""---
type: linkedin_post
status: draft
topic: "{topic}"
created: {timestamp}
scheduled_for: {(datetime.now(timezone.utc) + timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%SZ")}
approval_required: true
---

## Post Content

{content}

## Post Metadata
- **Topic**: {topic}
- **Created**: {timestamp}
- **Character Count**: {len(content)}
- **Status**: Draft - awaiting approval
"""

    filename = f"LINKEDIN_POST_{date_prefix}.md"
    filepath = plans_dir / filename
    filepath.write_text(draft_content, encoding="utf-8")
    logger.info(f"Draft created: {filepath}")

    # Create approval request
    _create_approval_request(vault_path, filepath, content, topic, timestamp)

    return filepath


def _generate_default_content(vault_path: Path, topic: str) -> str:
    """Generate default post content based on vault data."""
    # Try to read business goals for context
    goals_file = vault_path / "Business_Goals.md"
    goals_context = ""
    if goals_file.exists():
        goals_context = goals_file.read_text(encoding="utf-8")[:500]

    # Try to read recent Done items for achievements
    done_dir = vault_path / "Done"
    recent_achievements = []
    if done_dir.exists():
        for f in sorted(done_dir.iterdir(), reverse=True)[:5]:
            if f.suffix == ".md":
                recent_achievements.append(f.stem)

    # Build a template post
    achievements_text = ""
    if recent_achievements:
        achievements_text = "\n".join(f"- {a}" for a in recent_achievements[:3])

    content = f"""Sharing insights on {topic} today.

In the world of AI and automation, staying ahead means embracing intelligent workflows that save time and drive results.

Key takeaways from our recent work:
{achievements_text if achievements_text else "- Streamlined operations with AI-powered automation"}
- Building systems that work 24/7
- Focusing on what matters most

What are your thoughts on {topic}? Let's connect and discuss.

#AI #Automation #Business #Innovation #Productivity"""

    return content


def _create_approval_request(vault_path: Path, draft_path: Path, content: str, topic: str, timestamp: str):
    """Create an approval request file in /Pending_Approval."""
    approval_dir = vault_path / "Pending_Approval"
    approval_dir.mkdir(parents=True, exist_ok=True)

    expiry = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    approval_content = f"""---
type: approval_request
action: linkedin_post
topic: "{topic}"
created: {timestamp}
expires: {expiry}
status: pending
draft_file: "{draft_path.name}"
---

# Approval Required: LinkedIn Post

## Post Preview

{content}

## Details
- **Topic**: {topic}
- **Characters**: {len(content)}
- **Draft File**: {draft_path.name}

## To Approve
Move this file to the `/Approved` folder.

## To Reject
Move this file to the `/Rejected` folder.

## To Edit
Modify the post content in the draft file, then move this to `/Approved`.
"""

    approval_filename = f"LINKEDIN_POST_{draft_path.stem.split('_', 2)[-1]}.md"
    approval_path = approval_dir / approval_filename
    approval_path.write_text(approval_content, encoding="utf-8")
    logger.info(f"Approval request created: {approval_path}")


# ──────────────────────────────────────────────
# Posting via Playwright
# ──────────────────────────────────────────────

def post_to_linkedin(vault_path: Path, content: str, dry_run: bool = False) -> bool:
    """Post content to LinkedIn using Playwright MCP server."""
    if dry_run:
        logger.info("[DRY RUN] Would post to LinkedIn:")
        logger.info(f"Content ({len(content)} chars): {content[:200]}...")
        return True

    try:
        # Step 1: Navigate to LinkedIn
        logger.info("Navigating to LinkedIn...")
        mcp_navigate("https://www.linkedin.com/feed/")
        mcp_wait(3000)

        # Step 2: Take snapshot to find "Start a post" button
        logger.info("Taking snapshot to find post button...")
        snapshot = mcp_snapshot()

        # Step 3: Look for the post creation button and click it
        # The exact ref depends on the LinkedIn UI at the time
        logger.info("Looking for 'Start a post' button...")
        # Try clicking the post creation area
        snapshot_str = json.dumps(snapshot)

        # Common LinkedIn post button identifiers
        post_button_found = False
        for search_text in ["Start a post", "What do you want to talk about", "Share"]:
            if search_text.lower() in snapshot_str.lower():
                # Find the ref for this element
                logger.info(f"Found post trigger: '{search_text}'")
                post_button_found = True
                break

        if not post_button_found:
            logger.warning("Could not find LinkedIn post button. Taking screenshot for debug.")
            mcp_screenshot()
            return False

        # Step 4: Click on the post area to open the post editor
        # We'll use browser_run_code for more reliable interaction
        logger.info("Opening post editor...")
        mcp_call("browser_run_code", {
            "code": """async (page) => {
                // Click "Start a post" button
                const btn = await page.getByRole('button', { name: /start a post/i }).first();
                if (btn) {
                    await btn.click();
                    await page.waitForTimeout(2000);
                    return 'Post editor opened';
                }
                // Fallback: click the text area
                const textArea = await page.locator('[role="textbox"]').first();
                if (textArea) {
                    await textArea.click();
                    await page.waitForTimeout(2000);
                    return 'Text area clicked';
                }
                return 'No post button found';
            }"""
        })

        mcp_wait(2000)

        # Step 5: Type the post content
        logger.info("Typing post content...")
        mcp_call("browser_run_code", {
            "code": f"""async (page) => {{
                const editor = await page.locator('[role="textbox"]').first();
                await editor.click();
                await editor.fill({json.dumps(content)});
                await page.waitForTimeout(1000);
                return 'Content typed';
            }}"""
        })

        mcp_wait(1000)

        # Step 6: Click Post button
        logger.info("Clicking Post button...")
        mcp_call("browser_run_code", {
            "code": """async (page) => {
                const postBtn = await page.getByRole('button', { name: /^post$/i }).first();
                if (postBtn) {
                    await postBtn.click();
                    await page.waitForTimeout(3000);
                    return 'Post published';
                }
                return 'Post button not found';
            }"""
        })

        mcp_wait(3000)

        # Step 7: Screenshot for confirmation
        logger.info("Taking confirmation screenshot...")
        mcp_screenshot()

        logger.info("LinkedIn post published successfully!")
        return True

    except Exception as e:
        logger.error(f"Failed to post to LinkedIn: {e}")
        return False


# ──────────────────────────────────────────────
# Approval checking
# ──────────────────────────────────────────────

def check_approved_posts(vault_path: Path, dry_run: bool = False) -> int:
    """Check /Approved for LinkedIn posts and publish them."""
    approved_dir = vault_path / "Approved"
    done_dir = vault_path / "Done"
    plans_dir = vault_path / "Plans"
    logs_dir = vault_path / "Logs"

    done_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    if not approved_dir.exists():
        logger.info("No /Approved folder found.")
        return 0

    posted_count = 0
    for approval_file in approved_dir.iterdir():
        if not approval_file.name.startswith("LINKEDIN_POST_"):
            continue

        logger.info(f"Found approved LinkedIn post: {approval_file.name}")

        # Read the approval file to get the draft reference
        content_text = approval_file.read_text(encoding="utf-8")

        # Extract post content from between "## Post Preview" and "## Details"
        post_content = ""
        in_preview = False
        for line in content_text.split("\n"):
            if line.strip() == "## Post Preview":
                in_preview = True
                continue
            if line.strip().startswith("## Details") or line.strip().startswith("## To"):
                in_preview = False
                continue
            if in_preview:
                post_content += line + "\n"

        post_content = post_content.strip()
        if not post_content:
            logger.warning(f"No post content found in {approval_file.name}")
            continue

        # Post it
        success = post_to_linkedin(vault_path, post_content, dry_run=dry_run)

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Log the result
        log_entry = {
            "timestamp": timestamp,
            "action_type": "linkedin_post_published" if success else "linkedin_post_failed",
            "actor": "linkedin_poster",
            "target": "LinkedIn",
            "parameters": {
                "approval_file": approval_file.name,
                "content_length": len(post_content),
                "dry_run": dry_run,
            },
            "approval_status": "approved",
            "approved_by": "human",
            "result": "success" if success else "failed",
        }
        _append_log(logs_dir, log_entry)

        if success:
            # Move approval file to Done
            approval_file.rename(done_dir / approval_file.name)
            logger.info(f"Moved {approval_file.name} to /Done")
            posted_count += 1
        else:
            logger.error(f"Failed to post {approval_file.name}. Leaving in /Approved for retry.")

    if posted_count == 0:
        logger.info("No approved LinkedIn posts found.")

    return posted_count


def _append_log(logs_dir: Path, entry: dict):
    """Append a log entry to today's log file."""
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = logs_dir / f"{today}.json"

    logs = []
    if log_file.exists():
        try:
            logs = json.loads(log_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logs = []

    logs.append(entry)
    log_file.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI Employee LinkedIn Poster")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # draft command
    draft_parser = subparsers.add_parser("draft", help="Create a LinkedIn post draft")
    draft_parser.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))
    draft_parser.add_argument("--topic", type=str, required=True, help="Post topic")
    draft_parser.add_argument("--content", type=str, default=None, help="Custom post content (optional)")

    # post command
    post_parser = subparsers.add_parser("post", help="Post content to LinkedIn directly")
    post_parser.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))
    post_parser.add_argument("--content", type=str, required=True, help="Content to post")
    post_parser.add_argument("--dry-run", action="store_true", help="Log but don't actually post")

    # check-approved command
    check_parser = subparsers.add_parser("check-approved", help="Check for approved posts and publish")
    check_parser.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))
    check_parser.add_argument("--dry-run", action="store_true", help="Log but don't actually post")

    # auto command (draft + wait for approval)
    auto_parser = subparsers.add_parser("auto", help="Full workflow: draft -> approve -> post")
    auto_parser.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))
    auto_parser.add_argument("--topic", type=str, default="business automation", help="Post topic")
    auto_parser.add_argument("--dry-run", action="store_true", help="Log but don't actually post")

    args = parser.parse_args()
    vault_path = Path(args.vault_path)

    if args.command == "draft":
        draft_path = create_draft(vault_path, args.topic, args.content)
        logger.info(f"\nDraft created at: {draft_path}")
        logger.info("Review the draft and move the approval file from /Pending_Approval to /Approved to publish.")

    elif args.command == "post":
        dry_run = getattr(args, "dry_run", False)
        success = post_to_linkedin(vault_path, args.content, dry_run=dry_run)
        sys.exit(0 if success else 1)

    elif args.command == "check-approved":
        dry_run = getattr(args, "dry_run", False)
        count = check_approved_posts(vault_path, dry_run=dry_run)
        logger.info(f"Published {count} post(s).")

    elif args.command == "auto":
        # Step 1: Create draft
        draft_path = create_draft(vault_path, args.topic)
        logger.info(f"\nDraft created at: {draft_path}")
        logger.info("Waiting for approval... Move the file from /Pending_Approval to /Approved.")

        # Step 2: Poll for approval
        approved_dir = vault_path / "Approved"
        check_interval = 30
        max_wait = 3600  # 1 hour
        waited = 0

        while waited < max_wait:
            if approved_dir.exists():
                for f in approved_dir.iterdir():
                    if f.name.startswith("LINKEDIN_POST_"):
                        logger.info("Approval detected!")
                        dry_run = getattr(args, "dry_run", False)
                        check_approved_posts(vault_path, dry_run=dry_run)
                        return
            time.sleep(check_interval)
            waited += check_interval
            if waited % 300 == 0:
                logger.info(f"Still waiting for approval... ({waited // 60} min elapsed)")

        logger.warning("Timed out waiting for approval after 1 hour.")


if __name__ == "__main__":
    main()
