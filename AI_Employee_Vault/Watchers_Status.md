---
last_updated: 2026-03-03
tier: platinum
---

# Watchers Status

## Active Watchers

| Watcher | Location | Source | Method | Status | Interval | Script |
|---------|----------|--------|--------|--------|----------|--------|
| File System | Local | `/Inbox` folder | watchdog | Ready | Continuous | `watchers/filesystem_watcher.py` |
| Gmail | Cloud | Gmail API | OAuth2 polling | Ready | 120s | `watchers/gmail_watcher.py` |
| WhatsApp | Local | WhatsApp Web | Playwright | Ready | 30s | `watchers/whatsapp_watcher.py` |
| LinkedIn | Local | LinkedIn Web | Playwright | Ready | On-demand | `watchers/linkedin_poster.py` |
| Cloud Orchestrator | Cloud | Vault domains | Claim-by-move | Pending Setup | 60s | `watchers/cloud_orchestrator.py` |
| Local Orchestrator | Local | Vault domains | Claim-by-move | Ready | 60s | `watchers/orchestrator.py --mode local` |
| Vault Sync | Cloud+Local | Git repo | git pull/push | Pending Setup | 30s | `scripts/vault_sync.py` |
| Dashboard Merger | Local | `Updates/` | File scan | Ready | 30s | `watchers/dashboard_merger.py` |
| Health Monitor | Cloud | Services | Process/HTTP check | Pending Setup | 60s | `watchers/health_monitor.py` |
| Odoo Client | Cloud+Local | Odoo API | JSON-RPC | Pending Setup | On-demand | `watchers/odoo_mcp.py` |

## How to Start Each Watcher

### File System Watcher (Local)
```bash
cd watchers && uv run python filesystem_watcher.py --vault-path ../AI_Employee_Vault
```

### Gmail Watcher (Cloud)
```bash
cd watchers && uv run python gmail_watcher.py --vault-path ../AI_Employee_Vault --credentials ../credentials.json
```
Or via systemd: `sudo systemctl start ai-gmail-watcher`

### WhatsApp Watcher (Local)
```bash
# First run (headed mode - scan QR code)
cd watchers && uv run python whatsapp_watcher.py --vault-path ../AI_Employee_Vault --headed

# Normal headless run
cd watchers && uv run python whatsapp_watcher.py --vault-path ../AI_Employee_Vault
```

### Cloud Orchestrator (Cloud)
```bash
cd watchers && uv run python cloud_orchestrator.py --vault-path ../AI_Employee_Vault
```
Or via systemd: `sudo systemctl start ai-cloud-orchestrator`

### Local Orchestrator (Local)
```bash
cd watchers && uv run python orchestrator.py --vault-path ../AI_Employee_Vault --mode local
```

### Vault Sync (Cloud or Local)
```bash
uv run python scripts/vault_sync.py --vault AI_Employee_Vault --agent cloud  # on cloud
uv run python scripts/vault_sync.py --vault AI_Employee_Vault --agent local  # on local
```
Or via systemd (cloud): `sudo systemctl start ai-vault-sync`

### Health Monitor (Cloud)
```bash
cd watchers && uv run python health_monitor.py --vault-path ../AI_Employee_Vault
```
Or via systemd: `sudo systemctl start ai-health-monitor`

### LinkedIn Poster (Local)
```bash
# Create a draft
cd watchers && uv run python linkedin_poster.py draft --vault-path ../AI_Employee_Vault --topic "your topic"

# Check for approved posts and publish
cd watchers && uv run python linkedin_poster.py check-approved --vault-path ../AI_Employee_Vault
```

## Keyword Filters

### Gmail Watcher
- **Urgent**: urgent, asap, emergency, critical
- **Business**: invoice, payment, overdue, contract, deadline, proposal

### WhatsApp Watcher
- **Urgent**: urgent, asap, emergency, critical
- **Financial**: invoice, payment, price, pricing, quote, budget, overdue
- **Action**: help, need, request, order, deadline

## Authentication Status

| Service | Auth Method | Token Location | Status |
|---------|------------|----------------|--------|
| Gmail | OAuth2 | `watchers/token.json` | Authenticated |
| WhatsApp | QR Code | `watchers/whatsapp_session/` | Needs first login |
| LinkedIn | Browser session | Playwright MCP | Needs first login |
| Odoo | Username/Password | `secrets/` or env vars | Pending setup |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Gmail token expired | Delete `watchers/token.json` and re-run watcher |
| WhatsApp session lost | Run with `--headed` and re-scan QR code |
| Watcher stops running | Use watchdog or systemd for auto-restart |
| No emails detected | Try broader query: `--query "is:unread"` |
| Vault sync conflicts | Check `.conflict` files, see [[Sync_Config]] |
| Cloud service down | Check `journalctl -u <service>`, see [[Cloud_Status]] |
| Odoo unreachable | Check `docker compose logs odoo`, see [[Odoo_Config]] |
