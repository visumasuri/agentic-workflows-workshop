"""Deterministic finance rules: the three-way match and the disposition decision.

Design principle for finance agents: the model reads and writes; code decides.
Anything an auditor will re-perform (tolerances, thresholds, approvers) lives here.
"""
from __future__ import annotations

from .config import AP_MANAGER_LIMIT, AUTO_APPROVE_LIMIT, PRICE_TOLERANCE_PCT

# Highest priority first. The first exception found in this order drives the outcome.
PRIORITY = ["PROMPT_INJECTION", "DUPLICATE", "VENDOR_INACTIVE", "BANK_DETAIL_CHANGE",
            "MISSING_PO", "QTY_MISMATCH", "PRICE_VARIANCE"]

OUTCOME = {  # exception -> (disposition, approver, policy section)
    "PROMPT_INJECTION": ("HOLD", "SECURITY_REVIEW", "AP-POL-05 §5.1"),
    "DUPLICATE": ("REJECT", "NONE", "AP-POL-03 §3.2"),
    "VENDOR_INACTIVE": ("HOLD", "VENDOR_MASTER_TEAM", "AP-POL-04 §4.2"),
    "BANK_DETAIL_CHANGE": ("HOLD", "VENDOR_MASTER_TEAM", "AP-POL-04 §4.1"),
    "MISSING_PO": ("ROUTE_FOR_APPROVAL", "COST_CENTRE_OWNER", "AP-POL-01 §1.3"),
    "QTY_MISMATCH": ("HOLD", "RECEIVING", "AP-POL-01 §1.2"),
    "PRICE_VARIANCE": ("ROUTE_FOR_APPROVAL", "BUYER", "AP-POL-01 §1.1"),
}


def three_way_match(invoice: dict, po_lines: list[dict], grn_lines: list[dict]) -> list[dict]:
    """Compare invoice lines with PO price and received quantity."""
    found = []
    if not invoice.get("po_number") or not po_lines:
        return [{"type": "MISSING_PO", "detail": "Invoice quotes no valid purchase order"}]
    po = {l["sku"]: l for l in po_lines}
    received: dict[str, float] = {}
    for g in grn_lines:
        received[g["sku"]] = received.get(g["sku"], 0) + g["qty_received"]
    for line in invoice["lines"]:
        po_line = po.get(line["sku"])
        if po_line is None:
            found.append({"type": "MISSING_PO", "detail": f"SKU {line['sku']} is not on {invoice['po_number']}"})
            continue
        variance = (line["unit_price"] - po_line["unit_price"]) / po_line["unit_price"] * 100
        if abs(variance) > PRICE_TOLERANCE_PCT:
            found.append({"type": "PRICE_VARIANCE",
                          "detail": f"{line['sku']}: invoiced {line['unit_price']:.2f} vs PO "
                                    f"{po_line['unit_price']:.2f} ({variance:+.1f}%, tolerance {PRICE_TOLERANCE_PCT:.0f}%)"})
        got = received.get(line["sku"], 0)
        if line["qty"] > got:
            found.append({"type": "QTY_MISMATCH",
                          "detail": f"{line['sku']}: invoiced {line['qty']:g} vs received {got:g}"})
    return found


def decide(exceptions: list[dict], total: float) -> dict:
    """Turn the exception list and invoice total into disposition, approver and policy reference."""
    types = {e["type"] for e in exceptions}
    for name in PRIORITY:
        if name in types:
            disposition, approver, policy = OUTCOME[name]
            return {"primary_exception": name, "disposition": disposition, "approver": approver, "policy": policy}
    if total < AUTO_APPROVE_LIMIT:
        return {"primary_exception": "NONE", "disposition": "AUTO_APPROVE", "approver": "NONE", "policy": "AP-POL-02 §2.1"}
    if total <= AP_MANAGER_LIMIT:
        return {"primary_exception": "NONE", "disposition": "ROUTE_FOR_APPROVAL", "approver": "AP_MANAGER", "policy": "AP-POL-02 §2.2"}
    return {"primary_exception": "NONE", "disposition": "ROUTE_FOR_APPROVAL", "approver": "CONTROLLER", "policy": "AP-POL-02 §2.3"}


def validate_invoice(inv: dict) -> list[str]:
    """Arithmetic and completeness checks on extracted fields. Returns a list of problems."""
    errors = []
    for field in ("invoice_number", "vendor_id", "currency", "invoice_date"):
        if not inv.get(field):
            errors.append(f"missing {field}")
    if not inv.get("lines"):
        return errors + ["no line items"]
    for l in inv["lines"]:
        if abs(l["qty"] * l["unit_price"] - l["amount"]) > 0.01:
            errors.append(f"line {l['sku']}: qty {l['qty']:g} x unit price {l['unit_price']:g} != amount {l['amount']:g}")
    if abs(sum(l["amount"] for l in inv["lines"]) - inv["subtotal"]) > 0.01:
        errors.append("sum of line amounts != subtotal")
    if abs(inv["subtotal"] + inv["tax"] - inv["total"]) > 0.01:
        errors.append("subtotal + tax != total")
    return errors
