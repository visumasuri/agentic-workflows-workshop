# Module 3 - Tools, RAG and Context Integration (01:35-02:10)

**Objective:** connect the agent to business tools and knowledge sources.

**Method:** hands-on implementation.

## Concepts
Tool nodes, tool selection, parallel fan-out and fan-in, reducers, retrieval, context assembly, grounding, citations, tool-error handling.

## Task
Open `starter.py` and complete the four TODOs:
1. `lookup_grn`: call the tool through `call_with_retry`; on `ToolError` return the error in state instead of raising
2. `choose_tools`: return the list of tool nodes to run (skip PO and GRN when no PO is quoted)
3. `retrieve`: build the search query and retrieve three policy sections
4. `draft_memo`: assemble facts and policy into the prompt and ask for a `ResolutionMemo`

## Sample input
- `DOC-04`: invoice for 100 gasket kits; `goods_receipts.csv` shows 80 received
- `DOC-06`: services invoice with `PO Reference: NONE`
- `DOC-05`: second copy of `KIT-2291`, which is already in `posted_invoices.csv`
- `DOC-01` with the goods-receipt API switched off (`tools.FAULTS["lookup_grn"] = 5`)

## Expected output
```text

== DOC-04: quantity mismatch
tools called : ['check_history', 'lookup_grn', 'lookup_po', 'lookup_vendor']
exceptions   : ['QTY_MISMATCH - GK-110: invoiced 100 vs received 80']
decision     : HOLD / RECEIVING
retrieved    : [('AP-POL-01 §1.2', 3.683), ('AP-POL-01 §1.3', 1.665), ('AP-POL-01 §1.1', 1.332)]
memo         : Invoice INV-88140 from V001 for 4,950.00 USD: qty mismatch. Disposition HOLD, owner RECEIVING.
action       : Hold and refer to Receiving until the outstanding quantity is receipted or credited.
citations    : ['AP-POL-01 §1.2']

== DOC-06: no purchase order (tool selection skips PO and GRN)
tools called : ['check_history', 'lookup_vendor']
exceptions   : ['MISSING_PO - Invoice quotes no valid purchase order']
decision     : ROUTE_FOR_APPROVAL / COST_CENTRE_OWNER
retrieved    : [('AP-POL-01 §1.3', 9.003), ('AP-POL-01 §1.1', 7.173), ('AP-POL-01 §1.2', 2.768)]
memo         : Invoice KIT-2318 from V004 for 2,376.00 USD: missing po. Disposition ROUTE_FOR_APPROVAL, owner COST_CENTRE_OWNER.
action       : Route to the cost centre owner for non-PO approval.
citations    : ['AP-POL-01 §1.3']

== DOC-05: duplicate
tools called : ['check_history', 'lookup_grn', 'lookup_po', 'lookup_vendor']
exceptions   : ['PRICE_VARIANCE - LT-14P: invoiced 1200.00 vs PO 1140.00 (+5.3%, tolerance 2%)', 'DUPLICATE - KIT-2291 was posted on 2026-08-14']
decision     : REJECT / NONE
retrieved    : [('AP-POL-03 §3.1', 5.844), ('AP-POL-03 §3.2', 1.837), ('AP-POL-01 §1.1', 0.0)]
memo         : Invoice KIT-2291 from V004 for 13,200.00 USD: duplicate. Disposition REJECT, owner NONE.
action       : Reject and return to the vendor with the posting date of the original.
citations    : ['AP-POL-03 §3.2']

== DOC-01: goods-receipt API is down
tools called : ['check_history', 'lookup_grn', 'lookup_po', 'lookup_vendor']
exceptions   : ['TOOL_FAILURE - lookup_grn: upstream ERP timeout after 30s']
decision     : HOLD / AP_ANALYST
retrieved    : [('AP-POL-05 §5.3', 2.032), ('AP-POL-01 §1.1', 0.0), ('AP-POL-01 §1.2', 0.0)]
memo         : Invoice INV-88101 from V001 for 6,600.00 USD: tool failure. Disposition HOLD, owner AP_ANALYST.
action       : Hold for an AP analyst; a source system could not be reached.
citations    : ['AP-POL-05 §5.3']
```

## Check yourself
- In the DOC-06 run only two tools were called. Where was that decided?
- The memo cites `AP-POL-01 §1.2`. How do you know the model did not invent that reference?
- In the outage run, why is `HOLD / AP_ANALYST` a better outcome than an exception trace?

## Stretch
Change `k=3` to `k=1` in `retrieve` and re-run DOC-05. Which section is retrieved, and is it the one that supports the action?
