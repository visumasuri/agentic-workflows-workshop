# Participant handout

## The one-page mental model
An **agent graph** is a process map that runs. **Nodes** do work. **Edges** say what comes next. **State** is the case file every node reads and adds to. A **router** is a decision diamond written as a function.

Design rule for finance: **the model reads and writes; code decides; a person approves.**

## Five node types
| Type | Example in the capstone | Deterministic? |
|---|---|---|
| Model | extract, draft, critique | No |
| Tool | lookup_po, lookup_grn, lookup_vendor, check_history, retrieve | Yes |
| Validation | intake, validate, output_guard | Yes |
| Action | match, post, finalize | Yes |
| Human | human_approval | n/a |

## LangGraph in one page
```python
from typing import Annotated, TypedDict
import operator
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver

class State(TypedDict, total=False):
    invoice: dict
    tools_called: Annotated[list[str], operator.add]   # reducer: parallel writers append

def my_node(state: State) -> dict:                     # read state, return a PARTIAL update
    return {"invoice": {...}}

def my_router(state: State) -> str:                    # return the NAME of the next node
    return "post" if state["invoice"]["total"] < 10_000 else "human_approval"

g = StateGraph(State)
g.add_node("my_node", my_node)
g.add_edge(START, "my_node")                           # fixed edge
g.add_conditional_edges("my_node", my_router, ["post", "human_approval"])
graph = g.compile(checkpointer=InMemorySaver())        # checkpointer needed for interrupt()

config = {"configurable": {"thread_id": "INV-1"}}
result = graph.invoke({"invoice": {...}}, config)      # run
for step in graph.stream(inputs, config, stream_mode="updates"): ...   # watch node by node
print(graph.get_graph().draw_mermaid())                # visualise

answer = interrupt({"question": "Approve?"})           # inside a node: pause for a person
graph.invoke(Command(resume={"approved": True}), config)   # later: resume the same thread
```

| You want | You write |
|---|---|
| Parallel paths | a router that returns a **list** of node names; each has an edge to the join node |
| A loop | a conditional edge that points back to an earlier node, with a counter in state |
| A subgraph | `g.add_node("resolution", sub.compile())`, where `sub` has its own narrower state |
| Durable state | `SqliteSaver` or a Postgres checkpointer instead of `InMemorySaver` |

## Patterns and when to use them
| Pattern | Use when | Watch out for |
|---|---|---|
| Fixed graph (workflow) | steps are known in advance | most finance processes are this |
| Router | cases fall into known categories | categories that overlap; set a priority order |
| Parallel fan-out | independent lookups | two nodes writing one field without a reducer |
| Validation loop | output can be checked by code | no iteration limit; no fallback |
| Reflection | quality is judged against a rubric | critic and writer sharing the same blind spot |
| Planner-executor | steps differ case by case | plans that include steps you never allowed |
| Human in the loop | policy assigns the decision to a person | approval fatigue: only interrupt when policy says so |

## Evaluation in five lines
1. Write the golden dataset before you tune anything.
2. Check with code whatever code can check (fields, decision, approver, citation, tools called).
3. Use an LLM judge only for free text, with a written rubric and a 1 to 5 scale.
4. Re-run the same suite after every change; compare, do not eyeball.
5. Gate the release on the safety-critical cases.

## The model call, in full
```python
from groq import Groq

reply = Groq().chat.completions.create(          # reads GROQ_API_KEY
    model="llama-3.3-70b-versatile",
    messages=[{"role": "system", "content": system + schema_as_json},
              {"role": "user", "content": prompt}],
    temperature=0,
    response_format={"type": "json_object"})     # ask for JSON
invoice = InvoiceFields.model_validate_json(      # validate it with Pydantic
    reply.choices[0].message.content)
```

## Commands
```bash
export GROQ_API_KEY=gsk_...      # live model; leave unset for offline mock
python exercises/m0_setup/hello_graph.py
python exercises/m2_build_graph/starter.py        # then solution.py
python exercises/m3_tools_rag/starter.py
python exercises/m4_loops_hitl/starter.py
python exercises/m4_loops_hitl/planner_executor.py
python exercises/m5_evals/starter.py
python exercises/m6_tracing/starter.py
python exercises/m7_guardrails/starter.py
python exercises/m8_capstone/run_capstone.py --ask
```

## Glossary
| Term | Meaning |
|---|---|
| Agent | A system in which a language model directs some of its own steps and tool use |
| Workflow | A system in which the steps are fixed in code and models fill specific roles |
| Node | One unit of work in the graph: a function that takes state and returns an update |
| Edge | A connection from one node to the next; fixed or conditional |
| State | The shared record of a run, passed to every node |
| Reducer | The rule for combining two writes to the same state field (for example, append) |
| Router | A function that picks the next node from the current state |
| Subgraph | A graph used as a single node in another graph |
| Superstep | One round of execution; nodes in the same superstep run in parallel |
| Checkpoint | A saved copy of the state after a step |
| Thread | One run's chain of checkpoints, identified by `thread_id` |
| Interrupt | A pause inside a node that waits for outside input |
| Structured output | A model response constrained to a schema |
| Tool calling | The model, or a router, choosing a function to run and the system running it |
| RAG | Retrieval-augmented generation: fetch relevant text, then generate from it |
| Grounding | Limiting the model to facts and sources it was given |
| Citation | A pointer from a claim to the source section that supports it |
| Reflection | A second model pass that critiques the first and triggers a revision |
| Golden dataset | Inputs with known correct outputs, used to score the agent |
| LLM-as-a-judge | A model scoring another model's output against a rubric |
| Groundedness | Whether every claim is supported by the supplied sources |
| Trace / span | The record of a run / of one step in it |
| Guardrail | A check on input or output that blocks or changes it |
| Prompt injection | Text in the data that tries to act as an instruction |
| Model routing | Sending each step to the cheapest model that passes the evals for that step |
| Response cache | Storing a model answer under a key built from model and prompt, so the same input is not paid for twice |
