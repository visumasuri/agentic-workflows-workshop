"""Module 1 - model answer as a runnable skeleton.

Every node is a stub: it only records that it ran. The point is the SHAPE of the
graph (nodes, edges, routers, parallel fan-out, subgraph) before any logic exists.
Run:  python exercises/m1_graph_design/solution.py
"""
import pathlib
import sys
from typing import TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from langgraph.graph import END, START, StateGraph


class State(TypedDict, total=False):
    scenario: dict                                   # flags that stand in for real data


def stub(name: str):
    def node(state: State) -> dict:
        return {}                                    # no logic yet: design first
    return node


# ---- routers: pure functions of state that return the name(s) of the next node
def after_validate(state: State):
    s = state["scenario"]
    if not s.get("fields_valid", True):
        return "manual_review"
    return ["lookup_vendor", "check_history"] + (["lookup_po", "lookup_grn"] if s.get("has_po", True) else [])


def after_match(state: State) -> str:
    return "post" if state["scenario"].get("clean") and state["scenario"].get("total", 0) < 10_000 else "resolution"


def after_resolution(state: State) -> str:
    return "human_approval" if state["scenario"].get("needs_approval") else "finalize"


# ---- subgraph: the resolution memo is its own small graph
sub = StateGraph(State)
for n in ("retrieve_policy", "draft_memo", "critique"):
    sub.add_node(n, stub(n))
sub.add_edge(START, "retrieve_policy")
sub.add_edge("retrieve_policy", "draft_memo")
sub.add_edge("draft_memo", "critique")
sub.add_edge("critique", END)

g = StateGraph(State)
for n in ("intake", "extract", "validate", "manual_review", "lookup_po", "lookup_grn", "lookup_vendor",
          "check_history", "match", "human_approval", "post", "finalize"):
    g.add_node(n, stub(n))
g.add_node("resolution", sub.compile())

g.add_edge(START, "intake")
g.add_edge("intake", "extract")
g.add_edge("extract", "validate")
lookups = ["lookup_po", "lookup_grn", "lookup_vendor", "check_history"]
g.add_conditional_edges("validate", after_validate, ["manual_review", *lookups])
for n in lookups:
    g.add_edge(n, "match")
g.add_conditional_edges("match", after_match, ["post", "resolution"])
g.add_conditional_edges("resolution", after_resolution, ["human_approval", "finalize"])
g.add_edge("human_approval", "post")
for n in ("manual_review", "post", "finalize"):
    g.add_edge(n, END)
graph = g.compile()

SCENARIOS = {
    "clean invoice under 10k": {"clean": True, "total": 6_600},
    "price variance": {"clean": False, "needs_approval": True},
    "no purchase order": {"has_po": False, "needs_approval": True},
    "quantity mismatch (hold)": {"clean": False},
    "unreadable invoice": {"fields_valid": False},
}

if __name__ == "__main__":
    for name, scenario in SCENARIOS.items():
        path = [node for _, step in graph.stream({"scenario": scenario}, stream_mode="updates", subgraphs=True)
                for node in step if node != "resolution"]
        print(f"{name:<28} {' > '.join(path)}")
    print("\n" + graph.get_graph(xray=1).draw_mermaid())
