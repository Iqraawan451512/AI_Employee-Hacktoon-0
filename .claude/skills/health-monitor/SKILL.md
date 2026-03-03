---
name: health-monitor
description: |
  Cloud health monitoring service. Checks cloud orchestrator, gmail watcher,
  vault sync, Odoo HTTP, and disk usage every 60 seconds. Writes health
  signals to Updates/ for the dashboard merger.
user_invocable: true
---

# Health Monitor (Platinum Tier)

## What This Skill Does
- Checks health of all cloud-side services every 60 seconds
- Writes health status to `Updates/HEALTH_<timestamp>.md`
- Dashboard merger picks up signals and updates Dashboard.md
- Runs as a systemd service on the cloud VM

## Health Checks
| Check | Method | OK | Warn | Error |
|-------|--------|----|----- |-------|
| Cloud orchestrator | pgrep process | Running | Check timeout | Not running |
| Gmail watcher | pgrep process | Running | Check timeout | Not running |
| Vault sync | Last sync signal age | <2min | 2-5min | >5min |
| Odoo | HTTP GET :8069 | 200 | Non-200 | Unreachable |
| Disk usage | shutil.disk_usage | <80% | 80-90% | >90% |

## How to Use

### Run Once
```bash
uv run python watchers/health_monitor.py --vault-path AI_Employee_Vault --once
```

### Continuous Loop
```bash
uv run python watchers/health_monitor.py --vault-path AI_Employee_Vault --interval 60
```

### As systemd Service
```bash
sudo systemctl start ai-health-monitor
sudo systemctl status ai-health-monitor
journalctl -u ai-health-monitor -f
```

## Output Signal Format
Health signals in `Updates/HEALTH_*.md`:
```markdown
---
type: health_status
agent: cloud
action: health_ok | health_warn | health_error
overall: ok | warn | error
---

| Service | Status | Detail |
|---------|--------|--------|
| cloud_orchestrator | OK | Running (PID: 1234) |
| gmail_watcher | OK | Running (PID: 5678) |
| vault_sync | OK | Last sync 15s ago |
| odoo | OK | HTTP 200 |
| disk | OK | 45.2% used (50.3GB free) |
```
