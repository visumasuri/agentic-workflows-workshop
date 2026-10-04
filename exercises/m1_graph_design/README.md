# Module 1 - Agent Graph Design (00:15-00:50)

**Objective:** convert a business process into an agent execution graph, on paper, before writing logic.

**Method:** architecture walkthrough (15 min) + design exercise in pairs (15 min) + debrief (5 min).

## Concepts
Node, edge, shared state, entry and end points, conditional routing, parallel paths, subgraph.

## Task
1. Read `process_brief.md`. It describes how an Accounts Payable team handles invoice exceptions today.
2. Fill in `design_worksheet.md`:
   - list the nodes and label each one **model**, **tool**, **validation**, **action** or **human**
   - write the state: which fields does each node read and write?
   - draw the edges; mark each decision point as a router and write its rule in one line
   - mark which nodes can run in parallel, and what belongs in a subgraph
3. Compare with `solution.md`, then run `python exercises/m1_graph_design/solution.py` to see the model answer as a runnable skeleton (every node is a stub).

## Sample input
`process_brief.md` (one page of process narrative).

## Expected output
A node table, a state table and a graph. The runnable skeleton prints the path each scenario takes:

```text
clean invoice under 10k      intake > extract > validate > check_history > lookup_grn > lookup_po > lookup_vendor > match > post
price variance               intake > extract > validate > check_history > lookup_grn > lookup_po > lookup_vendor > match > retrieve_policy > draft_memo > critique > human_approval > post
no purchase order            intake > extract > validate > check_history > lookup_vendor > match > retrieve_policy > draft_memo > critique > human_approval > post
quantity mismatch (hold)     intake > extract > validate > check_history > lookup_grn > lookup_po > lookup_vendor > match > retrieve_policy > draft_memo > critique > finalize
unreadable invoice           intake > extract > validate > manual_review
```

## Check yourself
- Which steps did you make model nodes? Could any of them be plain code instead? (Rule: if an auditor will re-perform it, it is code.)
- Where can the run end? An agent graph usually has more than one end state.
- What would break if `lookup_po` and `lookup_grn` both wrote to the same state field?
