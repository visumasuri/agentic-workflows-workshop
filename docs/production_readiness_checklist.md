# Production readiness checklist

Used in Module 7. For each line, rate the capstone agent red, amber or green and say what evidence you would show a reviewer.

## 1. Inputs
- [ ] Documents are scanned for text addressed to the automation before any model sees them
- [ ] Document content is passed to the model as delimited data, never concatenated into instructions
- [ ] File type, size and encoding limits are enforced at intake
- [ ] Sensitive values (bank accounts, tax ids, personal data) are masked before model calls

## 2. Decisions
- [ ] Every rule an auditor will re-perform (tolerances, thresholds, approver) is deterministic code with unit tests
- [ ] The model's role is limited to reading and writing; it cannot change the disposition
- [ ] Structured outputs are validated against a schema; invalid outputs are retried, then routed to a person

## 3. Outputs
- [ ] Citations are checked against the retrieved sources before a memo is released
- [ ] Outputs are scanned for unmasked sensitive values
- [ ] Free-text outputs that contradict the coded decision are blocked

## 4. Access and approval
- [ ] The agent runs under its own service identity with least-privilege roles per tool
- [ ] Write tools (posting, vendor changes) check authorisation inside the tool, not in the prompt
- [ ] The approval matrix is enforced by the posting tool: no approval record, no posting
- [ ] The approver is never the same identity that processed the invoice (segregation of duties)

## 5. Loops and failure
- [ ] Every loop has an iteration limit and a named fallback
- [ ] Tool calls have timeouts, bounded retries with backoff, and a degraded path
- [ ] A model refusal or outage routes the item to a person; it does not block the queue

## 6. State and recovery
- [ ] State is checkpointed to durable storage at every step
- [ ] A paused run (awaiting approval) survives a restart and can be resumed by thread id
- [ ] Tool calls with side effects are idempotent, so a replay cannot post twice

## 7. Evaluation
- [ ] A golden dataset covers every exception type and every safety-critical scenario
- [ ] The suite runs on every change to a prompt, model version, tool or rule
- [ ] A release gate blocks deployment when a safety-critical case fails
- [ ] Production samples are reviewed and added to the golden dataset on a schedule

## 8. Observability
- [ ] Every run has a trace: nodes, tool calls, model calls, tokens, cost, latency, errors
- [ ] Alerts exist for error rate, retry rate, loop-limit hits, cost per item and queue age
- [ ] Traces and decisions are retained for the period the policy requires (seven years in the brief)

## 9. Deployment
- [ ] Model versions are pinned; an upgrade is a change that goes through the eval suite
- [ ] Prompts, rules and graph definition are in version control and released together
- [ ] There is a kill switch that sends every item to the manual queue
- [ ] Data residency, retention and vendor terms have been reviewed by Risk and Legal
- [ ] Volume, cost per item and human-review rate are reported to the process owner monthly
