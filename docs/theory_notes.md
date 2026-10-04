# Theory notes: agentic workflows, end to end

Background reading for the facilitator and a reference for participants. Each section gives the idea, the method used in the workshop, how it applies to finance, and where it comes from. References are listed at the end.

---

## 0. Foundations: what an agent is

**Anatomy.** An agent has five parts.
- **Model**: reads text and produces text or structured data. It is probabilistic: the same input can give different outputs.
- **Tools**: functions the system can run (look up a PO, post a journal). Tools are how the agent touches real systems.
- **State**: the record of the case so far. Models have no memory between calls; state is what carries the case forward.
- **Orchestration**: the logic that decides which step runs next.
- **Controls**: validation, limits, approvals, logs.

**Workflows and agents.** Anthropic's *Building effective agents* [1] draws the line that matters in practice. In a **workflow**, code fixes the path and models fill defined roles. In an **agent**, the model chooses its own steps and tools. Real systems sit on a spectrum between the two. The same paper's advice is to use the simplest design that works, and to add autonomy only where the task needs it.

For finance this points clearly toward the workflow end. Most finance processes are already specified (policies, tolerances, approval matrices), the cost of an error is high, and an auditor must be able to re-perform the result. The workshop therefore builds a **graph with a fixed shape** in which three nodes use a model and everything else is code.

**Why a graph.** A process map is a graph: steps, arrows, decision diamonds. Writing the agent as a graph gives a one-to-one mapping between what the process owner signed off and what runs, plus places to attach controls (a checkpoint after every node, a trace span per node, an approval at a named point).

**The ReAct loop.** The classic agent pattern, ReAct [2], alternates *reasoning* (the model writes what it will do) and *acting* (it calls a tool and reads the result) until done. It built on chain-of-thought prompting [3], which showed that asking a model to reason step by step improves accuracy. ReAct is flexible but its path is not known in advance. A graph lets you keep the useful part (model plus tools in a loop) inside boundaries you choose.

---

## 1. Agent graph design

**Elements.**
| Element | Definition | Process-map equivalent |
|---|---|---|
| Node | A function: takes state, returns an update | Activity box |
| Edge | What runs next | Arrow |
| Conditional edge / router | A function of state that names the next node | Decision diamond |
| State | Typed record shared by all nodes | The case file |
| Entry / end points | START and END | Start and end events |
| Parallel paths | Several nodes triggered by the same step | Parallel gateway |
| Subgraph | A graph used as one node | Sub-process |

**Execution model.** LangGraph runs in rounds called supersteps, a model taken from Google's Pregel system for large-scale graph processing [4]. In each superstep every node that was triggered runs, in parallel; their updates are then merged into the state; the nodes they point to run in the next superstep. Two consequences:
1. Nodes triggered together run at the same time, so they must not depend on each other.
2. If two parallel nodes write the same field, the state needs a **reducer** for that field: a rule for combining writes (for example, append to a list). Without one the run fails.

**Design method (used in Module 1).**
1. List the steps of the as-is process.
2. Label each step: model, tool, validation, action or human. Apply the test *"will an auditor re-perform this?"* If yes, it is code.
3. Write the state: which fields does each step read and write?
4. Draw the edges. For every decision, write the rule in one line.
5. Mark independent steps as parallel and self-contained groups as subgraphs.
6. List every end state. Add the failure paths: what happens when extraction fails, a system is down, a loop does not converge.

**Common design errors.** One giant model node that does everything (nothing can be tested alone). Routing decisions made by a model when a rule would do. No end state for failure. State used as a dumping ground, so nobody knows which node owns a field.

---

## 2. Building the graph

**State schema.** A `TypedDict` (or Pydantic model). Nodes return only the fields they change; the framework merges the update. Keep the state small and name the owner of each field.

**Three node kinds built in Module 2.**
- **Model node**: one model call with a narrow job. Give it only the fields it needs.
- **Validation node**: deterministic checks on what a model produced. In finance: arithmetic, completeness, format, cross-foot.
- **Action node**: applies rules or changes something.

**Structured outputs.** A model asked for free text returns something you must parse and hope. In the workshop the model is asked for JSON (JSON mode), the schema is included in the prompt, and Pydantic validates the reply; if validation fails, the error is sent back and the model tries again. Some providers go further and constrain decoding to the schema itself. Schema conformance is not correctness: `total: 21.78` is valid JSON and the wrong number. That is why a validation node follows every extraction.

**Routers.** A router is a pure function of state: no model call, no side effects, returns the name of the next node. Keeping routers deterministic means the path of a run can be explained from its state.

---

## 3. Tools, retrieval and context

**Tool calling.** The model is given tool descriptions and returns a request to call one; the system runs it and passes the result back. The idea was developed in work such as Toolformer [5] and is now a standard API feature. In a graph there are two ways to select tools:
- **Model-selected**: the model picks from a list. Flexible, less predictable.
- **Router-selected**: code picks, based on state. Used in the workshop, because which lookups an invoice needs is a known rule (a PO invoice needs four, a non-PO invoice needs two).

**Tool design rules.** One job per tool. Typed inputs and outputs. Read tools separate from write tools. Authorisation checked inside the tool. Write tools idempotent, so a retry cannot post twice. Errors returned as data the graph can route on, not raised into the void.

**Tool errors.** Three classes: transient (timeout, lock: retry with backoff), permanent (not found: route as a business exception), and permission (denied: stop and alert). A run should degrade to a person, not crash.

**Retrieval-augmented generation (RAG).** Introduced by Lewis et al. [6]: retrieve relevant passages, then generate an answer conditioned on them. It lets a model use knowledge it was never trained on (your policies) and makes answers checkable.
- **Chunking**: split documents into units that carry one idea. For policies, one numbered section per chunk, with the section id kept as metadata. That id becomes the citation.
- **Retrieval**: keyword ranking such as BM25 [7] scores a passage by rare shared terms; dense retrieval [8] compares embedding vectors and catches paraphrase. Hybrid search combines them. The workshop uses BM25 because it needs no model and no index server; the interface is the same.
- **Context assembly**: build the prompt from the facts of the case and the retrieved passages, each labelled with its id and delimited from instructions.
- **Grounding and citations**: instruct the model to use only what it was shown and to cite section ids. Then verify in code that every cited id was actually retrieved.

**Where RAG fails.** Usually in retrieval, not generation. If the right passage is not in the context, the model cannot cite it. Module 6 diagnoses exactly this: a query that mixed two exceptions pushed the right section out of the top three.

---

## 4. Loops, reflection and human intervention

**Why loops.** A single model call is right most of the time. A loop turns "most" into "nearly always" by checking and trying again, at the price of latency and cost. Every loop needs three things: a **check** that decides if another pass is needed, a **limit**, and a **fallback** for when the limit is hit.

**Validation loop.** Model produces, code checks, errors are fed back into the next prompt. Cheap and reliable when the check is deterministic.

**Reflection.** A second model pass critiques the first against a rubric, and the writer revises. Self-Refine [9] showed that iterative self-feedback improves output without extra training; Reflexion [10] extended it to agents that learn from feedback across attempts. Limits of reflection: a critic that shares the writer's blind spot adds cost without value, and a critic with a vague rubric never passes. Give the critic a specific, checkable rubric and, where possible, a different model or different instructions.

**Planner-executor.** One call writes a plan; a loop executes the steps; optionally a re-planner adjusts. Plan-and-Solve prompting [11] is the origin of the idea. Use it when the steps genuinely vary by case. Validate the plan against an allow-list before executing: a plan is model output and may contain steps you never offered.

**Human in the loop.** Three roles for a person: **approve** (policy assigns the decision), **edit** (correct a draft), **answer** (supply missing information). Mechanically, the node calls `interrupt()`, the state is checkpointed, and the run stops. When the person responds, the run resumes on the same thread from the same node. Design points:
- interrupt only where policy requires it, or approvers will stop reading
- give the approver the decision, the evidence and the policy citation on one screen
- record who decided, when, and what they saw

---

## 5. Evaluation

**Why evaluate.** A prompt change that fixes one case can break three others. Without a fixed test set you are tuning by anecdote.

**Golden dataset.** Inputs paired with known correct outputs. Build it from the process itself: one case per exception type, the boundary cases (exactly at tolerance, exactly at a threshold), the safety-critical cases (fraud, duplicates) and real failures as you find them. Twelve cases teach the method; a production suite for one process is typically a few hundred.

**What to measure.**
| Level | Question | Workshop check | Method |
|---|---|---|---|
| Component | Did extraction read the invoice correctly? | invoice number and total | exact match |
| Decision | Is the outcome right? | exception, disposition, approver | exact match |
| Tool selection | Were the right tools used? | set of tools called | set equality |
| Retrieval | Was the right policy found and cited? | expected section in citations | membership |
| Task completion | Did the run reach a valid end state? | terminal status, no crash | membership |
| Text quality | Is the memo grounded, relevant, correct? | 1 to 5 scores | LLM judge |

**Deterministic checks first.** They are exact, free and auditable. Use them for everything that has one right answer.

**LLM-as-a-judge.** For free text there is no exact match. A judge model scores the output against a rubric. G-Eval [12] showed that a rubric with explicit criteria and steps correlates better with human ratings; Zheng et al. [13] documented the biases (position, verbosity, self-preference). RAGAS [14] defines the RAG-specific metrics used here: faithfulness or groundedness (claims supported by the context) and relevance. Practical rules: one criterion per score, a short scale with each point defined, ask for the rationale, and check the judge against a sample of human ratings before trusting it [15].

**A judge does not replace decision checks.** In the Module 5 baseline the judge scores every memo 5.0 for groundedness while three decisions are wrong: a well-written, well-cited memo for the wrong decision is still wrong.

**Regression and gating.** Run the suite on every change (prompt, model version, tool, rule). Compare with the previous run. Block the release if a safety-critical case fails.

---

## 6. Tracing, debugging and optimisation

**Trace and span.** A trace is the full record of one run; a span is one step in it, with its inputs, outputs, duration, tokens, cost and error. The vocabulary comes from distributed tracing and OpenTelemetry. Agent-specific platforms (LangSmith, Langfuse, and others) add prompt and token views on the same idea.

**Debugging method.**
1. Start from a failed eval case, not from a hunch.
2. Read the trace forward, node by node, until the state first becomes wrong.
3. Classify the defect: extraction, tool, retrieval, rule, generation, or control flow.
4. Fix at that node. Add the case to the golden set if it is not there.
5. Re-run the whole suite.

**Where the money goes.** Cost = input tokens x input price + output tokens x output price, per call. Latency is dominated by output tokens and by slow tools. Measure per node before optimising.

**Optimisation levers, in the order to try them.**
1. **Remove calls**: does this step need a model at all?
2. **Shrink prompts**: pass the fields a node needs, not the whole state.
3. **Cache**: store an answer under a key built from the model and the full prompt, and reuse it when the same input returns (re-runs, retries, resubmitted documents). Only cache deterministic steps. Some providers also discount a repeated prompt prefix; check what yours offers.
4. **Route by difficulty**: send high-volume, low-judgement steps to a smaller model.
5. **Parallelise**: independent lookups in one superstep.
6. **Bound loops**: every extra pass is a full call.

Each change is an experiment. It counts only if the eval pass rate does not drop.

---

## 7. Guardrails and production readiness

**Threat model.** The agent reads documents written by outsiders. Indirect prompt injection [16] is text placed in that data to act as an instruction. It is the first item in the OWASP Top 10 for LLM applications [17]. No filter is complete, so the defence is layered:
1. scan and strip suspicious text at intake
2. pass documents as delimited data, and tell the model that content inside the delimiters is never an instruction
3. keep the decision in code, so the model cannot approve anything
4. enforce approval inside the write tool
5. evaluate with injection cases in the golden set

**Sensitive data.** Minimise what the model sees. Mask values the model does not need (bank accounts, tax ids, personal data) and do comparisons on the full value in code. Scan outputs for unmasked values.

**Access control.** The agent has its own identity and least-privilege roles. Authorisation is checked in the tool. Segregation of duties still applies: the identity that processes is not the identity that approves. These are the same ideas as in any internal control framework for financial reporting (for example COSO [18]); the agent is a new kind of user of the same controls.

**Checkpointing and persistence.** A checkpointer saves state after every step, keyed by thread id. This gives recovery after a crash, pauses that last days, and a step-by-step history for audit. Use durable storage (SQLite for a demo, Postgres in production). Because a node may re-run after a resume, side effects must be idempotent.

**Governance.** The NIST AI Risk Management Framework [19] organises the work into govern, map, measure and manage. In practice for a finance agent: a named process owner, a documented intended use, an eval suite as the measure, monitoring and a kill switch as the manage.

**Deployment considerations.** Pin model versions and treat an upgrade as a change. Version prompts, rules and graph together. Monitor error rate, retry rate, loop-limit hits, cost per item, human-review rate and queue age. Plan for the model being unavailable: the queue falls back to people.

---

## References

1. Schluntz, E. and Zhang, B. *Building effective agents.* Anthropic, December 2024.
2. Yao, S. et al. *ReAct: Synergizing Reasoning and Acting in Language Models.* ICLR 2023 (arXiv 2210.03629).
3. Wei, J. et al. *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models.* NeurIPS 2022 (arXiv 2201.11903).
4. Malewicz, G. et al. *Pregel: A System for Large-Scale Graph Processing.* SIGMOD 2010.
5. Schick, T. et al. *Toolformer: Language Models Can Teach Themselves to Use Tools.* NeurIPS 2023 (arXiv 2302.04761).
6. Lewis, P. et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* NeurIPS 2020 (arXiv 2005.11401).
7. Robertson, S. and Zaragoza, H. *The Probabilistic Relevance Framework: BM25 and Beyond.* Foundations and Trends in Information Retrieval, 2009.
8. Karpukhin, V. et al. *Dense Passage Retrieval for Open-Domain Question Answering.* EMNLP 2020 (arXiv 2004.04906).
9. Madaan, A. et al. *Self-Refine: Iterative Refinement with Self-Feedback.* NeurIPS 2023 (arXiv 2303.17651).
10. Shinn, N. et al. *Reflexion: Language Agents with Verbal Reinforcement Learning.* NeurIPS 2023 (arXiv 2303.11366).
11. Wang, L. et al. *Plan-and-Solve Prompting.* ACL 2023 (arXiv 2305.04091).
12. Liu, Y. et al. *G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment.* EMNLP 2023 (arXiv 2303.16634).
13. Zheng, L. et al. *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.* NeurIPS 2023 (arXiv 2306.05685).
14. Es, S. et al. *RAGAS: Automated Evaluation of Retrieval Augmented Generation.* EACL 2024 (arXiv 2309.15217).
15. Shankar, S. et al. *Who Validates the Validators? Aligning LLM-Assisted Evaluation of LLM Outputs with Human Preferences.* UIST 2024 (arXiv 2404.12272).
16. Greshake, K. et al. *Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.* AISec 2023 (arXiv 2302.12173).
17. OWASP. *Top 10 for Large Language Model Applications.* owasp.org.
18. COSO. *Internal Control - Integrated Framework.* 2013.
19. NIST. *Artificial Intelligence Risk Management Framework (AI RMF 1.0).* January 2023.
20. LangGraph documentation. langchain-ai.github.io/langgraph.

*Check each reference against the source before quoting it in client material.*
