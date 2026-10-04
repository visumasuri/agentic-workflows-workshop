"""Module 4 - loops, reflection and human intervention.

Part A  validation retry loop with an iteration limit and a fallback
Part B  reflection: draft -> critique -> revise, bounded
Part C  human approval with interrupt() and resume
Run:  python exercises/m4_loops_hitl/solution.py
"""
import pathlib
import sys
from typing import TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from finagent import rules
from finagent.graph import ALL_FEATURES, SYSTEM, build_graph, load_invoice
from finagent.llm import get_llm
from finagent.rag import PolicyRetriever
from finagent.schemas import Critique, InvoiceFields, ResolutionMemo

MAX_ATTEMPTS = 3
MAX_REVISIONS = 2


# ============================================================ Part A: validation retry loop
class ExtractState(TypedDict, total=False):
    raw_text: str
    invoice: dict
    errors: list[str]
    attempts: int
    status: str
    log: list[str]


def extract(state: ExtractState) -> dict:
    prompt = f"Extract the invoice fields.\n<invoice>\n{state['raw_text']}\n</invoice>"
    # STEP A1: when the previous attempt failed, feed the validation errors back into the prompt.
    # >>> SOLUTION
    if state.get("errors"):
        prompt += ("\nYour previous attempt failed these checks: " + "; ".join(state["errors"])
                   + ". Re-read the numbers. Some vendors use a decimal comma (1.250,00 means 1250.00).")
    # <<< SOLUTION
    invoice = get_llm().structured(InvoiceFields, prompt, system=SYSTEM).model_dump()
    attempts = state.get("attempts", 0) + 1
    return {"invoice": invoice, "attempts": attempts,
            "log": state.get("log", []) + [f"attempt {attempts}: total read as {invoice['total']:,.2f}"]}


def validate(state: ExtractState) -> dict:
    errors = rules.validate_invoice(state["invoice"])
    return {"errors": errors, "log": state["log"] + [f"  validation: {len(errors)} error(s)"]}


def after_validate(state: ExtractState) -> str:
    # STEP A2: three exits - valid, retry, or give up after MAX_ATTEMPTS. Never loop without a limit.
    # >>> SOLUTION
    if not state["errors"]:
        return "accept"
    return "manual_review" if state["attempts"] >= MAX_ATTEMPTS else "extract"
    # <<< SOLUTION


a = StateGraph(ExtractState)
a.add_node("extract", extract)
a.add_node("validate", validate)
a.add_node("accept", lambda s: {"status": "EXTRACTED"})
a.add_node("manual_review", lambda s: {"status": "MANUAL_REVIEW"})
a.add_edge(START, "extract")
a.add_edge("extract", "validate")
a.add_conditional_edges("validate", after_validate, ["extract", "accept", "manual_review"])
a.add_edge("accept", END)
a.add_edge("manual_review", END)
extract_loop = a.compile()


# ============================================================ Part B: reflection loop
class MemoState(TypedDict, total=False):
    payload: dict
    memo: dict
    critique: dict
    revisions: int
    status: str
    log: list[str]


STRICT_CRITIC = False     # failure scenario: a critic that can never be satisfied


def draft(state: MemoState) -> dict:
    p = state["payload"]
    memo = get_llm().structured(ResolutionMemo, f"Write a resolution memo.\n{p}", system=SYSTEM, payload=p).model_dump()
    return {"memo": memo, "revisions": 0, "log": [f"draft      citations={memo['citations']}"]}


def critique(state: MemoState) -> dict:
    p = {**state["payload"], "memo": state["memo"]}
    result = get_llm("fast").structured(Critique, f"Review this memo against the policy.\n{p}", system=SYSTEM, payload=p).model_dump()
    if STRICT_CRITIC:
        result = {"passed": False, "issues": ["Tone is not formal enough."]}
    return {"critique": result, "log": state["log"] + [f"critique   passed={result['passed']} issues={result['issues']}"]}


def revise(state: MemoState) -> dict:
    p = {**state["payload"], "critique": state["critique"]}
    memo = get_llm().structured(ResolutionMemo, f"Revise the memo to fix {state['critique']['issues']}.\n{p}",
                                system=SYSTEM, payload=p).model_dump()
    n = state["revisions"] + 1
    return {"memo": memo, "revisions": n, "log": state["log"] + [f"revise #{n}  citations={memo['citations']}"]}


def after_critique(state: MemoState) -> str:
    # STEP B1: stop when the critic passes; revise while under MAX_REVISIONS; otherwise escalate.
    # >>> SOLUTION
    if state["critique"]["passed"]:
        return "done"
    return "revise" if state["revisions"] < MAX_REVISIONS else "escalate"
    # <<< SOLUTION


b = StateGraph(MemoState)
b.add_node("draft", draft)
b.add_node("critique", critique)
b.add_node("revise", revise)
b.add_node("done", lambda s: {"status": "MEMO_ACCEPTED"})
b.add_node("escalate", lambda s: {"status": "ESCALATED_TO_ANALYST"})
b.add_edge(START, "draft")
b.add_edge("draft", "critique")
b.add_conditional_edges("critique", after_critique, ["revise", "done", "escalate"])
b.add_edge("revise", "critique")
b.add_edge("done", END)
b.add_edge("escalate", END)
reflection_loop = b.compile()


def memo_payload() -> dict:
    """Facts for DOC-03 (price variance), as Module 3 would have produced them."""
    invoice = {"invoice_number": "BW-30417", "vendor_id": "V003", "total": 8316.00, "currency": "USD"}
    exceptions = [{"type": "PRICE_VARIANCE", "detail": "CH-ERGO: invoiced 189.00 vs PO 165.00 (+14.5%, tolerance 2%)"}]
    return {"invoice": invoice, "exceptions": exceptions, "primary_exception": "PRICE_VARIANCE",
            "disposition": "ROUTE_FOR_APPROVAL", "approver": "BUYER", "policy": "AP-POL-01 §1.1",
            "policy_chunks": PolicyRetriever().search("PRICE VARIANCE unit price tolerance", k=3)}


# ============================================================ Part C: human approval
def human_approval_demo(doc_id: str, approved: bool) -> None:
    # A checkpointer is required: interrupt() saves the state so the run can resume later.
    graph = build_graph(ALL_FEATURES, checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": f"demo-{doc_id}-{approved}"}}
    paused = graph.invoke({"doc_id": doc_id, "raw_text": load_invoice(doc_id)}, config)
    request = paused["__interrupt__"][0].value
    print(f"  paused at   : {graph.get_state(config).next}")
    print(f"  asks        : {request['question']} ({request['approver_role']}, {request['total']:,.2f} {request['currency']})")
    print(f"  memo        : {request['memo']}")
    # STEP C1: resume the same thread with the human's decision using Command(resume=...).
    # >>> SOLUTION
    decision = {"approved": approved, "approver": "j.rivera (Controller)", "comment": "Checked against contract"}
    final = graph.invoke(Command(resume=decision), config)
    # <<< SOLUTION
    print(f"  decision    : approved={approved}  ->  status {final['status']}  posting {final.get('posting', '-')}")


if __name__ == "__main__":
    print("PART A - validation retry loop (DOC-11, European number format)")
    out = extract_loop.invoke({"raw_text": load_invoice("DOC-11")})
    print("\n".join("  " + line for line in out["log"]))
    print(f"  result: {out['status']} after {out['attempts']} attempt(s)")

    print("\nPART B - reflection loop (DOC-03, price variance)")
    out = reflection_loop.invoke({"payload": memo_payload()})
    print("\n".join("  " + line for line in out["log"]))
    print(f"  result: {out['status']} after {out['revisions']} revision(s)")

    print("\nPART B failure scenario - a critic that never passes")
    STRICT_CRITIC = True
    out = reflection_loop.invoke({"payload": memo_payload()})
    print("\n".join("  " + line for line in out["log"]))
    print(f"  result: {out['status']} after {out['revisions']} revision(s)  <- the limit stopped the loop")
    STRICT_CRITIC = False

    print("\nPART C - human approval (DOC-07, 62,700.00 needs the Controller)")
    human_approval_demo("DOC-07", approved=True)
    human_approval_demo("DOC-07", approved=False)
