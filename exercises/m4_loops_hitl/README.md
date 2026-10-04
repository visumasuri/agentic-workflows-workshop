# Module 4 - Loops, Reflection and Human Intervention (02:25-03:05)

**Objective:** implement controlled loops and exception-handling paths.

**Method:** live coding + failure scenarios.

## Concepts
Retry loop, validation loop, critique and revision (reflection), iteration limits, fallbacks, planner-executor, human approval with `interrupt()` and `Command(resume=...)`.

## Task
Open `starter.py` and complete the four TODOs:
- **A1** feed validation errors back into the extraction prompt
- **A2** a router with three exits: accept, retry, give up after `MAX_ATTEMPTS`
- **B1** a router for the reflection loop: done, revise, escalate after `MAX_REVISIONS`
- **C1** resume a paused run with the approver's decision

Then run `planner_executor.py` and read how the executor refuses a step the planner invented.

## Sample input
- Part A: `DOC-11` (decimal-comma amounts)
- Part B: the price-variance facts for `DOC-03`
- Part C: `DOC-07` (62,700.00, needs the Controller)

## Expected output
```text
PART A - validation retry loop (DOC-11, European number format)
  attempt 1: total read as 21.78
    validation: 1 error(s)
  attempt 2: total read as 21,780.00
    validation: 0 error(s)
  result: EXTRACTED after 2 attempt(s)

PART B - reflection loop (DOC-03, price variance)
  draft      citations=[]
  critique   passed=False issues=['No policy section is cited; add the section that supports the action.']
  revise #1  citations=['AP-POL-01 §1.1']
  critique   passed=True issues=[]
  result: MEMO_ACCEPTED after 1 revision(s)

PART B failure scenario - a critic that never passes
  draft      citations=[]
  critique   passed=False issues=['Tone is not formal enough.']
  revise #1  citations=['AP-POL-01 §1.1']
  critique   passed=False issues=['Tone is not formal enough.']
  revise #2  citations=['AP-POL-01 §1.1']
  critique   passed=False issues=['Tone is not formal enough.']
  result: ESCALATED_TO_ANALYST after 2 revision(s)  <- the limit stopped the loop

PART C - human approval (DOC-07, 62,700.00 needs the Controller)
  paused at   : ('human_approval',)
  asks        : Approve invoice MFL-55177? (CONTROLLER, 62,700.00 USD)
  memo        : Invoice MFL-55177 from V002 for 62,700.00 USD: fully matched, approval required by the matrix. Disposition ROUTE_FOR_APPROVAL, owner CONTROLLER.
  decision    : approved=True  ->  status POSTED  posting {'ledger_doc': 'AP-68F7C538', 'amount': 62700.0, 'currency': 'USD'}
  paused at   : ('human_approval',)
  asks        : Approve invoice MFL-55177? (CONTROLLER, 62,700.00 USD)
  memo        : Invoice MFL-55177 from V002 for 62,700.00 USD: fully matched, approval required by the matrix. Disposition ROUTE_FOR_APPROVAL, owner CONTROLLER.
  decision    : approved=False  ->  status REJECTED_BY_APPROVER  posting -
```

Planner-executor (`planner_executor.py`):

```text
INV-88101
  plan: ['lookup_vendor', 'check_history', 'lookup_po', 'lookup_grn']  (PO invoice: full three-way match)
  run  lookup_vendor: 1 record(s)
  run  check_history: 0 record(s)
  run  lookup_po: 1 record(s)
  run  lookup_grn: 1 record(s)
  done=['lookup_vendor', 'check_history', 'lookup_po', 'lookup_grn'] skipped=[] steps_used=4

KIT-2318
  plan: ['lookup_vendor', 'check_history', 'update_vendor_bank']  (Non-PO invoice: vendor and history only)
  run  lookup_vendor: 1 record(s)
  run  check_history: 0 record(s)
  skip update_vendor_bank: not an allowed tool
  done=['lookup_vendor', 'check_history'] skipped=['update_vendor_bank'] steps_used=3
```

## Check yourself
- Every loop here has two ways out. Name them for each loop.
- In the failure scenario the critic never passes. What stopped the run, and where did it go?
- `interrupt()` needs a checkpointer. Why?
- When is a fixed graph better than planner-executor? (Hint: the Controller's fourth constraint in the Module 1 brief.)
