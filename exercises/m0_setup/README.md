# Module 0 - Setup (00:00-00:15)

**Objective:** confirm the environment works and see the smallest possible agent graph.

## Task
1. Follow `docs/setup_guide.md` (create the virtual environment, install requirements).
2. Run `python exercises/m0_setup/hello_graph.py`.
3. Paste the Mermaid text it prints into https://mermaid.live to see the graph.

## Sample input
`data/invoices/DOC-01.txt` - a plain-text supplier invoice (INV-88101, 6,600.00 USD).

## Expected output
```text
python 3.11.17 | langgraph 1.2.12 | provider mock | main llama-3.3-70b-versatile | fast llama-3.1-8b-instant
Read INV-88101 for 6,600.00. Environment is ready.
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	read_invoice(read_invoice)
	greet(greet)
	__end__([<p>__end__</p>]):::last
	__start__ --> read_invoice;
	read_invoice --> greet;
	greet --> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc
```

## Check yourself
- Which of the two nodes calls the model, and which is plain Python?
- What does `provider mock` mean? Set `GROQ_API_KEY` and run it again: what changes? (See "Two ways to run" in the root README.)
