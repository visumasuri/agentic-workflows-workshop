"""Evaluation harness: run the agent over the golden dataset and score it.

Deterministic checks first (cheap, exact, auditable); an LLM judge only for the
free-text memo, where exact match cannot work.
"""
from __future__ import annotations

import json

from .config import DATA
from .graph import run_invoice
from .llm import get_llm
from .schemas import JudgeScore

TERMINAL = {"POSTED", "PENDING_APPROVAL", "ON_HOLD", "REJECTED", "MANUAL_REVIEW"}
CHECKS = ["extraction", "exception", "disposition", "approver", "citation", "tools", "completed"]


def load_golden() -> list[dict]:
    return [json.loads(l) for l in (DATA / "golden_dataset.jsonl").read_text().splitlines() if l.strip()]


def score_case(case: dict, out: dict) -> dict:
    inv, memo = out.get("invoice", {}), out.get("memo") or {}
    return {
        "extraction": inv.get("invoice_number") == case["invoice_number"] and abs(inv.get("total", 0) - case["total"]) < 0.01,
        "exception": out.get("primary_exception") == case["exception"],
        "disposition": out.get("disposition") == case["disposition"],
        "approver": out.get("approver") == case["approver"],
        "citation": case["citation"] is None or case["citation"] in memo.get("citations", []),
        "tools": sorted(set(out.get("tools_called", []))) == case["tools"],
        "completed": out.get("status") in TERMINAL,
    }


def judge_memo(case: dict, out: dict) -> dict | None:
    """LLM-as-a-judge on the memo: groundedness, relevance, correctness (1-5)."""
    if not out.get("memo"):
        return None
    payload = {"memo": out["memo"], "policy_chunks": out.get("policy_chunks", []),
               "primary_exception": out.get("primary_exception", ""), "expected_citation": case["citation"]}
    policy = "\n".join(f"[{c['id']}] {c['text']}" for c in payload["policy_chunks"])
    prompt = ("Score the memo from 1 (poor) to 5 (excellent).\n"
              "groundedness: every claim is supported by the policy text or invoice facts shown.\n"
              "relevance: it addresses this invoice's actual exception.\n"
              "correctness: the action and cited section are the right ones.\n"
              f"Memo: {out['memo']}\n<policy>\n{policy}\n</policy>\nReference citation: {case['citation']}")
    return get_llm("main").structured(JudgeScore, prompt, payload=payload).model_dump()


def evaluate(graph, cases: list[dict] | None = None, judge: bool = True) -> dict:
    cases = cases or load_golden()
    rows = []
    for case in cases:
        try:
            out = run_invoice(graph, case["doc_id"])
        except Exception as exc:                      # an unhandled crash is a failed case, not a failed suite
            out = {"status": f"CRASH: {type(exc).__name__}: {exc}"}
        checks = score_case(case, out)
        rows.append({"doc_id": case["doc_id"], "scenario": case["scenario"], "checks": checks,
                     "passed": all(checks.values()), "got": {k: out.get(k) for k in ("primary_exception", "disposition", "approver", "status")},
                     "judge": judge_memo(case, out) if judge else None})
    n = len(rows)
    summary = {c: sum(r["checks"][c] for r in rows) / n for c in CHECKS}
    summary["all_checks"] = sum(r["passed"] for r in rows) / n
    judged = [r["judge"] for r in rows if r["judge"]]
    for dim in ("groundedness", "relevance", "correctness"):
        summary[f"judge_{dim}"] = round(sum(j[dim] for j in judged) / len(judged), 2) if judged else None
    return {"rows": rows, "summary": summary}


def print_report(result: dict, title: str = "Evaluation report") -> None:
    print(f"\n{title}")
    print(f"{'doc':<8}{'scenario':<40}" + "".join(f"{c[:6]:>8}" for c in CHECKS) + f"{'PASS':>6}")
    for r in result["rows"]:
        print(f"{r['doc_id']:<8}{r['scenario'][:38]:<40}" + "".join(f"{'ok' if r['checks'][c] else 'FAIL':>8}" for c in CHECKS)
              + f"{'yes' if r['passed'] else 'NO':>6}")
    s = result["summary"]
    print(f"{'':<8}{'pass rate':<40}" + "".join(f"{s[c]:>8.0%}" for c in CHECKS) + f"{s['all_checks']:>6.0%}")
    if s["judge_groundedness"] is not None:
        print(f"Judge (1-5, memos only): groundedness {s['judge_groundedness']}, relevance {s['judge_relevance']}, "
              f"correctness {s['judge_correctness']}")
    for r in result["rows"]:
        if not r["passed"]:
            failed = [c for c, ok in r["checks"].items() if not ok]
            print(f"  {r['doc_id']} failed {failed}: got {r['got']}")
