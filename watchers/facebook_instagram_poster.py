"""
Facebook & Instagram Poster for AI Employee.

Automates posting business content on Facebook and Instagram using Playwright MCP,
and generates engagement summaries.

Usage:
    # Create a draft for Facebook
    uv run python facebook_instagram_poster.py draft --platform facebook --topic "AI automation"

    # Create a draft for Instagram
    uv run python facebook_instagram_poster.py draft --platform instagram --topic "productivity tips"

    # Check for approved posts and publish
    uv run python facebook_instagram_poster.py check-approved --vault-path ../AI_Employee_Vault

    # Generate engagement summary
    uv run python facebook_instagram_poster.py summary --vault-path ../AI_Employee_Vault

    # Dry run
    uv run python facebook_instagram_poster.py check-approved --dry-run
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
logger = logging.getLogger("FBInstaPost")


# ── Playwright MCP helpers ─────────────────────

def mcp_call(tool: str, params: dict) -> dict:
    cmd = [sys.executable, str(MCP_CLIENT), "call", "-u", MCP_URL, "-t", tool, "-p", json.dumps(params)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"MCP call failed: {result.stderr}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout}


# ── Draft creation ─────────────────────────────

def create_draft(vault_path: Path, platform: str, topic: str, content: str | None = None) -> Path:
    plans_dir = vault_path / "Plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    date_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not content:
        content = _generate_content(vault_path, platform, topic)

    prefix = "FACEBOOK" if platform == "facebook" else "INSTAGRAM"
    filename = f"{prefix}_POST_{date_prefix}.md"

    draft = f"""---
type: social_post
platform: {platform}
status: draft
topic: "{topic}"
created: {timestamp}
approval_required: true
---

## Post Content

{content}

## Post Metadata
- **Platform**: {platform.title()}
- **Topic**: {topic}
- **Created**: {timestamp}
- **Character Count**: {len(content)}
- **Status**: Draft - awaiting approval
"""
    filepath = plans_dir / filename
    filepath.write_text(draft, encoding="utf-8")
    logger.info(f"Draft created: {filepath}")

    _create_approval(vault_path, filepath, content, platform, topic, timestamp)
    return filepath


def _generate_content(vault_path: Path, platform: str, topic: str) -> str:
    goals_file = vault_path / "Business_Goals.md"
    goals = ""
    if goals_file.exists():
        goals = goals_file.read_text(encoding="utf-8")[:300]

    done_dir = vault_path / "Done"
    achievements = []
    if done_dir.exists():
        for f in sorted(done_dir.iterdir(), reverse=True)[:3]:
            if f.suffix == ".md":
                achievements.append(f.stem)

    ach_text = "\n".join(f"- {a}" for a in achievements) if achievements else "- Building AI-powered workflows"

    if platform == "instagram":
        return f"""🚀 {topic.title()}

We're leveraging AI to transform how businesses operate:

{ach_text}

The future isn't coming — it's already here.

What's your take on {topic}? Drop a comment below! 👇

#AI #Automation #Business #Innovation #Productivity #Tech #FutureOfWork #Entrepreneurship"""
    else:
        return f"""Sharing our journey with {topic}.

Key highlights from this week:
{ach_text}

AI-powered automation is changing the game for small businesses. We're building systems that work around the clock so you don't have to.

What challenges are you facing with {topic}? Let's discuss in the comments!

#AI #Automation #Business #Innovation #Productivity"""


def _create_approval(vault_path: Path, draft_path: Path, content: str, platform: str, topic: str, timestamp: str):
    approval_dir = vault_path / "Pending_Approval"
    approval_dir.mkdir(parents=True, exist_ok=True)
    expiry = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    prefix = "FACEBOOK" if platform == "facebook" else "INSTAGRAM"
    approval = f"""---
type: approval_request
action: {platform}_post
topic: "{topic}"
created: {timestamp}
expires: {expiry}
status: pending
draft_file: "{draft_path.name}"
---

# Approval Required: {platform.title()} Post

## Post Preview

{content}

## Details
- **Platform**: {platform.title()}
- **Topic**: {topic}
- **Characters**: {len(content)}

## To Approve
Move this file to the `/Approved` folder.

## To Reject
Move this file to the `/Rejected` folder.
"""
    approval_path = approval_dir / f"{prefix}_POST_{draft_path.stem.split('_', 2)[-1]}.md"
    approval_path.write_text(approval, encoding="utf-8")
    logger.info(f"Approval request: {approval_path}")


# ── Posting via Playwright ─────────────────────

def post_to_facebook(content: str, dry_run: bool = False) -> bool:
    if dry_run:
        logger.info(f"[DRY RUN] Would post to Facebook ({len(content)} chars): {content[:150]}...")
        return True
    try:
        logger.info("Navigating to Facebook...")
        mcp_call("browser_navigate", {"url": "https://www.facebook.com/"})
        mcp_call("browser_wait_for", {"time": 3000})

        logger.info("Creating post via Facebook...")
        mcp_call("browser_run_code", {"code": """async (page) => {
            const btn = await page.locator('[aria-label="Create a post"], [aria-label*="What\\'s on your mind"]').first();
            if (btn) { await btn.click(); await page.waitForTimeout(2000); }
            return 'Post dialog opened';
        }"""})
        mcp_call("browser_wait_for", {"time": 2000})

        mcp_call("browser_run_code", {"code": f"""async (page) => {{
            const editor = await page.locator('[role="textbox"]').first();
            await editor.click();
            await editor.fill({json.dumps(content)});
            await page.waitForTimeout(1000);
            return 'Content typed';
        }}"""})

        mcp_call("browser_run_code", {"code": """async (page) => {
            const postBtn = await page.getByRole('button', { name: /^post$/i }).first();
            if (postBtn) { await postBtn.click(); await page.waitForTimeout(3000); }
            return 'Posted';
        }"""})

        mcp_call("browser_take_screenshot", {"type": "png", "fullPage": False})
        logger.info("Facebook post published!")
        return True
    except Exception as e:
        logger.error(f"Facebook post failed: {e}")
        return False


def post_to_instagram(content: str, dry_run: bool = False) -> bool:
    if dry_run:
        logger.info(f"[DRY RUN] Would post to Instagram ({len(content)} chars): {content[:150]}...")
        return True
    try:
        logger.info("Navigating to Instagram...")
        mcp_call("browser_navigate", {"url": "https://www.instagram.com/"})
        mcp_call("browser_wait_for", {"time": 3000})

        logger.info("Creating post via Instagram...")
        mcp_call("browser_run_code", {"code": """async (page) => {
            const createBtn = await page.locator('[aria-label="New post"], svg[aria-label="New post"]').first();
            if (createBtn) { await createBtn.click(); await page.waitForTimeout(2000); }
            return 'Create dialog opened';
        }"""})

        mcp_call("browser_run_code", {"code": f"""async (page) => {{
            const caption = await page.locator('textarea[aria-label*="caption"], [aria-label*="Write a caption"]').first();
            if (caption) {{ await caption.fill({json.dumps(content)}); await page.waitForTimeout(1000); }}
            return 'Caption filled';
        }}"""})

        mcp_call("browser_run_code", {"code": """async (page) => {
            const shareBtn = await page.getByRole('button', { name: /share/i }).first();
            if (shareBtn) { await shareBtn.click(); await page.waitForTimeout(3000); }
            return 'Shared';
        }"""})

        mcp_call("browser_take_screenshot", {"type": "png", "fullPage": False})
        logger.info("Instagram post published!")
        return True
    except Exception as e:
        logger.error(f"Instagram post failed: {e}")
        return False


# ── Check approved posts ───────────────────────

def check_approved(vault_path: Path, dry_run: bool = False) -> int:
    approved_dir = vault_path / "Approved"
    done_dir = vault_path / "Done"
    logs_dir = vault_path / "Logs"
    done_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    if not approved_dir.exists():
        logger.info("No /Approved folder found.")
        return 0

    count = 0
    for f in list(approved_dir.iterdir()):
        if not (f.name.startswith("FACEBOOK_POST_") or f.name.startswith("INSTAGRAM_POST_")):
            continue

        platform = "facebook" if f.name.startswith("FACEBOOK") else "instagram"
        logger.info(f"Found approved {platform} post: {f.name}")

        text = f.read_text(encoding="utf-8")
        post_content = _extract_preview(text)
        if not post_content:
            logger.warning(f"No content found in {f.name}")
            continue

        if platform == "facebook":
            success = post_to_facebook(post_content, dry_run)
        else:
            success = post_to_instagram(post_content, dry_run)

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        _append_log(logs_dir, {
            "timestamp": timestamp,
            "action_type": f"{platform}_post_published" if success else f"{platform}_post_failed",
            "actor": "fb_insta_poster",
            "target": platform.title(),
            "parameters": {"approval_file": f.name, "content_length": len(post_content), "dry_run": dry_run},
            "approval_status": "approved",
            "approved_by": "human",
            "result": "success" if success else "failed",
        })

        if success:
            f.rename(done_dir / f.name)
            count += 1

    if count == 0:
        logger.info("No approved Facebook/Instagram posts found.")
    return count


def _extract_preview(text: str) -> str:
    content = ""
    in_preview = False
    for line in text.split("\n"):
        if line.strip() == "## Post Preview":
            in_preview = True
            continue
        if in_preview and line.strip().startswith("## "):
            break
        if in_preview:
            content += line + "\n"
    return content.strip()


# ── Engagement summary ─────────────────────────

def generate_summary(vault_path: Path) -> Path:
    logs_dir = vault_path / "Logs"
    briefings_dir = vault_path / "Briefings"
    briefings_dir.mkdir(parents=True, exist_ok=True)

    fb_posts = 0
    ig_posts = 0
    total_chars = 0

    # Scan logs from the past 7 days
    for i in range(7):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        log_file = logs_dir / f"{day}.json"
        if not log_file.exists():
            continue
        try:
            logs = json.loads(log_file.read_text(encoding="utf-8"))
            for entry in logs:
                action = entry.get("action_type", "")
                if "facebook_post_published" in action:
                    fb_posts += 1
                    total_chars += entry.get("parameters", {}).get("content_length", 0)
                if "instagram_post_published" in action:
                    ig_posts += 1
                    total_chars += entry.get("parameters", {}).get("content_length", 0)
        except json.JSONDecodeError:
            continue

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = datetime.now().strftime("%Y-%m-%d")
    summary = f"""---
generated: {timestamp}
period: last 7 days
---

# Social Media Summary - Facebook & Instagram

## Overview
| Platform | Posts Published | Total Characters |
|----------|----------------|-----------------|
| Facebook | {fb_posts} | - |
| Instagram | {ig_posts} | - |
| **Total** | **{fb_posts + ig_posts}** | **{total_chars}** |

## Recommendations
- {"Increase posting frequency to 2-3 times per week" if (fb_posts + ig_posts) < 4 else "Good posting cadence this week"}
- Engage with comments within 24 hours of posting
- Cross-post high-performing content between platforms
- Use Instagram Stories for behind-the-scenes content

---
*Generated by AI Employee v0.2 (Gold Tier)*
"""
    filepath = briefings_dir / f"{date_str}_Social_Media_Summary.md"
    filepath.write_text(summary, encoding="utf-8")
    logger.info(f"Summary generated: {filepath}")
    return filepath


def _append_log(logs_dir: Path, entry: dict):
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


# ── CLI ────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI Employee Facebook & Instagram Poster")
    sub = parser.add_subparsers(dest="command", required=True)

    d = sub.add_parser("draft", help="Create a post draft")
    d.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))
    d.add_argument("--platform", choices=["facebook", "instagram"], required=True)
    d.add_argument("--topic", type=str, required=True)
    d.add_argument("--content", type=str, default=None)

    c = sub.add_parser("check-approved", help="Publish approved posts")
    c.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))
    c.add_argument("--dry-run", action="store_true")

    s = sub.add_parser("summary", help="Generate engagement summary")
    s.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))

    args = parser.parse_args()
    vault = Path(args.vault_path)

    if args.command == "draft":
        create_draft(vault, args.platform, args.topic, getattr(args, "content", None))
    elif args.command == "check-approved":
        check_approved(vault, getattr(args, "dry_run", False))
    elif args.command == "summary":
        generate_summary(vault)


if __name__ == "__main__":
    main()
