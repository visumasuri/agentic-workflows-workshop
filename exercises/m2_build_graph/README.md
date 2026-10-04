# Module 2 - Building the Agent Graph (00:50-01:35)

**Objective:** build and execute a functional multi-node agent graph.

**Method:** live coding (20 min) + guided build (20 min) + debrief (5 min).

## Concepts
State schema (`TypedDict`), model / validation / action nodes, edges, router functions, structured outputs (Pydantic).

## Task
Open `starter.py` and complete the five TODOs:
1. define the `State` schema
2. `extract`: a model node that returns an `InvoiceFields` structured output
3. `validate`: a validation node using `rules.validate_invoice`
4. `route_after_validate`: a router that returns the name of the next node
5. wire the graph and compile it

Run `python exercises/m2_build_graph/starter.py`. Compare with `solution.py`.

## Sample input
`DOC-01` (clean, 6,600.00), `DOC-07` (clean, 62,700.00) and `DOC-11` (Czech vendor, amounts written `21.780,00`).

## Expected output
```text
doc     invoice              total  status        disposition         approver    errors
DOC-01  INV-88101         6,600.00  DECIDED       AUTO_APPROVE        NONE        -
DOC-07  MFL-55177        62,700.00  DECIDED       ROUTE_FOR_APPROVAL  CONTROLLER  -
DOC-11  OP-2026-0714         21.78  NEEDS_REVIEW  HOLD                AP_ANALYST  line BX-600: qty 1.25 x unit price 1440 != amount 18

Streaming DOC-01 node by node:
  extract    wrote ['invoice']
  validate   wrote ['errors']
  decide     wrote ['approver', 'disposition', 'status']

---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	extract(extract)
	validate(validate)
	decide(decide)
	needs_review(needs_review)
	__end__([<p>__end__</p>]):::last
	__start__ --> extract;
	extract --> validate;
	validate -.-> decide;
	validate -.-> needs_review;
	decide --> __end__;
	needs_review --> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc
```

## Check yourself
- `DOC-11` was read as 21.78 instead of 21,780.00. Which node caught it, and was that node a model?
- A node returns only the fields it changes. What happens to the rest of the state?
- Why return a Pydantic object from the model rather than parse free text?

## Stretch
Add a field `currency_ok` to the state and a rule that only USD, EUR and GBP are accepted.
