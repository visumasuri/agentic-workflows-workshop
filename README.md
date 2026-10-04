# Building Agentic Workflows for Finance

A five-hour, hands-on workshop for the Finance Transformation team. Participants build one agent from an empty file to a tested, traced and controlled workflow: an **Accounts Payable invoice exception agent** written as a LangGraph graph.

## What is in this folder

| Path | What it is |
|---|---|
| `deck/Agentic_Workflows_for_Finance.pptx` | The training deck (theory, diagrams, exercise slides with sample input and output, speaker notes) |
| `docs/facilitator_guide.md` | Minute-by-minute run sheet, talking points, demo commands, fallback plans |
| `docs/setup_guide.md` | Installation, verification, switching to a live model, troubleshooting |
| `docs/theory_notes.md` | The theory and literature behind each module, with references |
| `docs/participant_handout.md` | Cheat sheet: LangGraph API, patterns, glossary |
| `docs/production_readiness_checklist.md` | Controls checklist used in Module 7 |
| `exercises/m0 ... m8` | One folder per module: `README.md` (task, sample input, expected output), `starter.py`, `solution.py`, `expected_output.txt` |
| `finagent/` | Shared package: model wrapper, tools, retrieval, rules, guardrails, tracing, the capstone graph, the eval harness |
| `data/` | 12 sample invoices, PO / goods receipt / vendor / history tables, five AP policies, the golden dataset |
| `traces/` | Trace files written by Modules 6 and 8 |
| `tools/make_starters.py` | Regenerates every `starter.py` from its `solution.py` |

## Quick start

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python exercises/m0_setup/hello_graph.py
python exercises/m8_capstone/run_capstone.py
```

## Agenda

| Time | Module | Exercise | Outcome |
|---|---|---|---|
| 00:00-00:15 | 0 Setup | `m0_setup` | Environment and target architecture |
| 00:15-00:50 | 1 Agent Graph Design | `m1_graph_design` | A business process turned into a graph |
| 00:50-01:35 | 2 Building the Agent Graph | `m2_build_graph` | A working multi-node graph |
| 01:35-02:10 | 3 Tools, RAG and Context | `m3_tools_rag` | Agent connected to tools and policy |
| 02:10-02:25 | Break | | |
| 02:25-03:05 | 4 Loops, Reflection, Human Intervention | `m4_loops_hitl` | Controlled loops and approval |
| 03:05-03:50 | 5 Agent Evaluations | `m5_evals` | An evaluation suite |
| 03:50-04:20 | 6 Tracing, Debugging, Optimisation | `m6_tracing` | Failures diagnosed, cost reduced |
| 04:20-04:45 | 7 Guardrails and Production Readiness | `m7_guardrails` | Enterprise controls |
| 04:45-05:00 | 8 Capstone and Wrap-Up | `m8_capstone` | A tested, observable, controlled workflow |

## Two ways to run

**Live, with a free Groq key.** Get a key at console.groq.com, then `export GROQ_API_KEY=gsk_...`. The model nodes call open Llama models hosted by Groq through the small `groq` package: one `chat.completions.create` call that asks for JSON, validated with Pydantic (see `finagent/llm.py`, about 40 lines). Outputs vary in wording, and the scripted mistakes described in the exercises (the decimal-comma misread, the uncited first draft) may not occur. The free tier is rate limited; the code waits and retries. Never send client data.

**Offline mock (no key).** Without `GROQ_API_KEY`, or with `LLM_PROVIDER=mock`, the model is replaced by a scripted stand-in. Nothing leaves the laptop and every output is reproducible, which is why the expected outputs in the exercise READMEs match exactly. The graph, tools, retrieval, rules, guardrails, checkpoints and evaluation code are real in both modes. Only the three model nodes (extract, draft, critique) and the judge are scripted. Latency and cost figures in mock mode are simulated from token counts.

Models are set by `MAIN_MODEL` (default `llama-3.3-70b-versatile`) and `FAST_MODEL` (default `llama-3.1-8b-instant`). Groq retires models from time to time: check console.groq.com/docs/models and change the two names if a default is gone.

## The story across the day

The evaluation suite is the thread. The same 12 golden cases are run after each stage:

| Stage | What was added | Correct decisions | All checks pass |
|---|---|---|---|
| Modules 2-4 build | extraction, tools, retrieval, loops | 9 of 12 | 0 of 12 (duplicate-check tool never called) |
| Module 5 | duplicate check, bank-detail check | 11 of 12 | 10 of 12 |
| Module 6 | focused retrieval query | 11 of 12 | 11 of 12 |
| Module 7 | injection guardrail, masking | 12 of 12 | 12 of 12 |

All data is synthetic. Vendor names, bank accounts and policies are invented for training.
