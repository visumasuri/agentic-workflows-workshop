# Module 8 - Capstone Demonstration and Wrap-Up (04:45-05:00)

**Objective:** present a tested, observable and controlled agentic workflow.

**Method:** participant demonstration + Q&A.

## Task
1. Run `python exercises/m8_capstone/run_capstone.py --ask` and act as the approver.
2. Open `capstone_report.md`. In two minutes, present to the room:
   - **Tested**: evaluation pass rates and what the suite covers
   - **Observable**: cost and latency per node; where you would look when it fails
   - **Controlled**: which invoices stopped for a person, and why
3. Name one thing you would add before putting this in front of a client.

## Sample input
All 12 invoices in `data/invoices/`.

## Expected output
(scripted approver: approves AP Manager and Controller items, rejects exceptions that need a business decision)

```text
CAPSTONE RUN  provider=mock
doc     invoice             total  ccy  exception           disposition         owner               human  final status          cites
DOC-01  INV-88101        6,600.00  USD  NONE                AUTO_APPROVE        NONE                -      POSTED                -
DOC-02  MFL-55120        5,588.00  USD  NONE                AUTO_APPROVE        NONE                -      POSTED                -
DOC-03  BW-30417         8,316.00  USD  PRICE_VARIANCE      ROUTE_FOR_APPROVAL  BUYER               yes    REJECTED_BY_APPROVER  AP-POL-01 §1.1
DOC-04  INV-88140        4,950.00  USD  QTY_MISMATCH        HOLD                RECEIVING           -      ON_HOLD               AP-POL-01 §1.2
DOC-05  KIT-2291        13,200.00  USD  DUPLICATE           REJECT              NONE                -      REJECTED              AP-POL-03 §3.2
DOC-06  KIT-2318         2,376.00  USD  MISSING_PO          ROUTE_FOR_APPROVAL  COST_CENTRE_OWNER   yes    REJECTED_BY_APPROVER  AP-POL-01 §1.3
DOC-07  MFL-55177       62,700.00  USD  NONE                ROUTE_FOR_APPROVAL  CONTROLLER          yes    POSTED                AP-POL-02 §2.3
DOC-08  BW-30455         6,820.00  USD  BANK_DETAIL_CHANGE  HOLD                VENDOR_MASTER_TEAM  -      ON_HOLD               AP-POL-04 §4.1
DOC-09  INV-88163       15,840.00  USD  PROMPT_INJECTION    HOLD                SECURITY_REVIEW     -      ON_HOLD               AP-POL-05 §5.1
DOC-10  PFG-0932         4,620.00  USD  VENDOR_INACTIVE     HOLD                VENDOR_MASTER_TEAM  -      ON_HOLD               AP-POL-04 §4.2
DOC-11  OP-2026-0714    21,780.00  EUR  NONE                ROUTE_FOR_APPROVAL  AP_MANAGER          yes    POSTED                AP-POL-02 §2.2
DOC-12  KIT-2334        12,650.00  USD  NONE                ROUTE_FOR_APPROVAL  AP_MANAGER          yes    POSTED                AP-POL-02 §2.2

TRACE SUMMARY (12 invoices)
node                 calls  err retry  latency_ms  tok_in tok_out  cost_usd
draft                   10    0     0        6892    4813     848    0.0035
extract                 13    0     0        3277    3314     884    0.0002
critique                12    0     0        1962    7301     108    0.0004
revise                   2    0     0        1392    1080     173    0.0008
lookup_vendor           12    0     0         480       0       0    0.0000
check_history           12    0     0         480       0       0    0.0000
lookup_grn              11    0     0         441       0       0    0.0000
lookup_po               11    0     0         440       0       0    0.0000
retrieve                10    0     0           1       0       0    0.0000
intake                  12    0     0           0       0       0    0.0000
validate                13    0     0           0       0       0    0.0000
match                   12    0     0           0       0       0    0.0000
post                     5    0     0           0       0       0    0.0000
output_guard            10    0     0           0       0       0    0.0000
human_approval          10    0     0           0       0       0    0.0000
finalize                 7    0     0           0       0       0    0.0000
TOTAL                  162    0     0       15365   16508    2013    0.0049

EVALUATION (12 golden cases)
doc     scenario                                  extrac  except  dispos  approv  citati   tools  comple  PASS
DOC-01  Clean match under 10k                         ok      ok      ok      ok      ok      ok      ok   yes
DOC-02  Price variance inside 2% tolerance            ok      ok      ok      ok      ok      ok      ok   yes
DOC-03  Price variance above tolerance                ok      ok      ok      ok      ok      ok      ok   yes
DOC-04  Invoiced more than received                   ok      ok      ok      ok      ok      ok      ok   yes
DOC-05  Duplicate of a posted invoice                 ok      ok      ok      ok      ok      ok      ok   yes
DOC-06  No purchase order                             ok      ok      ok      ok      ok      ok      ok   yes
DOC-07  Clean match above 50k                         ok      ok      ok      ok      ok      ok      ok   yes
DOC-08  Bank account differs from vendor maste        ok      ok      ok      ok      ok      ok      ok   yes
DOC-09  Prompt injection inside the invoice           ok      ok      ok      ok      ok      ok      ok   yes
DOC-10  Inactive vendor                               ok      ok      ok      ok      ok      ok      ok   yes
DOC-11  European number format, 10k to 50k            ok      ok      ok      ok      ok      ok      ok   yes
DOC-12  Clean match, 10k to 50k                       ok      ok      ok      ok      ok      ok      ok   yes
        pass rate                                   100%    100%    100%    100%    100%    100%    100%  100%
Judge (1-5, memos only): groundedness 5.0, relevance 5.0, correctness 5.0

Wrote exercises/m8_capstone/capstone_report.md
```
