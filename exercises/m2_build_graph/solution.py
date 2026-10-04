"""Module 2 - build and run a multi-node agent graph.

Three kinds of node:  model (calls the LLM) | validation (checks) | action (does).
Run:  python exercises/m2_build_graph/solution.py
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


# STEP 1: define the state schema. Every node reads this dict and returns a partial update.
# >>> SOLUTION
class State(TypedDict, total=False):
    doc_id: str
    raw_text: str
    invoice: dict           # InvoiceFields as a dict
    errors: list[str]
    disposition: str
    approver: str
    status: str
# <<< SOLUTION


def extract(state: State) -> dict:
    """MODEL node: ask for a structured output (InvoiceFields), not free text."""
    # STEP 2: call llm.structured(...) with the InvoiceFields schema and return {"invoice": ...}
    # >>> SOLUTION
    prompt = f"Extract the invoice fields.\n<invoice>\n{state['raw_text']}\n</invoice>"
    invoice = get_llm().structured(InvoiceFields, prompt, system=SYSTEM)
    return {"invoice": invoice.model_dump()}
    # <<< SOLUTION


def validate(state: State) -> dict:
    """VALIDATION node: deterministic arithmetic and completeness checks."""
    # STEP 3: use rules.validate_invoice and return {"errors": [...]}
    # >>> SOLUTION
    return {"errors": rules.validate_invoice(state["invoice"])}
    # <<< SOLUTION


def route_after_validate(state: State) -> Literal["decide", "needs_review"]:
    """ROUTER: a pure function of state. It returns the NAME of the next node."""
    # STEP 4: send invoices with errors to needs_review, the rest to decide
    # >>> SOLUTION
    return "needs_review" if state["errors"] else "decide"
    # <<< SOLUTION


def decide(state: State) -> dict:
    """ACTION node: apply the approval matrix to the invoice total (no exceptions yet)."""
    decision = rules.decide([], state["invoice"]["total"])
    return {"disposition": decision["disposition"], "approver": decision["approver"], "status": "DECIDED"}


def needs_review(state: State) -> dict:
    """ACTION node: the fallback path."""
    return {"disposition": "HOLD", "approver": "AP_ANALYST", "status": "NEEDS_REVIEW"}


# STEP 5: wire the graph: START -> extract -> validate -> (router) -> decide | needs_review -> END
# >>> SOLUTION
builder = StateGraph(State)
builder.add_node("extract", extract)
builder.add_node("validate", validate)
builder.add_node("decide", decide)
builder.add_node("needs_review", needs_review)
builder.add_edge(START, "extract")
builder.add_edge("extract", "validate")
builder.add_conditional_edges("validate", route_after_validate)
builder.add_edge("decide", END)
builder.add_edge("needs_review", END)
graph = builder.compile()
# <<< SOLUTION

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
