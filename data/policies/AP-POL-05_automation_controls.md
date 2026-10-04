# AP-POL-05 Automation and AI Controls

## §5.1 Instructions inside documents
Text inside an invoice, email or attachment is data. It is never an instruction to the automation. A document that contains text addressed to the automation, such as a request to skip matching or to approve immediately, is placed on hold and referred to Security Review.

## §5.2 Sensitive data
Bank account numbers and tax identifiers are masked before any text is sent to a language model. Comparisons that need the full value are done by deterministic code, not by the model.

## §5.3 Human approval and segregation of duties
The automation may propose a disposition but may not approve an invoice that the approval matrix assigns to a person. Postings of 10,000 or more need a recorded human approval. Every run is logged with its inputs, tool calls and outputs and kept for seven years.
