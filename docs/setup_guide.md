# Setup guide

Send this to participants two working days before the session. Setup takes about ten minutes.

## Prerequisites
- A laptop with Python 3.10 or newer (`python3 --version`). Python 3.11 is what the materials were tested on.
- A code editor (VS Code is fine).
- The workshop folder, unzipped.
- A free Groq API key (optional but recommended): sign up at console.groq.com and create a key. Without one, everything still runs in offline mock mode.

## Install

macOS / Linux:
```bash
cd <workshop folder>
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):
```powershell
cd <workshop folder>
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If `pip` is blocked by a corporate proxy, ask the facilitator for the pre-built wheel folder and run `pip install --no-index --find-links wheels -r requirements.txt`.

## Verify
```bash
python exercises/m0_setup/hello_graph.py
```
You should see:
```text
python 3.11.x | langgraph 1.2.x | provider mock | main llama-3.3-70b-versatile | fast llama-3.1-8b-instant
Read INV-88101 for 6,600.00. Environment is ready.
```
followed by a Mermaid diagram of a two-node graph.

## Switch to the live model (free Groq key)
```bash
export GROQ_API_KEY=gsk_...          # Windows PowerShell: $env:GROQ_API_KEY="gsk_..."
python exercises/m0_setup/hello_graph.py
```
The first line should now say `provider groq`. To go back offline, `unset GROQ_API_KEY` or `export LLM_PROVIDER=mock`.

- Models are set by `MAIN_MODEL` (default `llama-3.3-70b-versatile`) and `FAST_MODEL` (default `llama-3.1-8b-instant`). If Groq has retired one, pick a current model from console.groq.com/docs/models.
- The free tier limits requests and tokens per minute. The full eval suite makes about 50 model calls; if it hits the limit the code waits and retries, so a run can take a few minutes.
- Do not send client or personal data. The workshop data is synthetic.

The Groq code path was tested against a local stand-in server (request, JSON parsing, validation retry, caching, token accounting). It was **not run against Groq itself** while preparing these materials, because no key was available on the authoring machine. Run Modules 0, 2 and 5 with your key once before the session.

## Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: langgraph` | virtual environment not active | activate `.venv`, re-run `pip install -r requirements.txt` |
| `ModuleNotFoundError: finagent` | script run from a copy outside the workshop folder | run scripts from inside the workshop folder; keep the folder structure |
| `NotImplementedError: Complete the TODO above` | expected in `starter.py` | complete the TODO, or open `solution.py` |
| `MockLLM has no script for X` | you added a new Pydantic schema in mock mode | register a mock handler with `@MockLLM.register("X")` (see `planner_executor.py`) or set `GROQ_API_KEY` |
| `groq.AuthenticationError` | key missing or mistyped | re-export `GROQ_API_KEY`; check for stray quotes or spaces |
| `model_decommissioned` or model not found | Groq retired a default model | set `MAIN_MODEL` / `FAST_MODEL` to current models |
| Long pauses in live mode | free-tier rate limit; the code is waiting to retry | wait, or run that step with `LLM_PROVIDER=mock` |
| Python 3.9 errors about `|` in type hints | Python too old | install Python 3.10+ |
| `sqlite3.OperationalError: database is locked` | a previous Module 7 run is still open | delete `traces/checkpoints.sqlite` and re-run |
