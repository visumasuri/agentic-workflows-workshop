"""Module 2 - build and run a multi-node agent graph.

Three kinds of node:  model (calls the LLM) | validation (checks) | action (does).
Run:  python exercises/m2_build_graph/starter.py
"""
import pathlib
import sys
from typing import Literal, TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from langgraph.graph import END, START, StateGraph

from finagent import rules
from finagent.graph import SYSTEM, load_invoice
from finagent.llm import get_llm
from finagent.schemas import InvoiceFields


# TODO 1: define the state schema. Every node reads this dict and returns a partial update.
raise NotImplementedError("Complete the TODO above")


def extract(state: State) -> dict:
    """MODEL node: ask for a structured output (InvoiceFields), not free text."""
    # TODO 2: call llm.structured(...) with the InvoiceFields schema and return {"invoice": ...}
    raise NotImplementedError("Complete the TODO above")


def validate(state: State) -> dict:
    """VALIDATION node: deterministic arithmetic and completeness checks."""
    # TODO 3: use rules.validate_invoice and return {"errors": [...]}
    raise NotImplementedError("Complete the TODO above")


def route_after_validate(state: State) -> Literal["decide", "needs_review"]:
    """ROUTER: a pure function of state. It returns the NAME of the next node."""
    # TODO 4: send invoices with errors to needs_review, the rest to decide
    raise NotImplementedError("Complete the TODO above")


def decide(state: State) -> dict:
    """ACTION node: apply the approval matrix to the invoice total (no exceptions yet)."""
    decision = rules.decide([], state["invoice"]["total"])
    return {"disposition": decision["disposition"], "approver": decision["approver"], "status": "DECIDED"}


def needs_review(state: State) -> dict:
    """ACTION node: the fallback path."""
    return {"disposition": "HOLD", "approver": "AP_ANALYST", "status": "NEEDS_REVIEW"}


# TODO 5: wire the graph: START -> extract -> validate -> (router) -> decide | needs_review -> END
raise NotImplementedError("Complete the TODO above")

if __name__ == "__main__":
    print(f"{'doc':<8}{'invoice':<14}{'total':>12}  {'status':<14}{'disposition':<20}{'approver':<12}errors")
    for doc_id in ("DOC-01", "DOC-07", "DOC-11"):
        out = graph.invoke({"doc_id": doc_id, "raw_text": load_invoice(doc_id)})
        inv = out["invoice"]
        print(f"{doc_id:<8}{inv['invoice_number']:<14}{inv['total']:>12,.2f}  {out['status']:<14}"
              f"{out['disposition']:<20}{out['approver']:<12}{'; '.join(out['errors']) or '-'}")
    print("\nStreaming DOC-01 node by node:")
    for step in graph.stream({"doc_id": "DOC-01", "raw_text": load_invoice("DOC-01")}, stream_mode="updates"):
        for node, update in step.items():
            print(f"  {node:<10} wrote {sorted(update)}")
    print("\n" + graph.get_graph().draw_mermaid())
