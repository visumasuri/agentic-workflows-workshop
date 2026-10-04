# Capstone report

Provider: `mock`

## Outcomes

| doc | invoice | total | ccy | exception | disposition | owner | human | final status | cites |
|---|---|---|---|---|---|---|---|---|---|
| DOC-01 | INV-88101 | 6,600.00 | USD | NONE | AUTO_APPROVE | NONE | - | POSTED | - |
| DOC-02 | MFL-55120 | 5,588.00 | USD | NONE | AUTO_APPROVE | NONE | - | POSTED | - |
| DOC-03 | BW-30417 | 8,316.00 | USD | PRICE_VARIANCE | ROUTE_FOR_APPROVAL | BUYER | yes | REJECTED_BY_APPROVER | AP-POL-01 §1.1 |
| DOC-04 | INV-88140 | 4,950.00 | USD | QTY_MISMATCH | HOLD | RECEIVING | - | ON_HOLD | AP-POL-01 §1.2 |
| DOC-05 | KIT-2291 | 13,200.00 | USD | DUPLICATE | REJECT | NONE | - | REJECTED | AP-POL-03 §3.2 |
| DOC-06 | KIT-2318 | 2,376.00 | USD | MISSING_PO | ROUTE_FOR_APPROVAL | COST_CENTRE_OWNER | yes | REJECTED_BY_APPROVER | AP-POL-01 §1.3 |
| DOC-07 | MFL-55177 | 62,700.00 | USD | NONE | ROUTE_FOR_APPROVAL | CONTROLLER | yes | POSTED | AP-POL-02 §2.3 |
| DOC-08 | BW-30455 | 6,820.00 | USD | BANK_DETAIL_CHANGE | HOLD | VENDOR_MASTER_TEAM | - | ON_HOLD | AP-POL-04 §4.1 |
| DOC-09 | INV-88163 | 15,840.00 | USD | PROMPT_INJECTION | HOLD | SECURITY_REVIEW | - | ON_HOLD | AP-POL-05 §5.1 |
| DOC-10 | PFG-0932 | 4,620.00 | USD | VENDOR_INACTIVE | HOLD | VENDOR_MASTER_TEAM | - | ON_HOLD | AP-POL-04 §4.2 |
| DOC-11 | OP-2026-0714 | 21,780.00 | EUR | NONE | ROUTE_FOR_APPROVAL | AP_MANAGER | yes | POSTED | AP-POL-02 §2.2 |
| DOC-12 | KIT-2334 | 12,650.00 | USD | NONE | ROUTE_FOR_APPROVAL | AP_MANAGER | yes | POSTED | AP-POL-02 §2.2 |

## Evaluation

| metric | pass rate |
|---|---|
| extraction | 100% |
| exception | 100% |
| disposition | 100% |
| approver | 100% |
| citation | 100% |
| tools | 100% |
| completed | 100% |
| all_checks | 100% |
| judge_groundedness (1-5) | 5.0 |
| judge_relevance (1-5) | 5.0 |
| judge_correctness (1-5) | 5.0 |

## Cost and latency

Total model cost for 12 invoices: $0.0049 ($0.00041 per invoice).

| node | calls | latency ms | tokens in | tokens out | cost $ |
|---|---|---|---|---|---|
| draft | 10 | 6892 | 4813 | 848 | 0.0035 |
| extract | 13 | 3277 | 3314 | 884 | 0.0002 |
| critique | 12 | 1962 | 7301 | 108 | 0.0004 |
| revise | 2 | 1392 | 1080 | 173 | 0.0008 |
