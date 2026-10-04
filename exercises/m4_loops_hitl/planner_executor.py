"""Module 4 extension - the planner-executor pattern.

A planner (model) writes a list of steps; an executor loop runs one step per
iteration; the loop ends when the plan is empty or the step budget is spent.
Use it when the steps genuinely differ case by case. If the steps are always
the same, a fixed graph (as in Module 3) is cheaper and easier to audit.
Run:  python exercises/m4_loops_hitl/planner_executor.py
"""
import pathlib
import sys
from typing import TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from finagent import tools
from finagent.llm import MockLLM, get_llm

MAX_STEPS = 6
ALLOWED = {"lookup_vendor", "check_history", "lookup_po", "lookup_grn"}   # the plan may only use these


class Plan(BaseModel):
    steps: list[str]
    reason: str


@MockLLM.register("Plan")
def _mock_plan(prompt: str, payload: dict) -> dict:
    if payload.get("po_number"):
        return {"steps": ["lookup_vendor", "check_history", "lookup_po", "lookup_grn"], "reason": "PO invoice: full three-way match"}
    return {"steps": ["lookup_vendor", "check_history", "update_vendor_bank"], "reason": "Non-PO invoice: vendor and history only"}


class State(TypedDict, total=False):
    invoice: dict
    plan: list[str]
    done: list[str]
    skipped: list[str]
    results: dict
    steps_used: int


def planner(state: State) -> dict:
    inv = state["invoice"]
    plan = get_llm().structured(Plan, f"Plan the checks for this invoice using only {sorted(ALLOWED)}: {inv}", payload=inv)
    print(f"  plan: {plan.steps}  ({plan.reason})")
    return {"plan": plan.steps, "done": [], "skipped": [], "results": {}, "steps_used": 0}


def executor(state: State) -> dict:
    step, rest = state["plan"][0], state["plan"][1:]
    inv = state["invoice"]
    if step not in ALLOWED:                       # never execute a step the plan invented
        print(f"  skip {step}: not an allowed tool")
        return {"plan": rest, "skipped": state["skipped"] + [step], "steps_used": state["steps_used"] + 1}
    args = {"lookup_vendor": (inv["vendor_id"],), "check_history": (inv["vendor_id"], inv["invoice_number"]),
            "lookup_po": (inv.get("po_number"),), "lookup_grn": (inv.get("po_number"),)}[step]
    result = getattr(tools, step)(*args)
    print(f"  run  {step}: {len(result) if isinstance(result, list) else 1} record(s)")
    return {"plan": rest, "done": state["done"] + [step], "results": {**state["results"], step: result},
            "steps_used": state["steps_used"] + 1}


def more_steps(state: State) -> str:
    return "executor" if state["plan"] and state["steps_used"] < MAX_STEPS else END


g = StateGraph(State)
g.add_node("planner", planner)
g.add_node("executor", executor)
g.add_edge(START, "planner")
g.add_edge("planner", "executor")
g.add_conditional_edges("executor", more_steps, ["executor", END])
graph = g.compile()

if __name__ == "__main__":
    for inv in ({"invoice_number": "INV-88101", "vendor_id": "V001", "po_number": "PO-4501"},
                {"invoice_number": "KIT-2318", "vendor_id": "V004", "po_number": None}):
        print(f"\n{inv['invoice_number']}")
        out = graph.invoke({"invoice": inv})
        print(f"  done={out['done']} skipped={out['skipped']} steps_used={out['steps_used']}")
