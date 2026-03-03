---
type: config
last_updated: 2026-03-03
tier: platinum
---

# Odoo Configuration

## Connection Details
| Setting | Value |
|---------|-------|
| Version | Odoo 19 (Community) |
| URL | `http://localhost:8069` (internal) |
| External | `https://<domain>` (via Nginx) |
| Database | `odoo` |
| API | JSON-RPC at `/jsonrpc` |

**Note**: Credentials are stored in `secrets/` or environment variables. Never commit passwords to the vault.

## Docker Stack
| Container | Image | Port |
|-----------|-------|------|
| `ai-employee-odoo` | `odoo:19` | 8069 |
| `ai-employee-postgres` | `postgres:16` | 5432 |
| `ai-employee-nginx` | `nginx:alpine` | 80, 443 |

## Environment Variables
Set in `odoo/.env` (gitignored):
```
POSTGRES_USER=odoo
POSTGRES_PASSWORD=<secret>
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USER=admin
ODOO_PASSWORD=<secret>
```

## Work-Zone Rules
| Operation | Cloud Agent | Local Agent |
|-----------|------------|-------------|
| Create draft invoices | YES | YES |
| List draft invoices | YES | YES |
| Post (confirm) invoices | NO | YES |
| View reports | YES | YES |
| Make payments | NO | YES |

## Backup
- Script: `odoo/backup.sh`
- Schedule: Daily at 2:00 AM (cron)
- Retention: 7 days
- Location: `/opt/ai-employee/backups/odoo/`
- Method: `pg_dump` via Docker exec

### Setup Cron
```bash
echo "0 2 * * * /opt/ai-employee/odoo/backup.sh >> /var/log/odoo-backup.log 2>&1" | crontab -
```

## API Usage
```python
from odoo_mcp import OdooClient

client = OdooClient()  # reads from env vars
client.authenticate()
client.create_draft_invoice("Customer", [{"name": "Service", "price_unit": 100}])
client.list_draft_invoices()
client.post_invoice(42, agent="local")  # Local only!
```

## Related
- [[Cloud_Status]] - Cloud VM status
- [[Bank_Transactions]] - Financial tracking
- [[Approval_Policy]] - Invoice approval rules
