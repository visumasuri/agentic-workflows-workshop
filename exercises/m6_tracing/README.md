# Module 6 - Tracing, Debugging and Optimisation (03:50-04:20)

**Objective:** diagnose execution failures and optimise performance.

**Method:** trace-analysis exercise.

## Concepts
Graph visualisation, node-level traces (spans), error analysis, latency, token usage, cost, prompt comparison, caching, model routing.

## Task
Open `starter.py` and complete the three TODOs:
- **A1** `totals`: sum latency, tokens and cost across spans
- **B1** fix the DOC-05 citation failure at its real cause
- **C1** add two experiments: route `extract` and `critique` to the fast model; then run the same invoices again with the response cache on

Traces are written to `traces/*.jsonl`, one JSON object per node run. Open one and read it.

## Sample input
One span from `traces/suite_all_main.jsonl`:
```json
{"run_id": "suite_all_main", "doc_id": "DOC-05", "node": "retrieve", "status": "ok", "error": null,
 "llm_calls": [], "retries": 0, "output": {"policy_chunks": ["AP-POL-01 §1.1", "AP-POL-03 §3.1", "AP-POL-01 §1.2"]},
 "latency_ms": 0.1, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}
```

## Expected output
```text

PART A - where do time and money go? (12 invoices, every model call on the main model)
node                 calls  err retry  latency_ms  tok_in tok_out  cost_usd
extract                 13    0     0        8086    3403     884    0.0027
draft                   10    0     0        6812    4872     828    0.0035
critique                13    0     0        5078    8008     132    0.0048
revise                   3    0     0        2078    1654     257    0.0012
check_history           12    0     0         480       0       0    0.0000
lookup_vendor           12    0     0         480       0       0    0.0000
lookup_grn              11    0     0         440       0       0    0.0000
lookup_po               11    0     0         440       0       0    0.0000
retrieve                10    0     0           0       0       0    0.0000
intake                  12    0     0           0       0       0    0.0000
validate                13    0     0           0       0       0    0.0000
match                   12    0     0           0       0       0    0.0000
post                     2    0     0           0       0       0    0.0000
output_guard            10    0     0           0       0       0    0.0000
human_approval           6    0     0           0       0       0    0.0000
finalize                10    0     0           0       0       0    0.0000
TOTAL                  160    0     0       23895   17937    2101    0.0122
Per invoice: 2.0 s, 20,038 tokens in total, $0.00102 each

PART B1 - DOC-05 fails the citation check. Follow the trace:
  match     -> 'DUPLICATE'
  retrieve  -> ['AP-POL-01 §1.1', 'AP-POL-03 §3.1', 'AP-POL-01 §1.2']
  draft     -> {'summary': 'Invoice KIT-2291 from V004 for 13,200.00 USD: duplicate. Disposition REJECT, owner NONE.', 'facts': ['LT-14P: invoiced 1200.00 vs PO 1140.00 (+5...
  Diagnosis: match found DUPLICATE and PRICE_VARIANCE. The retrieval query mixed both, so the top 3
  sections were about price and AP-POL-03 §3.2 was pushed out. The model cited what it was shown.
  After fix: retrieved ['AP-POL-03 §3.1', 'AP-POL-03 §3.2', 'AP-POL-01 §1.1'], cited ['AP-POL-03 §3.2']

PART B2 - an incident: DOC-04 took over a minute and ended ON_HOLD for the wrong reason
  intake                 0 ms
  extract              614 ms
  validate               0 ms
  check_history         40 ms
  lookup_grn         97000 ms retries=3
  lookup_po             40 ms
  lookup_vendor         40 ms
  match                  0 ms
  retrieve               0 ms
  draft                658 ms
  critique             374 ms
  output_guard           0 ms
  finalize               0 ms
  Outcome: TOOL_FAILURE -> HOLD / AP_ANALYST
  Diagnosis: lookup_grn retried 3 times against a dead endpoint (about 30 s each). The fallback worked,
  but the timeout is too long. Fix: shorter timeout, circuit breaker, alert on retries > 0.

PART C - optimisation experiments (same 12 invoices, same eval suite)
experiment                             latency s   tokens   cost $  saving  eval pass
A  all calls on main model                  23.9   19,988   0.0122      0%        92%
B  extract + critique on fast model         16.2   19,988   0.0053     56%        92%
C  B again, with response cache              1.8        0   0.0000    100%        92%
A cache pays off when the same input comes back: re-runs, retries, resubmitted documents.
Rule: an optimisation only counts if the eval pass rate does not drop.
```

*Latency and cost come from the mock provider's simulated figures (`finagent/config.py`). With `GROQ_API_KEY` set they are measured.*

## Check yourself
- Which node costs the most, and which is the slowest? Are they the same node?
- The DOC-05 memo was wrong, but the model did nothing wrong. Where was the defect?
- Experiment B saves 56%. What must be true before you ship it?
- Experiment C costs nothing. When would a response cache be wrong to use?

## Stretch
Move `draft` to the fast model as well. In mock mode the eval pass rate will not change. Why is that not evidence that it is safe, and how would you get real evidence?
