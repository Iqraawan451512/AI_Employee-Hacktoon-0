"""
Twitter (X) Poster for AI Employee.

Automates posting on Twitter/X using Playwright MCP and generates engagement summaries.

Usage:
    uv run python twitter_poster.py draft --topic "AI automation"
    uv run python twitter_poster.py check-approved --vault-path ../AI_Employee_Vault
    uv run python twitter_poster.py summary --vault-path ../AI_Employee_Vault
    uv run python twitter_poster.py check-approved --dry-run
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
logger = logging.getLogger("TwitterPoster")


def mcp_call(tool: str, params: dict) -> dict:
    cmd = [sys.executable, str(MCP_CLIENT), "call", "-u", MCP_URL, "-t", tool, "-p", json.dumps(params)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"MCP call failed: {result.stderr}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout}


# ── Draft ──────────────────────────────────────

def create_draft(vault_path: Path, topic: str, content: str | None = None) -> Path:
    plans_dir = vault_path / "Plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    date_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not content:
        content = _generate_tweet(vault_path, topic)

    # Twitter limit: 280 chars
    if len(content) > 280:
        logger.warning(f"Tweet is {len(content)} chars (max 280). Truncating...")
        content = content[:277] + "..."

    filename = f"TWITTER_POST_{date_prefix}.md"
    draft = f"""---
type: social_post
platform: twitter
status: draft
topic: "{topic}"
created: {timestamp}
approval_required: true
char_count: {len(content)}
---

## Post Content

{content}

## Post Metadata
- **Platform**: Twitter (X)
- **Topic**: {topic}
- **Characters**: {len(content)} / 280
- **Status**: Draft - awaiting approval
"""
    filepath = plans_dir / filename
    filepath.write_text(draft, encoding="utf-8")
    logger.info(f"Draft created: {filepath}")

    _create_approval(vault_path, filepath, content, topic, timestamp)
    return filepath


def _generate_tweet(vault_path: Path, topic: str) -> str:
    done_dir = vault_path / "Done"
    achievement = ""
    if done_dir.exists():
        for f in sorted(done_dir.iterdir(), reverse=True)[:1]:
            if f.suffix == ".md":
                achievement = f"Recent win: {f.stem[:40]}\n\n"

    return f"""{achievement}Working on {topic} — AI automation is transforming how small businesses operate.

Build systems that work 24/7 so you can focus on what matters.

#AI #Automation #Business"""[:280]


def _create_approval(vault_path: Path, draft_path: Path, content: str, topic: str, timestamp: str):
    approval_dir = vault_path / "Pending_Approval"
    approval_dir.mkdir(parents=True, exist_ok=True)
    expiry = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    approval = f"""---
type: approval_request
action: twitter_post
topic: "{topic}"
created: {timestamp}
expires: {expiry}
status: pending
draft_file: "{draft_path.name}"
---

# Approval Required: Twitter (X) Post

## Post Preview

{content}

## Details
- **Platform**: Twitter (X)
- **Characters**: {len(content)} / 280
- **Topic**: {topic}

## To Approve
Move this file to the `/Approved` folder.

## To Reject
Move this file to the `/Rejected` folder.
"""
    suffix = draft_path.stem.split("_", 2)[-1]
    approval_path = approval_dir / f"TWITTER_POST_{suffix}.md"
    approval_path.write_text(approval, encoding="utf-8")
    logger.info(f"Approval request: {approval_path}")


# ── Post via Playwright ────────────────────────

def post_to_twitter(content: str, dry_run: bool = False) -> bool:
    if dry_run:
        logger.info(f"[DRY RUN] Would tweet ({len(content)} chars): {content[:150]}...")
        return True
    try:
        logger.info("Navigating to Twitter/X...")
        mcp_call("browser_navigate", {"url": "https://x.com/compose/post"})
        mcp_call("browser_wait_for", {"time": 3000})

        logger.info("Composing tweet...")
        mcp_call("browser_run_code", {"code": f"""async (page) => {{
            const editor = await page.locator('[data-testid="tweetTextarea_0"], [role="textbox"]').first();
            await editor.click();
            await editor.fill({json.dumps(content)});
            await page.waitForTimeout(1000);
            return 'Content typed';
        }}"""})

        mcp_call("browser_wait_for", {"time": 1000})

        logger.info("Clicking Post button...")
        mcp_call("browser_run_code", {"code": """async (page) => {
            const postBtn = await page.locator('[data-testid="tweetButton"], [data-testid="tweetButtonInline"]').first();
            if (postBtn) { await postBtn.click(); await page.waitForTimeout(3000); }
            return 'Tweeted';
        }"""})

        mcp_call("browser_take_screenshot", {"type": "png", "fullPage": False})
        logger.info("Tweet published!")
        return True
    except Exception as e:
        logger.error(f"Tweet failed: {e}")
        return False


# ── Check approved ─────────────────────────────

def check_approved(vault_path: Path, dry_run: bool = False) -> int:
    approved_dir = vault_path / "Approved"
    done_dir = vault_path / "Done"
    logs_dir = vault_path / "Logs"
    done_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    if not approved_dir.exists():
        logger.info("No /Approved folder.")
        return 0

    count = 0
    for f in list(approved_dir.iterdir()):
        if not f.name.startswith("TWITTER_POST_"):
            continue

        logger.info(f"Found approved tweet: {f.name}")
        text = f.read_text(encoding="utf-8")
        post_content = _extract_preview(text)
        if not post_content:
            continue

        success = post_to_twitter(post_content, dry_run)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        _append_log(logs_dir, {
            "timestamp": timestamp,
            "action_type": "twitter_post_published" if success else "twitter_post_failed",
            "actor": "twitter_poster",
            "target": "Twitter/X",
            "parameters": {"approval_file": f.name, "content_length": len(post_content), "dry_run": dry_run},
            "approval_status": "approved",
            "approved_by": "human",
            "result": "success" if success else "failed",
        })

        if success:
            f.rename(done_dir / f.name)
            count += 1

    if count == 0:
        logger.info("No approved tweets found.")
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


# ── Summary ────────────────────────────────────

def generate_summary(vault_path: Path) -> Path:
    logs_dir = vault_path / "Logs"
    briefings_dir = vault_path / "Briefings"
    briefings_dir.mkdir(parents=True, exist_ok=True)

    tweet_count = 0
    for i in range(7):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        log_file = logs_dir / f"{day}.json"
        if not log_file.exists():
            continue
        try:
            logs = json.loads(log_file.read_text(encoding="utf-8"))
            tweet_count += sum(1 for e in logs if "twitter_post_published" in e.get("action_type", ""))
        except json.JSONDecodeError:
            continue

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = datetime.now().strftime("%Y-%m-%d")
    summary = f"""---
generated: {timestamp}
period: last 7 days
---

# Twitter (X) Summary

## Overview
| Metric | Value |
|--------|-------|
| Tweets Published | {tweet_count} |
| Avg per day | {tweet_count / 7:.1f} |

## Recommendations
- {"Post at least 3-5 tweets per week for visibility" if tweet_count < 3 else "Good posting frequency!"}
- Engage with replies and quote-tweets
- Use threads for longer insights
- Post during peak hours (8-10 AM, 12-1 PM, 5-7 PM)

---
*Generated by AI Employee v0.2 (Gold Tier)*
"""
    filepath = briefings_dir / f"{date_str}_Twitter_Summary.md"
    filepath.write_text(summary, encoding="utf-8")
    logger.info(f"Summary: {filepath}")
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


def main():
    parser = argparse.ArgumentParser(description="AI Employee Twitter (X) Poster")
    sub = parser.add_subparsers(dest="command", required=True)

    d = sub.add_parser("draft", help="Create a tweet draft")
    d.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))
    d.add_argument("--topic", type=str, required=True)
    d.add_argument("--content", type=str, default=None)

    c = sub.add_parser("check-approved", help="Publish approved tweets")
    c.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))
    c.add_argument("--dry-run", action="store_true")

    s = sub.add_parser("summary", help="Generate Twitter summary")
    s.add_argument("--vault-path", type=str, default=str(DEFAULT_VAULT))

    args = parser.parse_args()
    vault = Path(args.vault_path)

    if args.command == "draft":
        create_draft(vault, args.topic, getattr(args, "content", None))
    elif args.command == "check-approved":
        check_approved(vault, getattr(args, "dry_run", False))
    elif args.command == "summary":
        generate_summary(vault)


if __name__ == "__main__":
    main()
