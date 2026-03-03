---
name: linkedin-poster
description: |
  Automatically create and post business content on LinkedIn to generate sales leads.
  Uses Playwright browser automation to log in, compose, and publish posts.
  Supports draft-only mode (requires human approval before posting) and scheduled posting.
user_invocable: true
---

# LinkedIn Poster Skill

Create and publish business content on LinkedIn using Playwright browser automation.

## Prerequisites

1. **Playwright MCP server** running (uses `browsing-with-playwright` skill)
2. **LinkedIn account** credentials stored securely in environment variables
3. **Company Handbook** rules followed (drafts auto-approved, publishing requires human approval)

## Workflow

### Step 1: Generate Post Content

Before posting, Claude generates content based on:
- Business goals from `AI_Employee_Vault/Business_Goals.md`
- Recent achievements from `AI_Employee_Vault/Done/`
- Industry trends and thought leadership topics

Content is saved as a draft in the vault first:

```markdown
# AI_Employee_Vault/Plans/LINKEDIN_POST_2026-02-26.md
---
type: linkedin_post
status: draft
created: 2026-02-26T10:00:00Z
scheduled_for: 2026-02-26T14:00:00Z
approval_required: true
---

## Post Content
<generated post text>

## Hashtags
#AI #Automation #Business

## Target Audience
Business owners, tech leads

## Goal
Brand awareness / Lead generation
```

### Step 2: Human Approval (HITL)

Per Company Handbook, social media publishing **requires human approval**:

1. Draft is created in `/Plans/`
2. Approval file created in `/Pending_Approval/`:

```markdown
# AI_Employee_Vault/Pending_Approval/LINKEDIN_POST_2026-02-26.md
---
type: approval_request
action: linkedin_post
created: 2026-02-26T10:00:00Z
expires: 2026-02-27T10:00:00Z
status: pending
---

## Post Preview
<post content here>

## To Approve
Move this file to /Approved folder.

## To Reject
Move this file to /Rejected folder.

## To Edit
Modify the post content above, then move to /Approved.
```

3. Human reviews and moves file to `/Approved/` or `/Rejected/`

### Step 3: Post via Playwright

Once approved, use the Playwright MCP to post:

```bash
# 1. Start Playwright MCP server
bash .claude/skills/browsing-with-playwright/scripts/start-server.sh

# 2. Navigate to LinkedIn
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_navigate \
  -p '{"url": "https://www.linkedin.com/feed/"}'

# 3. Take snapshot to find the post button
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_snapshot -p '{}'

# 4. Click "Start a post" button (ref from snapshot)
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_click \
  -p '{"element": "Start a post", "ref": "<ref_from_snapshot>"}'

# 5. Type the post content
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_type \
  -p '{"element": "Post editor", "ref": "<ref>", "text": "<post_content>"}'

# 6. Click Post button
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_click \
  -p '{"element": "Post button", "ref": "<ref>"}'

# 7. Screenshot for confirmation
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_take_screenshot \
  -p '{"type": "png", "fullPage": false}'
```

### Step 4: Log and Update

After posting:
1. Log the action to `/Logs/YYYY-MM-DD.json`
2. Move approval file to `/Done/`
3. Update Dashboard with posting activity

## Post Content Guidelines

Generate posts that:
- Share business insights and expertise
- Highlight recent project completions
- Offer value to potential clients
- Include relevant hashtags (3-5 max)
- Keep under 1300 characters for optimal engagement
- Include a call-to-action (CTA)

## Content Templates

### Achievement Post
```
Excited to share that we just completed [project/milestone]!

Key results:
- [Result 1]
- [Result 2]
- [Result 3]

[Insight or lesson learned]

#Industry #Achievement #Business
```

### Thought Leadership
```
[Industry trend or observation]

Here's what we've learned from [experience]:

1. [Insight 1]
2. [Insight 2]
3. [Insight 3]

What's your experience with [topic]?

#ThoughtLeadership #Industry
```

### Service Promotion
```
[Problem statement that resonates with target audience]

We help businesses [solution] by [method].

Recent results for our clients:
- [Metric 1]
- [Metric 2]

Interested? Let's connect.

#Services #Business #Solutions
```

## Scheduling

LinkedIn posts can be scheduled by creating draft files with `scheduled_for` in the frontmatter. The `scheduler` skill picks these up and triggers posting at the right time.

## Dry Run Mode

Set `DRY_RUN=true` in environment to generate and approve posts without actually publishing.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| LinkedIn login required | Use Playwright in headed mode to log in first; session persists |
| Post button not found | Take a fresh snapshot; LinkedIn UI may have changed |
| Rate limited | Space posts 24+ hours apart |
| Content flagged | Review LinkedIn content policies; avoid spam patterns |
