---
name: facebook-instagram-poster
description: |
  Create and post business content on Facebook and Instagram using Playwright MCP.
  Supports draft creation with approval workflow, publishing approved posts,
  and generating engagement summaries. All posts require human approval before publishing.
user_invocable: false
---

# Facebook & Instagram Poster

## What This Skill Does
- Creates draft posts for Facebook or Instagram
- Generates content from vault context (business goals, recent achievements)
- Creates approval requests in `/Pending_Approval`
- Publishes approved posts via Playwright browser automation
- Generates weekly engagement summaries in `/Briefings`

## Commands

### Create a Draft
```bash
uv run python watchers/facebook_instagram_poster.py draft --platform facebook --topic "AI automation"
uv run python watchers/facebook_instagram_poster.py draft --platform instagram --topic "productivity tips"
```

### Check & Publish Approved Posts
```bash
uv run python watchers/facebook_instagram_poster.py check-approved --vault-path AI_Employee_Vault
uv run python watchers/facebook_instagram_poster.py check-approved --dry-run
```

### Generate Engagement Summary
```bash
uv run python watchers/facebook_instagram_poster.py summary --vault-path AI_Employee_Vault
```

## Approval Workflow
1. `draft` creates files in `/Plans` and `/Pending_Approval`
2. Human reviews and moves to `/Approved` or `/Rejected`
3. `check-approved` finds approved posts and publishes via Playwright
4. Published posts move to `/Done`
5. All actions logged to `/Logs`

## Prerequisites
- Playwright MCP server running on port 8808
- Logged into Facebook/Instagram in the Playwright browser session
