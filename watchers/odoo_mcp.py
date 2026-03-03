"""
Odoo MCP Client for AI Employee (Platinum Tier).

JSON-RPC client for Odoo ERP. Provides draft invoice creation (Cloud),
invoice posting (Local-only), and listing operations.

Safety: post_invoice() is marked Local-only and will refuse to run
if called with agent="cloud".

Usage:
    from odoo_mcp import OdooClient

    client = OdooClient(url="http://localhost:8069", db="odoo", user="admin", password="admin")
    client.authenticate()
    draft_id = client.create_draft_invoice(partner="John Doe", lines=[...])
    invoices = client.list_draft_invoices()
    client.post_invoice(invoice_id=draft_id, agent="local")  # Local-only!
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

DEFAULT_VAULT = Path(__file__).parent.parent / "AI_Employee_Vault"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("OdooMCP")


class OdooClient:
    """JSON-RPC client for Odoo ERP."""

    def __init__(
        self,
        url: str = None,
        db: str = None,
        user: str = None,
        password: str = None,
    ):
        self.url = url or os.environ.get("ODOO_URL", "http://localhost:8069")
        self.db = db or os.environ.get("ODOO_DB", "odoo")
        self.user = user or os.environ.get("ODOO_USER", "admin")
        self.password = password or os.environ.get("ODOO_PASSWORD", "admin")
        self.uid = None
        self._request_id = 0

    def _jsonrpc(self, service: str, method: str, args: list) -> dict:
        """Make a JSON-RPC call to Odoo."""
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": service,
                "method": method,
                "args": args,
            },
            "id": self._request_id,
        }

        data = json.dumps(payload).encode("utf-8")
        req = Request(
            f"{self.url}/jsonrpc",
            data=data,
            headers={"Content-Type": "application/json"},
        )

        try:
            response = urlopen(req, timeout=30)
            result = json.loads(response.read().decode("utf-8"))
        except URLError as e:
            logger.error(f"Odoo connection error: {e}")
            raise ConnectionError(f"Cannot reach Odoo at {self.url}: {e}") from e

        if result.get("error"):
            error = result["error"]
            msg = error.get("data", {}).get("message", error.get("message", str(error)))
            raise RuntimeError(f"Odoo RPC error: {msg}")

        return result.get("result")

    def authenticate(self) -> int:
        """Authenticate with Odoo and return user ID."""
        self.uid = self._jsonrpc("common", "authenticate", [self.db, self.user, self.password, {}])
        if not self.uid:
            raise RuntimeError(f"Odoo authentication failed for user '{self.user}'")
        logger.info(f"Authenticated as {self.user} (uid={self.uid})")
        return self.uid

    def _execute(self, model: str, method: str, *args, **kwargs):
        """Execute an Odoo model method."""
        if not self.uid:
            self.authenticate()
        return self._jsonrpc(
            "object",
            "execute_kw",
            [self.db, self.uid, self.password, model, method, list(args), kwargs],
        )

    def create_draft_invoice(
        self,
        partner_name: str,
        lines: list[dict],
        move_type: str = "out_invoice",
    ) -> int:
        """Create a draft invoice in Odoo.

        Args:
            partner_name: Customer/partner name
            lines: List of dicts with 'name', 'quantity', 'price_unit'
            move_type: Invoice type (default: out_invoice = customer invoice)

        Returns:
            Invoice ID
        """
        # Find or create partner
        partner_ids = self._execute(
            "res.partner", "search", [("name", "ilike", partner_name)], limit=1,
        )
        if partner_ids:
            partner_id = partner_ids[0]
        else:
            partner_id = self._execute("res.partner", "create", {"name": partner_name})
            logger.info(f"Created partner: {partner_name} (id={partner_id})")

        # Build invoice lines
        invoice_lines = []
        for line in lines:
            invoice_lines.append((0, 0, {
                "name": line.get("name", "Service"),
                "quantity": line.get("quantity", 1),
                "price_unit": line.get("price_unit", 0),
            }))

        # Create draft invoice
        invoice_id = self._execute("account.move", "create", {
            "move_type": move_type,
            "partner_id": partner_id,
            "invoice_line_ids": invoice_lines,
            "invoice_date": datetime.now().strftime("%Y-%m-%d"),
        })

        logger.info(f"Created draft invoice #{invoice_id} for {partner_name}")
        return invoice_id

    def list_draft_invoices(self, limit: int = 20) -> list[dict]:
        """List draft invoices.

        Returns:
            List of invoice dicts with id, partner, amount, date.
        """
        invoice_ids = self._execute(
            "account.move",
            "search",
            [("state", "=", "draft"), ("move_type", "=", "out_invoice")],
            limit=limit,
            order="create_date desc",
        )

        if not invoice_ids:
            return []

        invoices = self._execute(
            "account.move",
            "read",
            invoice_ids,
            fields=["id", "name", "partner_id", "amount_total", "invoice_date", "state"],
        )

        return invoices

    def post_invoice(self, invoice_id: int, agent: str = "local") -> bool:
        """Post (confirm) a draft invoice. LOCAL-ONLY operation.

        Args:
            invoice_id: The invoice ID to post
            agent: Must be "local" — cloud agents are blocked

        Returns:
            True if successful
        """
        if agent != "local":
            raise PermissionError(
                f"post_invoice is Local-only. Called with agent='{agent}'. "
                "Cloud agents can only create draft invoices."
            )

        self._execute("account.move", "action_post", [invoice_id])
        logger.info(f"Posted invoice #{invoice_id} (agent=local)")
        return True

    def write_vault_signal(self, vault_path: Path, action: str, detail: str):
        """Write an Odoo action signal to Updates/."""
        updates_dir = vault_path / "Updates"
        updates_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        signal = updates_dir / f"ODOO_{ts}.md"
        signal.write_text(
            f"""---
type: odoo_update
agent: cloud
domain: finance
action: {action}
timestamp: {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
---

# Odoo Update: {action}

{detail}
""",
            encoding="utf-8",
        )


# CLI for manual testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI Employee Odoo MCP Client")
    parser.add_argument("action", choices=["list", "create", "post"],
                        help="Action to perform")
    parser.add_argument("--url", type=str, default="http://localhost:8069")
    parser.add_argument("--db", type=str, default="odoo")
    parser.add_argument("--user", type=str, default="admin")
    parser.add_argument("--password", type=str, default="admin")
    parser.add_argument("--partner", type=str, default="Test Customer")
    parser.add_argument("--amount", type=float, default=100.0)
    parser.add_argument("--description", type=str, default="Service")
    parser.add_argument("--invoice-id", type=int, help="Invoice ID for post action")
    parser.add_argument("--agent", type=str, default="local", choices=["cloud", "local"])
    args = parser.parse_args()

    client = OdooClient(url=args.url, db=args.db, user=args.user, password=args.password)
    client.authenticate()

    if args.action == "list":
        invoices = client.list_draft_invoices()
        print(json.dumps(invoices, indent=2, default=str))

    elif args.action == "create":
        invoice_id = client.create_draft_invoice(
            partner_name=args.partner,
            lines=[{"name": args.description, "quantity": 1, "price_unit": args.amount}],
        )
        print(f"Created draft invoice: #{invoice_id}")

    elif args.action == "post":
        if not args.invoice_id:
            print("Error: --invoice-id required for post action")
            sys.exit(1)
        client.post_invoice(args.invoice_id, agent=args.agent)
        print(f"Posted invoice: #{args.invoice_id}")
