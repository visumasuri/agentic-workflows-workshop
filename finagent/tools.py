"""Business tools the agent can call. Each reads a CSV that stands in for an ERP API."""
from __future__ import annotations

import csv
import hashlib
from functools import lru_cache

from .config import DATA, MAX_TOOL_RETRIES
from .tracing import record_tool


class ToolError(Exception):
    """A tool failed in a way the caller may retry (timeout, 5xx, lock)."""


class AccessDenied(Exception):
    """The caller's role is not allowed to use this tool."""


# Fault injection for the failure-scenario exercises: {"lookup_grn": 2} makes the
# first two calls to lookup_grn raise ToolError.
FAULTS: dict[str, int] = {}

# Access control: which role may call which tool.
PERMISSIONS = {
    "ap_agent": {"lookup_po", "lookup_grn", "lookup_vendor", "check_history", "post_to_ledger"},
    "read_only": {"lookup_po", "lookup_grn", "lookup_vendor", "check_history"},
}


@lru_cache(maxsize=None)
def _table(name: str) -> list[dict]:
    with (DATA / name).open() as fh:
        return list(csv.DictReader(fh))


def _maybe_fail(tool: str) -> None:
    if FAULTS.get(tool, 0) > 0:
        FAULTS[tool] -= 1
        raise ToolError(f"{tool}: upstream ERP timeout after 30s")


def _authorise(tool: str, role: str) -> None:
    if tool not in PERMISSIONS.get(role, set()):
        raise AccessDenied(f"role '{role}' may not call {tool}")


def lookup_po(po_number: str, role: str = "ap_agent") -> list[dict]:
    """Return the PO lines for a purchase order number (empty list if unknown)."""
    _authorise("lookup_po", role)
    _maybe_fail("lookup_po")
    return [{**r, "qty_ordered": float(r["qty_ordered"]), "unit_price": float(r["unit_price"])}
            for r in _table("purchase_orders.csv") if r["po_number"] == po_number]


def lookup_grn(po_number: str, role: str = "ap_agent") -> list[dict]:
    """Return goods receipt lines for a purchase order number."""
    _authorise("lookup_grn", role)
    _maybe_fail("lookup_grn")
    return [{**r, "qty_received": float(r["qty_received"])}
            for r in _table("goods_receipts.csv") if r["po_number"] == po_number]


def lookup_vendor(vendor_id: str, role: str = "ap_agent") -> dict | None:
    """Return the vendor master record, or None if the vendor is unknown."""
    _authorise("lookup_vendor", role)
    _maybe_fail("lookup_vendor")
    return next((dict(r) for r in _table("vendor_master.csv") if r["vendor_id"] == vendor_id), None)


def check_history(vendor_id: str, invoice_number: str, role: str = "ap_agent") -> list[dict]:
    """Return posted invoices with the same vendor and invoice number."""
    _authorise("check_history", role)
    _maybe_fail("check_history")
    return [dict(r) for r in _table("posted_invoices.csv")
            if r["vendor_id"] == vendor_id and r["invoice_number"] == invoice_number]


def post_to_ledger(invoice: dict, approval: dict | None = None, role: str = "ap_agent") -> dict:
    """Post an approved invoice. Postings of 10,000 or more need a recorded human approval."""
    _authorise("post_to_ledger", role)
    if invoice["total"] >= 10_000 and not (approval and approval.get("approved")):
        raise AccessDenied("posting of 10,000 or more needs a recorded human approval (AP-POL-05 §5.3)")
    doc = hashlib.sha1(invoice["invoice_number"].encode()).hexdigest()[:8].upper()
    return {"ledger_doc": f"AP-{doc}", "amount": invoice["total"], "currency": invoice["currency"]}


def call_with_retry(fn, *args, retries: int = MAX_TOOL_RETRIES, **kwargs):
    """Retry a tool on ToolError with exponential backoff (recorded, not slept, in the workshop)."""
    for attempt in range(1, retries + 1):
        try:
            result = fn(*args, **kwargs)
            record_tool(latency_ms=40.0)
            return result
        except ToolError:
            record_tool(latency_ms=30_000 + 500 * 2 ** attempt, retried=True)
            if attempt == retries:
                raise
