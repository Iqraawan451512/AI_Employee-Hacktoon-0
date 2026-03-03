---
name: twitter-poster
description: |
  Create and post content on Twitter/X using Playwright MCP. Enforces 280 character limit.
  Supports draft creation with approval workflow, publishing approved tweets,
  and generating weekly engagement summaries. All posts require human approval.
user_invocable: false
---

# Twitter (X) Poster

## What This Skill Does
- Creates tweet drafts (max 280 characters) with approval workflow
- Generates content from vault context
- Publishes approved tweets via Playwright browser automation
- Generates weekly Twitter engagement summaries

## Commands

### Create a Draft
```bash
uv run python watchers/twitter_poster.py draft --topic "AI automation"
uv run python watchers/twitter_poster.py draft --topic "business" --content "Custom tweet text here"
```

### Check & Publish Approved Tweets
```bash
uv run python watchers/twitter_poster.py check-approved --vault-path AI_Employee_Vault
uv run python watchers/twitter_poster.py check-approved --dry-run
```

### Generate Summary
```bash
uv run python watchers/twitter_poster.py summary --vault-path AI_Employee_Vault
```

## Character Limit
- Tweets auto-truncated to 280 characters
- Character count shown in draft metadata

## Approval Workflow
1. `draft` → `/Plans` + `/Pending_Approval`
2. Human moves to `/Approved`
3. `check-approved` publishes via Playwright
4. Published tweets move to `/Done`

## Prerequisites
- Playwright MCP server running on port 8808
- Logged into Twitter/X in the Playwright browser session
