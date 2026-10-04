"""Module 3 - tools, retrieval and context assembly.

Adds to the Module 2 graph: four tool nodes that run in parallel, a deterministic
match, policy retrieval, and a grounded memo with citations. Tool errors degrade
to a HOLD instead of crashing the run.
Run:  python exercises/m3_tools_rag/solution.py
"""
import operator
import pathlib
import sys
from typing import Annotated, Optional, TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from langgraph.graph import END, START, StateGraph

from finagent import rules, tools
from finagent.graph import SYSTEM, load_invoice
from finagent.llm import get_llm
from finagent.rag import PolicyRetriever
from finagent.schemas import InvoiceFields, ResolutionMemo

retriever = PolicyRetriever()


class State(TypedDict, total=False):
    doc_id: str
    raw_text: str
    invoice: dict
    po_lines: list[dict]
    grn_lines: list[dict]
    vendor: Optional[dict]
    history_hits: list[dict]
    tools_called: Annotated[list[str], operator.add]   # reducer: parallel nodes each append
    tool_errors: Annotated[list[str], operator.add]
    exceptions: list[dict]
    primary_exception: str
    disposition: str
    approver: str
    policy_chunks: list[dict]
    memo: dict


def extract(state: State) -> dict:
    prompt = f"Extract the invoice fields.\n<invoice>\n{state['raw_text']}\n</invoice>"
    return {"invoice": get_llm().structured(InvoiceFields, prompt, system=SYSTEM).model_dump()}


# ---------------------------------------------------------------- tool nodes
def lookup_po(state: State) -> dict:
    try:
        lines = tools.call_with_retry(tools.lookup_po, state["invoice"]["po_number"])
        return {"po_lines": lines, "tools_called": ["lookup_po"]}
    except tools.ToolError as exc:
        return {"tools_called": ["lookup_po"], "tool_errors": [str(exc)]}


def lookup_grn(state: State) -> dict:
    # STEP 1: call tools.lookup_grn through tools.call_with_retry. On ToolError, do not
    # raise: return the error in "tool_errors" so the graph can degrade gracefully.
    # >>> SOLUTION
    try:
        lines = tools.call_with_retry(tools.lookup_grn, state["invoice"]["po_number"])
        return {"grn_lines": lines, "tools_called": ["lookup_grn"]}
    except tools.ToolError as exc:
        return {"tools_called": ["lookup_grn"], "tool_errors": [str(exc)]}
    # <<< SOLUTION


def lookup_vendor(state: State) -> dict:
    return {"vendor": tools.call_with_retry(tools.lookup_vendor, state["invoice"]["vendor_id"]),
            "tools_called": ["lookup_vendor"]}


def check_history(state: State) -> dict:
    inv = state["invoice"]
    return {"history_hits": tools.call_with_retry(tools.check_history, inv["vendor_id"], inv["invoice_number"]),
            "tools_called": ["check_history"]}


def choose_tools(state: State) -> list[str]:
    """Tool selection as a router: returning a LIST fans out and runs the nodes in parallel."""
    # STEP 2: always look up the vendor and the history; only look up PO and GRN when a PO is quoted.
    # >>> SOLUTION
    selected = ["lookup_vendor", "check_history"]
    if state["invoice"].get("po_number"):
        selected += ["lookup_po", "lookup_grn"]
    return selected
    # <<< SOLUTION


# ---------------------------------------------------------------- match (deterministic)
def match(state: State) -> dict:
    inv = state["invoice"]
    if state.get("tool_errors"):
        return {"exceptions": [{"type": "TOOL_FAILURE", "detail": e} for e in state["tool_errors"]],
                "primary_exception": "TOOL_FAILURE", "disposition": "HOLD", "approver": "AP_ANALYST"}
    found = rules.three_way_match(inv, state.get("po_lines", []), state.get("grn_lines", []))
    if not state.get("vendor") or state["vendor"]["status"] != "ACTIVE":
        found.append({"type": "VENDOR_INACTIVE", "detail": f"Vendor {inv['vendor_id']} is not ACTIVE"})
    for hit in state.get("history_hits", []):
        found.append({"type": "DUPLICATE", "detail": f"{hit['invoice_number']} was posted on {hit['posted_date']}"})
    d = rules.decide(found, inv["total"])
    return {"exceptions": found, "primary_exception": d["primary_exception"],
            "disposition": d["disposition"], "approver": d["approver"]}


# ---------------------------------------------------------------- retrieval + grounded generation
def retrieve(state: State) -> dict:
    # STEP 3: build a search query from the primary exception and its details, retrieve k=3 sections.
    # >>> SOLUTION
    exc = state["primary_exception"]
    details = " ".join(e["detail"] for e in state["exceptions"] if e["type"] == exc)
    query = f"{exc.replace('_', ' ')} {details}" if exc != "NONE" else \
        f"fully matched invoice approval required before posting {state['approver'].replace('_', ' ')}"
    return {"policy_chunks": retriever.search(query, k=3)}
    # <<< SOLUTION


def draft_memo(state: State) -> dict:
    # STEP 4: assemble the context (facts + retrieved policy inside <policy> tags, each section
    # labelled with its id) and ask for a ResolutionMemo. The model may cite only what it was shown.
    # >>> SOLUTION
    policy = "\n".join(f"[{c['id']}] {c['title']}: {c['text']}" for c in state["policy_chunks"])
    payload = {"invoice": state["invoice"], "exceptions": state["exceptions"],
               "primary_exception": state["primary_exception"], "disposition": state["disposition"],
               "approver": state["approver"], "policy_chunks": state["policy_chunks"],
               "policy": rules.OUTCOME.get(state["primary_exception"], (None, None, None))[2]}
    prompt = (f"Write a resolution memo for the approver.\nInvoice: {state['invoice']}\n"
              f"Exceptions: {state['exceptions']}\nDisposition: {state['disposition']}, owner {state['approver']}\n"
              f"<policy>\n{policy}\n</policy>")
    memo = get_llm().structured(ResolutionMemo, prompt, system=SYSTEM, payload=payload)
    return {"memo": memo.model_dump()}
    # <<< SOLUTION


def needs_memo(state: State) -> str:
    return END if state["disposition"] == "AUTO_APPROVE" else "retrieve"


LOOKUPS = ["lookup_po", "lookup_grn", "lookup_vendor", "check_history"]
builder = StateGraph(State)
for name, fn in [("extract", extract), ("lookup_po", lookup_po), ("lookup_grn", lookup_grn),
                 ("lookup_vendor", lookup_vendor), ("check_history", check_history), ("match", match),
                 ("retrieve", retrieve), ("draft_memo", draft_memo)]:
    builder.add_node(name, fn)
builder.add_edge(START, "extract")
builder.add_conditional_edges("extract", choose_tools, LOOKUPS)     # fan out
for name in LOOKUPS:
    builder.add_edge(name, "match")                                  # fan in
builder.add_conditional_edges("match", needs_memo, ["retrieve", END])
builder.add_edge("retrieve", "draft_memo")
builder.add_edge("draft_memo", END)
graph = builder.compile()


def show(doc_id: str, title: str) -> None:
    out = graph.invoke({"doc_id": doc_id, "raw_text": load_invoice(doc_id)})
    print(f"\n== {doc_id}: {title}")
    print(f"tools called : {sorted(out['tools_called'])}")
    print(f"exceptions   : {[e['type'] + ' - ' + e['detail'] for e in out['exceptions']] or 'none'}")
    print(f"decision     : {out['disposition']} / {out['approver']}")
    if out.get("memo"):
        print(f"retrieved    : {[(c['id'], c['score']) for c in out['policy_chunks']]}")
        print(f"memo         : {out['memo']['summary']}")
        print(f"action       : {out['memo']['recommended_action']}")
        print(f"citations    : {out['memo']['citations']}")


if __name__ == "__main__":
    show("DOC-04", "quantity mismatch")
    show("DOC-06", "no purchase order (tool selection skips PO and GRN)")
    show("DOC-05", "duplicate")
    tools.FAULTS["lookup_grn"] = 5                                    # ERP outage: every retry fails
    show("DOC-01", "goods-receipt API is down")
    tools.FAULTS.clear()
