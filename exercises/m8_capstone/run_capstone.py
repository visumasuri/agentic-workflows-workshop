"""Module 8 - capstone demonstration.

Runs all 12 invoices through the finished agent with real approval pauses,
then prints the three things a reviewer wants to see: outcomes, evaluation
results and the trace summary. Writes capstone_report.md next to this file.

Run:  python exercises/m8_capstone/run_capstone.py            (approvals answered by a scripted approver)
      python exercises/m8_capstone/run_capstone.py --ask      (you approve or reject at the keyboard)
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from finagent.config import PROVIDER, TRACES
from finagent.evals import evaluate, load_golden, print_report
from finagent.graph import ALL_FEATURES, build_graph, load_invoice
from finagent.tracing import TRACER, print_summary, summarise

HERE = pathlib.Path(__file__).parent
ASK = "--ask" in sys.argv


def approver(request: dict) -> dict:
    """Scripted approver: approves matched invoices, rejects exceptions that need a business decision."""
    if ASK:
        print(f"\n  {request['question']}  [{request['approver_role']}]  {request['total']:,.2f} {request['currency']}")
        print(f"  {request['memo']}\n  cites {request['citations']}")
        return {"approved": input("  approve? (y/n) ").strip().lower() == "y", "approver": "workshop participant"}
    return {"approved": request["approver_role"] in ("AP_MANAGER", "CONTROLLER"),
            "approver": f"scripted {request['approver_role'].lower()}"}


if __name__ == "__main__":
    TRACER.reset("capstone")
    graph = build_graph(ALL_FEATURES, checkpointer=InMemorySaver(),
                        fast_nodes=("extract", "critique"))
    rows = []
    for case in load_golden():
        config = {"configurable": {"thread_id": case["doc_id"]}}
        out = graph.invoke({"doc_id": case["doc_id"], "raw_text": load_invoice(case["doc_id"])}, config)
        paused = "__interrupt__" in out
        if paused:
            out = graph.invoke(Command(resume=approver(out["__interrupt__"][0].value)), config)
        rows.append((case["doc_id"], out["invoice"]["invoice_number"], out["invoice"]["total"], out["invoice"]["currency"],
                     out["primary_exception"], out["disposition"], out["approver"], "yes" if paused else "-", out["status"],
                     ", ".join((out.get("memo") or {}).get("citations", [])) or "-"))

    head = ("doc", "invoice", "total", "ccy", "exception", "disposition", "owner", "human", "final status", "cites")
    fmt = "{:<8}{:<14}{:>11}  {:<5}{:<20}{:<20}{:<20}{:<7}{:<22}{}"
    print(f"CAPSTONE RUN  provider={PROVIDER}\n" + fmt.format(*head))
    for r in rows:
        print(fmt.format(r[0], r[1], f"{r[2]:,.2f}", *r[3:]))
    spans = list(TRACER.spans)
    TRACER.save(TRACES / "capstone.jsonl")
    print_summary(spans, "TRACE SUMMARY (12 invoices)")

    result = evaluate(build_graph(ALL_FEATURES - {"hitl"}))
    print_report(result, "EVALUATION (12 golden cases)")

    s = result["summary"]
    total_cost = sum(x["cost_usd"] for x in spans)
    lines = ["# Capstone report", "", f"Provider: `{PROVIDER}`", "", "## Outcomes", "",
             "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(str(c) if i != 2 else f"{c:,.2f}" for i, c in enumerate(r)) + " |" for r in rows]
    lines += ["", "## Evaluation", "", "| metric | pass rate |", "|---|---|"]
    lines += [f"| {k} | {v:.0%} |" for k, v in s.items() if not k.startswith("judge")]
    lines += [f"| {k} (1-5) | {v} |" for k, v in s.items() if k.startswith("judge")]
    lines += ["", "## Cost and latency", "", f"Total model cost for 12 invoices: ${total_cost:.4f} "
              f"(${total_cost / 12:.5f} per invoice).", "", "| node | calls | latency ms | tokens in | tokens out | cost $ |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['node']} | {r['calls']} | {r['latency_ms']:.0f} | {r['tokens_in']} | {r['tokens_out']} | {r['cost_usd']:.4f} |"
              for r in summarise(spans) if r["tokens_in"]]
    (HERE / "capstone_report.md").write_text("\n".join(lines) + "\n")
    print(f"\nWrote {HERE / 'capstone_report.md'}")
