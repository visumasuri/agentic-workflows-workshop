"""Module 5 - build and run an evaluation suite.

1. deterministic checks against a golden dataset
2. an LLM judge for the free-text memo
3. compare a baseline with a candidate, and gate the release
Run:  python exercises/m5_evals/solution.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from finagent.evals import CHECKS, evaluate, load_golden, print_report
from finagent.graph import BASELINE, build_graph

# Cases where a wrong answer means money leaves the company or a control is bypassed.
SAFETY_CRITICAL = {"DOC-05", "DOC-08", "DOC-09", "DOC-10"}


def check_disposition(case: dict, out: dict) -> bool:
    # STEP 1: exact match between the agent's disposition and the golden one.
    # >>> SOLUTION
    return out.get("disposition") == case["disposition"]
    # <<< SOLUTION


def check_citation(case: dict, out: dict) -> bool:
    # STEP 2: pass when no citation is expected, or the expected section id is among the memo's citations.
    # >>> SOLUTION
    if case["citation"] is None:
        return True
    return case["citation"] in (out.get("memo") or {}).get("citations", [])
    # <<< SOLUTION


def check_tools(case: dict, out: dict) -> bool:
    # STEP 3: tool selection - the set of tools called equals the expected set (order does not matter).
    # >>> SOLUTION
    return sorted(set(out.get("tools_called", []))) == case["tools"]
    # <<< SOLUTION


def release_gate(result: dict) -> tuple[bool, list[str]]:
    """Pass/fail decision a pipeline can enforce before a new version is deployed."""
    # STEP 4: fail the gate when disposition accuracy is below 100%, any safety-critical case
    # fails, or mean judge groundedness is below 4.5.
    # >>> SOLUTION
    reasons = []
    s = result["summary"]
    if s["disposition"] < 1.0:
        reasons.append(f"disposition accuracy {s['disposition']:.0%} is below 100%")
    failed_critical = sorted(r["doc_id"] for r in result["rows"] if r["doc_id"] in SAFETY_CRITICAL and not r["passed"])
    if failed_critical:
        reasons.append(f"safety-critical cases failed: {failed_critical}")
    if s["judge_groundedness"] is not None and s["judge_groundedness"] < 4.5:
        reasons.append(f"judge groundedness {s['judge_groundedness']} is below 4.5")
    return (not reasons, reasons)
    # <<< SOLUTION


def compare(before: dict, after: dict) -> None:
    print(f"\n{'metric':<22}{'baseline':>10}{'candidate':>11}{'change':>9}")
    for metric in CHECKS + ["all_checks"]:
        b, c = before["summary"][metric], after["summary"][metric]
        print(f"{metric:<22}{b:>10.0%}{c:>11.0%}{(c - b) * 100:>+8.0f}pt")
    for dim in ("judge_groundedness", "judge_relevance", "judge_correctness"):
        b, c = before["summary"][dim], after["summary"][dim]
        print(f"{dim:<22}{b:>10.2f}{c:>11.2f}{c - b:>+9.2f}")


if __name__ == "__main__":
    golden = load_golden()
    case, sample = golden[2], {"disposition": "ROUTE_FOR_APPROVAL", "memo": {"citations": ["AP-POL-01 §1.1"]},
                               "tools_called": ["lookup_po", "lookup_grn", "lookup_vendor", "check_history"]}
    print(f"Unit test of the checks on {case['doc_id']}: disposition={check_disposition(case, sample)} "
          f"citation={check_citation(case, sample)} tools={check_tools(case, sample)}")

    baseline = evaluate(build_graph(BASELINE))
    print_report(baseline, "BASELINE - the graph as built in Modules 2 to 4")
    ok, why = release_gate(baseline)
    print(f"Release gate: {'PASS' if ok else 'FAIL'} {why}")

    # The failures point at two missing controls. Add them and re-run the SAME suite.
    candidate = evaluate(build_graph(BASELINE | {"dup_check", "bank_check"}))
    print_report(candidate, "CANDIDATE - duplicate check and bank-detail check added")
    ok, why = release_gate(candidate)
    print(f"Release gate: {'PASS' if ok else 'FAIL'} {why}")
    compare(baseline, candidate)
