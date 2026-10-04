# Facilitator guide

**Workshop:** Building Agentic Workflows for Finance
**Audience:** Finance Transformation team. Assumes finance process knowledge and basic Python reading ability. No prior agent experience.
**Duration:** 5 hours including one 15-minute break.
**Format:** theory from the deck, then a hands-on exercise per module on one capstone that grows through the day.

## Before the day

| When | Do |
|---|---|
| 2 days before | Send `docs/setup_guide.md` and the workshop folder. Ask everyone to create a free Groq key. Ask participants to run Module 0 and reply with the first line of output |
| 1 day before | Run every `solution.py` on the presenting laptop. Check the projector shows a terminal at 18pt or larger |
| 1 day before | Run Modules 0, 2 and 5 with your `GROQ_API_KEY` set. The Groq path was tested against a stand-in server only, not against Groq itself. Decide whether the room runs live or on the mock |
| On the day | Open three windows: deck, editor on the workshop folder, terminal with `.venv` active. Print `m1_graph_design/process_brief.md` and `design_worksheet.md`, one per pair |

**Pairing.** Pair a stronger Python reader with a stronger process person. The design exercise (Module 1) and the eval reading (Module 5) reward process knowledge more than coding.

**The rule to repeat all day:** *the model reads and writes; code decides; a person approves.*

## Run sheet

### 00:00-00:15 Module 0: Setup (slides 1-9)
| Min | Activity |
|---|---|
| 0-3 | Welcome, outcomes, agenda |
| 3-9 | Agent anatomy: model, tools, state, orchestration, controls. Workflow versus agent |
| 9-12 | Introduce the capstone: the AP exception process and the target graph |
| 12-15 | Everyone runs `python exercises/m0_setup/hello_graph.py` |

- Say: most finance processes belong at the workflow end of the spectrum. We are building a process map that runs.
- Explain the two modes now: with a Groq key the model nodes call a hosted Llama model; without one they are scripted. Everything else is real in both. The handout outputs are from mock mode, so live wording will differ.
- Thirty people on one office network share Groq's free-tier limits per key, not per network, so each participant needs their own key. If the room stalls on rate limits, have everyone run `export LLM_PROVIDER=mock`.
- If someone's setup is broken, pair them up. Do not debug installs in the room.

### 00:15-00:50 Module 1: Agent Graph Design (slides 10-17)
| Min | Activity |
|---|---|
| 0-12 | Walkthrough: nodes, edges, state, routers, parallel paths, subgraphs, supersteps |
| 12-28 | Pairs read `process_brief.md` and fill in `design_worksheet.md` |
| 28-35 | Debrief: two pairs present; show `solution.md`; run `solution.py` |

- Ask each pair: *which steps did you make model nodes?* Most groups over-use the model. The model answer has 3 model nodes out of 15.
- Ask: *how many ways can a run end?* Most designs have one. The answer has six.
- Typical miss: no path for "system is down" or "extraction keeps failing".

### 00:50-01:35 Module 2: Building the Agent Graph (slides 18-24)
| Min | Activity |
|---|---|
| 0-8 | State schema, node kinds, structured outputs, routers |
| 8-25 | Live-code `m2_build_graph/starter.py` TODO 1 to 3 with the room following |
| 25-40 | Participants finish TODO 4 and 5 and run it |
| 40-45 | Debrief on DOC-11 |

- The teaching moment is DOC-11: the total is read as 21.78. Ask *which node caught it?* A validation node, not a model. Schema-valid is not correct.
- Show `graph.stream(..., stream_mode="updates")`: each node writes only its own fields.
- Common errors: returning the whole state from a node; a router that returns a node name that was never added.

### 01:35-02:10 Module 3: Tools, RAG and Context (slides 25-31)
| Min | Activity |
|---|---|
| 0-10 | Tool nodes, tool selection, fan-out and fan-in, reducers, RAG, citations, tool errors |
| 10-30 | Participants complete the four TODOs in `m3_tools_rag/starter.py` |
| 30-35 | Debrief: the outage run |

- Show `data/policies/AP-POL-01_three_way_match.md` and how one section becomes one chunk with a citation id.
- On the outage run ask: *is HOLD / AP_ANALYST the right outcome?* It is the Controller's fourth constraint from the brief.
- If short of time, give TODO 1 and 2 as done and have them write only the retrieval query and the prompt.

### 02:10-02:25 Break (slide 32)
Leave the DOC-11 output on screen. It is the hook for Module 4.

### 02:25-03:05 Module 4: Loops, Reflection and Human Intervention (slides 33-40)
| Min | Activity |
|---|---|
| 0-10 | Loop anatomy (check, limit, fallback), reflection, planner-executor, interrupt and resume |
| 10-28 | Live-code Part A; participants do B1 and C1 |
| 28-35 | Failure scenario: the critic that never passes |
| 35-40 | Run `planner_executor.py`; discuss when a fixed graph is better |

- In Part C, point at `graph.get_state(config).next`: the run is parked on a named node, with its state saved.
- In `planner_executor.py` the plan contains `update_vendor_bank`. The executor refuses it. A plan is model output.
- Note: a node that calls `interrupt()` runs again from its first line on resume. Keep side effects after the interrupt, or in a later node.

### 03:05-03:50 Module 5: Agent Evaluations (slides 41-47)
| Min | Activity |
|---|---|
| 0-10 | Golden datasets, deterministic checks, LLM judge, metrics, release gate |
| 10-25 | Participants complete the four TODOs and run the baseline |
| 25-38 | In pairs: for each failing case, name the missing control. Then run the candidate |
| 38-45 | Debrief: read the comparison table |

- Let the room find it: the baseline **auto-approved and posted DOC-08**, an invoice with changed bank details.
- Point out judge groundedness 5.0 next to 75% decision accuracy. A judge alone would have passed this agent.
- Two cases still fail after the fix. Do not explain them yet. Module 6 fixes one, Module 7 the other.

### 03:50-04:20 Module 6: Tracing, Debugging and Optimisation (slides 48-54)
| Min | Activity |
|---|---|
| 0-7 | Spans, the debugging method, cost and latency levers |
| 7-22 | Participants run the starter; Part B1 as a group: read the DOC-05 trace forward |
| 22-30 | Part C: the three experiments |

- B1: the model cited what it was shown. The defect was the retrieval query. Fix the node where the state first went wrong.
- B2: 97 seconds in one node. Ask what alert would have caught it.
- Be straight about mock mode: latency and cost are simulated from token counts, and the eval pass rate cannot drop when you move a scripted node to another model. With a live model it can, which is the reason to re-run the suite.

### 04:20-04:45 Module 7: Guardrails and Production Readiness (slides 55-61)
| Min | Activity |
|---|---|
| 0-8 | Threat model, layered defence, sensitive data, access control, checkpointing |
| 8-18 | Participants complete the TODOs; watch DOC-09 go from ROUTE to HOLD and the suite reach 12 of 12 |
| 18-25 | Walk `production_readiness_checklist.md`; rate the capstone red, amber or green |

- Say plainly that the regex scanner is weak on its own. Ask what else stops DOC-09 being paid: the decision is in code, the price variance still routes it to a buyer, and posting needs an approval record.
- Part D: delete the graph object, reopen the database, resume. The state was on disk.

### 04:45-05:00 Module 8: Capstone and Wrap-Up (slides 62-69)
| Min | Activity |
|---|---|
| 0-5 | Everyone runs `run_capstone.py --ask` and approves or rejects |
| 5-11 | Two or three pairs present: tested, observable, controlled |
| 11-15 | Lessons, next steps, questions |

## If you are running late
| Cut | Saves | Cost |
|---|---|---|
| Module 3: give TODO 1 and 2 as done | 8 min | less tool practice |
| Module 4: skip `planner_executor.py` | 5 min | pattern covered on slides only |
| Module 6: demonstrate Part C instead of having them code it | 6 min | none of the diagnosis is lost |
| Module 7: checklist as take-home | 7 min | less discussion |

Never cut the Module 5 baseline reading or the capstone presentations.

## Questions you will get
| Question | Short answer |
|---|---|
| Why not let the model decide? | Because an auditor must re-perform the decision and get the same answer. A model call cannot promise that |
| Is this just RPA with a model? | The graph is the workflow. The model adds reading unstructured documents and writing explanations, which RPA could not do |
| Why LangGraph? | Its concepts (nodes, edges, state, checkpoints, interrupts) map directly to a process map and to controls. The design method transfers to other frameworks |
| How big should the golden dataset be? | Enough to cover every exception type, boundary and safety-critical scenario. Start with dozens; grow it from production failures |
| Can we use client data? | Not in this workshop. In engagements, only inside environments and under terms the firm and the client have approved |
| What changes with a live model? | Wording varies, and so can extraction and citations. That variance is what the eval suite measures |
| What does it cost? | Free on Groq's free tier. At approximate list prices the mock run is about a tenth of a cent per invoice, less after routing. Measure on your own volume and rates |
| Why Groq and Llama? | A free key, an open model and one function call keep the focus on the graph. The model sits behind one small wrapper, so a firm-approved model can replace it without touching the graph |

## After the session
- Share the folder, including `solution.py` files.
- Ask each participant for one process from their engagement and a first node table for it, using the Module 1 worksheet.
