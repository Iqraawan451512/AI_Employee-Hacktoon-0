---
name: claim-manager
description: |
  Claim-by-move protocol for preventing Cloud and Local agents from processing
  the same task. Atomically moves files to In_Progress/<agent>/ for claiming
  and releases them to destination folders when done.
user_invocable: true
---

# Claim Manager (Platinum Tier)

## What This Skill Does
- Prevents Cloud and Local agents from processing the same task
- `try_claim(file, agent)` atomically moves file to `In_Progress/<agent>/`
- `release(file, dest)` moves file from In_Progress to destination
- Writes `.claim` metadata alongside claimed files
- If file is already gone (claimed by other agent), returns None

## How to Use

### In Python
```python
from claim_manager import ClaimManager

cm = ClaimManager(vault_path)

# Claim a task
claimed = cm.try_claim(Path("Needs_Action/email/task.md"), agent="cloud")
if claimed:
    # Process the file...
    cm.release(claimed, destination="Pending_Approval/email")
else:
    print("Another agent already claimed this task")

# List all current claims
claims = cm.list_claims(agent="cloud")
```

## Claim Protocol
```
1. Agent finds task in Needs_Action/<domain>/
2. try_claim() → atomic rename to In_Progress/<agent>/
   ├── Success → .claim metadata written, return claimed path
   └── Failure (file gone) → return None (other agent won)
3. Agent processes the file
4. release() → move from In_Progress to destination folder
```

## Directory Structure
```
In_Progress/
├── cloud/       # Tasks currently claimed by Cloud agent
│   ├── task.md
│   └── task.md.claim  # metadata (agent, timestamp, original path)
└── local/       # Tasks currently claimed by Local agent
```

## Safety
- Atomic rename prevents double-processing
- `.claim` metadata enables debugging stuck claims
- Both agents must use this protocol for coordination
