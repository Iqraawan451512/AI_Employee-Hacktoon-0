---
type: playbook
version: "0.4"
last_updated: 2026-03-03
tier: platinum
---

# Error Recovery Playbook

## Error Classification
| Category | Examples | Recovery Action |
|----------|----------|----------------|
| Transient | Timeout, rate limit, 502/503 | Retry with exponential backoff |
| Authentication | 401, token expired, forbidden | Alert human, refresh credentials |
| Data | JSON parse error, missing field | Log and skip, alert human |
| System | Disk full, memory, permission denied | Alert human immediately |

## Retry Strategy
- **Base delay**: 1 second
- **Max delay**: 60 seconds
- **Max attempts**: 3 (configurable)
- **Backoff formula**: `min(base * 2^attempt, max_delay)`

## Watchdog Configuration
| Process | Restart Delay | Max Restarts |
|---------|--------------|--------------|
| filesystem_watcher | 5s | 10 |
| gmail_watcher | 10s | 5 |

## Escalation Path
1. Error occurs → Retry automatically (if transient)
2. All retries fail → Log error, create alert
3. Process crashes → Watchdog restarts
4. Max restarts exceeded → Alert in `/Needs_Action`
5. Human reviews alert → Manual intervention

## Common Issues & Fixes
| Issue | Solution |
|-------|----------|
| Gmail token expired | Re-run `gmail_watcher.py` to trigger OAuth refresh |
| Playwright timeout | Check MCP server is running on port 8808 |
| File watcher crash | Check `/Inbox` permissions, restart via watchdog |
| Rate limited | Wait and retry, or reduce posting frequency |

## Sync Conflict Recovery (Platinum)

| Scenario | Recovery |
|----------|----------|
| Dashboard.md conflict | Auto-resolved: Local always wins (`merge=ours`) |
| Other file conflict | Auto-resolved: Remote wins, local saved as `.conflict` |
| Rebase failure | Auto-aborted, retry next cycle |
| Push rejected | Pull first, then retry push |
| Vault sync stale (>5min) | Health monitor raises ERROR, check network/Git remote |

### Manual Sync Recovery
```bash
# Check sync status
cd AI_Employee_Vault && git status

# Force pull (discard local changes)
git fetch origin && git reset --hard origin/main

# Restart sync service
sudo systemctl restart ai-vault-sync
```

## VM Outage Recovery (Platinum)

| Scenario | Impact | Recovery |
|----------|--------|----------|
| Cloud VM down | No new email drafts, no health signals | Local operates independently |
| VM reboots | Services restart via systemd | Automatic recovery |
| VM disk full | Health monitor alerts (if still running) | Clean logs/backups, expand disk |
| Odoo down | No invoice operations | `docker compose restart odoo` |
| Network outage | Vault sync fails | Auto-retry on next cycle |

### VM Recovery Steps
1. SSH into VM: `ssh ai-employee@<ip>`
2. Check services: `systemctl status ai-cloud-orchestrator ai-vault-sync ai-health-monitor`
3. Check Docker: `docker compose -f /opt/ai-employee/odoo/docker-compose.yml ps`
4. Check logs: `journalctl -u ai-cloud-orchestrator --since "1 hour ago"`
5. Restart if needed: `systemctl restart ai-cloud-orchestrator`

## Links
- [[Watchers_Status]] - Current watcher status
- [[Dashboard]] - System health overview
- [[Cloud_Status]] - Cloud VM status
- [[Sync_Config]] - Vault sync configuration
