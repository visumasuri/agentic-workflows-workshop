"""Module 7 - guardrails and production readiness.

Part A  input guardrail: prompt injection inside a document
Part B  sensitive data: mask before the model sees it
Part C  access control and the approval gate on the posting tool
Part D  checkpointing and persistence: survive a restart, resume after approval
Run:  python exercises/m7_guardrails/solution.py
"""
import pathlib
import re
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from finagent import guardrails, tools
from finagent.config import TRACES
from finagent.evals import evaluate, print_report
from finagent.graph import ALL_FEATURES, build_graph, load_invoice, run_invoice

INJECTION_PATTERNS = [
    # STEP A1: write patterns for text that addresses the automation rather than describing the invoice.
    # >>> SOLUTION (list)
    r"ignore (all |any )?(prior|previous|above) instructions",
    r"(system|developer) (note|message|prompt)",
    r"approve this invoice (immediately|now)",
    r"without (matching|review|approval)",
    # <<< SOLUTION
]


def scan(text: str) -> tuple[str, list[str]]:
    """Return (text with suspicious lines removed, the lines that were removed)."""
    # STEP A2: drop every line that matches a pattern and report it.
    # >>> SOLUTION
    kept, findings = [], []
    for line in text.splitlines():
        (findings if any(re.search(p, line, re.I) for p in INJECTION_PATTERNS) else kept).append(line)
    return "\n".join(kept), findings
    # <<< SOLUTION


def mask(text: str) -> str:
    # STEP B1: replace the bank account with **** plus its last four characters.
    # >>> SOLUTION
    return re.sub(r"(Bank Account:\s*)([A-Z]{2}[A-Z0-9]{10,32})", lambda m: f"{m.group(1)}****{m.group(2)[-4:]}", text)
    # <<< SOLUTION


if __name__ == "__main__":
    no_guard = ALL_FEATURES - {"guardrails", "pii_mask", "hitl"}
    guarded = ALL_FEATURES - {"hitl"}

    print("PART A - prompt injection (DOC-09)")
    _, findings = scan(load_invoice("DOC-09"))
    print(f"  scanner found: {findings}")
    for label, features in (("without guardrail", no_guard), ("with guardrail", guarded)):
        out = run_invoice(build_graph(features), "DOC-09")
        print(f"  {label:<18}: {out['primary_exception']} -> {out['disposition']} / {out['approver']}")

    print("\nPART B - what the model is allowed to see (DOC-08)")
    raw = load_invoice("DOC-08")
    print("  raw   : " + next(l for l in raw.splitlines() if l.startswith("Bank")))
    print("  masked: " + next(l for l in mask(raw).splitlines() if l.startswith("Bank")))
    out = run_invoice(build_graph(guarded), "DOC-08")
    print(f"  the bank check still works, in code: {out['exceptions'][0]['detail']}")
    print(f"  output guardrail on the memo: {guardrails.validate_memo(out['memo'], {c['id'] for c in out['policy_chunks']}, out['disposition']) or 'no problems'}")

    print("\nPART C - access control on tools")
    invoice = {"invoice_number": "MFL-55177", "total": 62700.0, "currency": "USD"}
    for label, kwargs in (("read_only role posts", {"role": "read_only"}),
                          ("ap_agent posts 62,700 without approval", {}),
                          ("ap_agent posts with recorded approval", {"approval": {"approved": True, "approver": "j.rivera"}})):
        try:
            print(f"  {label:<40}: OK {tools.post_to_ledger(invoice, **kwargs)}")
        except tools.AccessDenied as exc:
            print(f"  {label:<40}: DENIED - {exc}")

    print("\nPART D - persistence: pause for approval, restart the process, resume")
    db = TRACES / "checkpoints.sqlite"
    db.unlink(missing_ok=True)
    config = {"configurable": {"thread_id": "DOC-07-2026-10-04"}}
    # STEP D1: compile the graph with a SqliteSaver so state is written to disk at every step.
    # >>> SOLUTION
    conn = sqlite3.connect(db, check_same_thread=False)
    graph = build_graph(ALL_FEATURES, checkpointer=SqliteSaver(conn))
    # <<< SOLUTION
    paused = graph.invoke({"doc_id": "DOC-07", "raw_text": load_invoice("DOC-07")}, config)
    print(f"  run 1 paused before: {graph.get_state(config).next}, waiting for {paused['__interrupt__'][0].value['approver_role']}")
    conn.close()
    del graph                                                    # simulate the worker shutting down overnight

    conn = sqlite3.connect(db, check_same_thread=False)          # a new process, next morning
    graph = build_graph(ALL_FEATURES, checkpointer=SqliteSaver(conn))
    state = graph.get_state(config)
    print(f"  run 2 found thread {config['configurable']['thread_id']} waiting at {state.next} "
          f"with invoice {state.values['invoice']['invoice_number']} already extracted")
    final = graph.invoke(Command(resume={"approved": True, "approver": "j.rivera (Controller)"}), config)
    print(f"  resumed -> {final['status']} {final['posting']}  approved by {final['approval']['approver']}")
    steps = len(list(graph.get_state_history(config)))
    print(f"  audit trail: {steps} checkpoints stored for this thread")
    conn.close()

    print_report(evaluate(build_graph(guarded)), "\nFULL SUITE with every control switched on")
