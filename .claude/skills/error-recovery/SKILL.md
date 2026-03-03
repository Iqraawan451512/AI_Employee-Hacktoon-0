---
name: error-recovery
description: |
  Error recovery and watchdog system for AI Employee. Handles retry logic with exponential
  backoff, classifies errors (transient vs permanent), and monitors watcher processes.
  The watchdog auto-restarts crashed processes and alerts human when max restarts exceeded.
  Use when a watcher crashes, an API call fails, or you need to diagnose system errors.
user_invocable: false
---

# Error Recovery & Watchdog

## What This Skill Does
- Provides retry logic with exponential backoff for transient errors
- Classifies errors into categories: transient, authentication, data, system
- Monitors all watcher processes and auto-restarts on crash
- Alerts human via `/Needs_Action` when processes exceed max restart limit
- Logs all restarts and failures to `/Logs`

## Retry Handler (`watchers/retry_handler.py`)

### Usage in Code
```python
from retry_handler import with_retry, TransientError, PermanentError, classify_error

@with_retry(max_attempts=3, base_delay=1.0, max_delay=60.0)
def call_api():
    # Will retry up to 3 times with exponential backoff
    ...
```

### Error Classification
```python
category = classify_error(some_exception)
# Returns: "transient", "authentication", "data", "system", or "unknown"
```

## Watchdog (`watchers/watchdog.py`)

### Start Watchdog
```bash
uv run python watchers/watchdog.py --vault-path AI_Employee_Vault --check-interval 30
```

### Custom Config
Create `watchdog_config.json`:
```json
{
  "filesystem_watcher": {
    "command": ["python", "filesystem_watcher.py", "--vault-path", "../AI_Employee_Vault"],
    "cwd": "watchers",
    "restart_delay": 5,
    "max_restarts": 10
  }
}
```

### Behavior
- Checks processes every 30 seconds (configurable)
- Restarts crashed processes with configurable delay
- Resets restart counter if process ran >5 minutes (stable)
- Creates ALERT files in `/Needs_Action` when max restarts exceeded
- Saves PIDs to `watchers/.pids/` for tracking

## Recovery Strategies by Error Type
| Category | Action |
|----------|--------|
| Transient | Retry with backoff |
| Authentication | Alert human, do NOT retry |
| Data | Log and skip, alert human |
| System | Alert human immediately |
