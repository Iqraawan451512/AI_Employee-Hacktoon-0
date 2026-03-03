---
type: status
last_updated: 2026-03-03
tier: platinum
---

# Cloud VM Status

## VM Details
| Setting | Value |
|---------|-------|
| Provider | `<configure>` |
| OS | Ubuntu 24.04 LTS |
| IP | `<configure>` |
| SSH | `ssh ai-employee@<ip>` |

## Services
| Service | systemd Unit | Status | Port |
|---------|-------------|--------|------|
| Cloud Orchestrator | `ai-cloud-orchestrator.service` | Pending setup | — |
| Gmail Watcher | `ai-gmail-watcher.service` | Pending setup | — |
| Vault Sync | `ai-vault-sync.service` | Pending setup | — |
| Health Monitor | `ai-health-monitor.service` | Pending setup | — |
| Odoo | `docker (ai-employee-odoo)` | Pending setup | 8069 |
| PostgreSQL | `docker (ai-employee-postgres)` | Pending setup | 5432 |
| Nginx | `docker (ai-employee-nginx)` | Pending setup | 80/443 |

## Health Status
_Health signals are written to `Updates/HEALTH_*.md` by the health monitor._
_See [[Dashboard]] for merged health status._

**Last Health Check**: Pending first run

## Service Management
```bash
# Start all services
sudo systemctl start ai-vault-sync ai-cloud-orchestrator ai-gmail-watcher ai-health-monitor

# Check status
sudo systemctl status ai-cloud-orchestrator
sudo systemctl status ai-gmail-watcher

# View logs
journalctl -u ai-cloud-orchestrator -f
journalctl -u ai-vault-sync --since "1 hour ago"

# Restart
sudo systemctl restart ai-cloud-orchestrator

# Odoo
cd /opt/ai-employee/odoo && docker compose up -d
docker compose logs -f odoo
```

## Odoo Access
| Setting | Value |
|---------|-------|
| URL | `https://<domain>` or `http://<ip>:8069` |
| Database | See [[Odoo_Config]] |
| Backup | Daily at 2 AM via `odoo/backup.sh` |

## Related
- [[Sync_Config]] - Vault sync configuration
- [[Odoo_Config]] - Odoo connection details
- [[Architecture]] - System architecture
- [[Watchers_Status]] - All watcher status
