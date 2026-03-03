---
name: odoo-accounting
description: |
  Odoo ERP integration for draft invoice creation (Cloud) and posting (Local-only).
  Uses JSON-RPC to communicate with Odoo 19. Cloud agents can create drafts,
  but only Local agents can post (confirm) invoices.
user_invocable: true
---

# Odoo Accounting (Platinum Tier)

## What This Skill Does
- Creates draft invoices in Odoo via JSON-RPC
- Lists draft invoices for review
- Posts (confirms) invoices — **Local agent only**
- Writes Odoo activity signals to `Updates/`

## How to Use

### List Draft Invoices
```bash
uv run python watchers/odoo_mcp.py list --url http://localhost:8069 --db odoo --user admin --password admin
```

### Create Draft Invoice (Cloud or Local)
```bash
uv run python watchers/odoo_mcp.py create --partner "John Doe" --amount 500 --description "Consulting"
```

### Post Invoice (Local Only)
```bash
uv run python watchers/odoo_mcp.py post --invoice-id 42 --agent local
```

### In Python
```python
from odoo_mcp import OdooClient

client = OdooClient(url="http://localhost:8069", db="odoo", user="admin", password="admin")
client.authenticate()

# Cloud can do this:
invoice_id = client.create_draft_invoice("Customer", [{"name": "Service", "price_unit": 100}])

# Only Local can do this:
client.post_invoice(invoice_id, agent="local")
```

## Work-Zone Rules
| Action | Cloud | Local |
|--------|-------|-------|
| Create draft invoice | YES | YES |
| List invoices | YES | YES |
| Post (confirm) invoice | NO | YES |

## Odoo Setup
- Docker Compose: `odoo/docker-compose.yml`
- Nginx reverse proxy: `odoo/nginx/conf.d/odoo.conf`
- Daily backup: `odoo/backup.sh` (cron at 2 AM)
- Config: `AI_Employee_Vault/Odoo_Config.md`

## Environment Variables
```
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USER=admin
ODOO_PASSWORD=<from secrets>
```
