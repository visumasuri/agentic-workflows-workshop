"""Module 6 - tracing, debugging and optimisation.

Part A  trace a suite run and find where time, tokens and money go
Part B  diagnose two failures from their traces
Part C  optimise: model routing and response caching, then re-run the evals
Run:  python exercises/m6_tracing/solution.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from finagent import llm, tools
from finagent.config import TRACES
from finagent.evals import evaluate, load_golden
from finagent.graph import BASELINE, build_graph, run_invoice
from finagent.tracing import TRACER, load_spans, print_summary, summarise

FEATURES = BASELINE | {"dup_check", "bank_check"}          # where Module 5 left the agent


def trace_suite(run_id: str, **graph_kwargs) -> tuple[dict, list[dict]]:
    TRACER.reset(run_id)
    result = evaluate(build_graph(**graph_kwargs), judge=False)
    path = TRACER.save(TRACES / f"{run_id}.jsonl")
    return result, load_spans(path)


def totals(spans: list[dict]) -> dict:
    # STEP A1: add up latency_ms, tokens_in, tokens_out and cost_usd across spans.
    # >>> SOLUTION
    return {k: sum(s.get(k, 0) for s in spans) for k in ("latency_ms", "tokens_in", "tokens_out", "cost_usd")}
    # <<< SOLUTION


def spans_for(spans: list[dict], doc_id: str) -> list[dict]:
    return [s for s in spans if s["doc_id"] == doc_id]


def print_timeline(spans: list[dict]) -> None:
    for s in spans:
        flag = "" if s["status"] == "ok" else f"  <-- {s['status'].upper()} {s['error'] or ''}"
        retry = f" retries={s['retries']}" if s["retries"] else ""
        print(f"  {s['node']:<15}{s['latency_ms']:>9.0f} ms{retry}{flag}")


if __name__ == "__main__":
    # ------------------------------------------------------------ Part A
    result, spans = trace_suite("suite_all_main", features=FEATURES)
    print_summary(spans, "PART A - where do time and money go? (12 invoices, every model call on the main model)")
    t = totals(spans)
    print(f"Per invoice: {t['latency_ms'] / 12 / 1000:.1f} s, {t['tokens_in'] + t['tokens_out']:,.0f} tokens in total, "
          f"${t['cost_usd'] / 12:.5f} each")

    # ------------------------------------------------------------ Part B1: a wrong answer
    print("\nPART B1 - DOC-05 fails the citation check. Follow the trace:")
    for s in spans_for(spans, "DOC-05"):
        if s["node"] in ("match", "retrieve", "draft"):
            keys = {"match": "primary_exception", "retrieve": "policy_chunks", "draft": "memo"}
            print(f"  {s['node']:<9} -> {s['output'].get(keys[s['node']])}")
    print("  Diagnosis: match found DUPLICATE and PRICE_VARIANCE. The retrieval query mixed both, so the top 3")
    print("  sections were about price and AP-POL-03 §3.2 was pushed out. The model cited what it was shown.")
    # STEP B1: fix retrieval, not the prompt - build the query from the primary exception only.
    # >>> SOLUTION
    fixed_features = FEATURES | {"focused_retrieval"}
    # <<< SOLUTION
    TRACER.reset("doc05_fixed")
    out = run_invoice(build_graph(fixed_features), "DOC-05")
    print(f"  After fix: retrieved {[c['id'] for c in out['policy_chunks']]}, cited {out['memo']['citations']}")

    # ------------------------------------------------------------ Part B2: a slow run
    print("\nPART B2 - an incident: DOC-04 took over a minute and ended ON_HOLD for the wrong reason")
    tools.FAULTS["lookup_grn"] = 5
    TRACER.reset("incident")
    out = run_invoice(build_graph(fixed_features), "DOC-04")
    tools.FAULTS.clear()
    TRACER.save(TRACES / "incident_doc04.jsonl")
    print_timeline(TRACER.spans)
    print(f"  Outcome: {out['primary_exception']} -> {out['disposition']} / {out['approver']}")
    print("  Diagnosis: lookup_grn retried 3 times against a dead endpoint (about 30 s each). The fallback worked,")
    print("  but the timeout is too long. Fix: shorter timeout, circuit breaker, alert on retries > 0.")

    # ------------------------------------------------------------ Part C: optimise
    print("\nPART C - optimisation experiments (same 12 invoices, same eval suite)")
    experiments = [
        ("A  all calls on main model", {}),
        # STEP C1: route the high-volume, low-judgement nodes to the fast model (B). Then switch on
        # the response cache and run the same invoices a second time (C).
        # >>> SOLUTION (list)
        ("B  extract + critique on fast model", {"fast_nodes": ("extract", "critique")}),
        ("C  B again, with response cache", {"fast_nodes": ("extract", "critique"), "cache": True}),
        # <<< SOLUTION
    ]
    print(f"{'experiment':<38}{'latency s':>10}{'tokens':>9}{'cost $':>9}{'saving':>8}{'eval pass':>11}")
    base_cost = None
    for name, kwargs in experiments:
        if kwargs.get("cache"):                       # first pass fills the cache; the second pass is measured
            llm.CACHE.clear()
            evaluate(build_graph(features=fixed_features, **kwargs), judge=False)
        result, spans = trace_suite("exp_" + name[0], features=fixed_features, **kwargs)
        t = totals(spans)
        base_cost = base_cost or t["cost_usd"]
        print(f"{name:<38}{t['latency_ms'] / 1000:>10.1f}{t['tokens_in'] + t['tokens_out']:>9,.0f}"
              f"{t['cost_usd']:>9.4f}{1 - t['cost_usd'] / base_cost:>8.0%}{result['summary']['all_checks']:>11.0%}")
    print("A cache pays off when the same input comes back: re-runs, retries, resubmitted documents.")
    print("Rule: an optimisation only counts if the eval pass rate does not drop.")
