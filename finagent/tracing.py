"""Node-level tracing: one span per node run, with the model calls made inside it.

In production you would send the same spans to LangSmith, Langfuse or an
OpenTelemetry collector. A JSONL file keeps the workshop dependency-free.
"""
from __future__ import annotations

import contextvars
import functools
import json
import time
from pathlib import Path
from typing import Callable

_current_span: contextvars.ContextVar = contextvars.ContextVar("span", default=None)


class Tracer:
    def __init__(self) -> None:
        self.spans: list[dict] = []
        self.run_id = "run"

    def reset(self, run_id: str = "run") -> None:
        self.spans, self.run_id = [], run_id

    def node(self, name: str) -> Callable:
        """Decorator: wrap a node function so each call is recorded as a span."""
        def wrap(fn: Callable) -> Callable:
            @functools.wraps(fn)
            def inner(state, *args, **kwargs):
                span = {"run_id": self.run_id, "doc_id": state.get("doc_id"), "node": name,
                        "status": "ok", "error": None, "llm_calls": [], "retries": 0}
                token = _current_span.set(span)
                t0 = time.perf_counter()
                try:
                    update = fn(state, *args, **kwargs)
                    span["output"] = _preview(update)
                    return update
                except Exception as exc:
                    if type(exc).__name__ == "GraphInterrupt":   # a human-approval pause, not a failure
                        span["status"] = "interrupted"
                    else:
                        span["status"], span["error"] = "error", f"{type(exc).__name__}: {exc}"
                    raise
                finally:
                    wall = (time.perf_counter() - t0) * 1000
                    simulated = sum(c["latency_ms"] for c in span["llm_calls"]) + span.get("tool_latency_ms", 0)
                    span["latency_ms"] = round(wall + simulated, 1)
                    span["tokens_in"] = sum(c["tokens_in"] for c in span["llm_calls"])
                    span["tokens_out"] = sum(c["tokens_out"] for c in span["llm_calls"])
                    span["cost_usd"] = round(sum(c["cost_usd"] for c in span["llm_calls"]), 6)
                    self.spans.append(span)
                    _current_span.reset(token)
            return inner
        return wrap

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as fh:
            for span in self.spans:
                fh.write(json.dumps(span) + "\n")
        return path


TRACER = Tracer()


def _preview(update) -> dict:
    """Small, loggable view of what a node returned (ids for retrieved chunks, short reprs otherwise)."""
    out = {}
    for key, value in (update or {}).items() if isinstance(update, dict) else []:
        if isinstance(value, list) and value and isinstance(value[0], dict) and "id" in value[0]:
            out[key] = [v["id"] for v in value]
        else:
            text = repr(value)
            out[key] = text if len(text) <= 160 else text[:157] + "..."
    return out


def record_llm_call(call: dict) -> None:
    span = _current_span.get()
    if span is not None:
        span["llm_calls"].append(call)


def record_tool(latency_ms: float = 0.0, retried: bool = False) -> None:
    span = _current_span.get()
    if span is not None:
        span["tool_latency_ms"] = span.get("tool_latency_ms", 0) + latency_ms
        span["retries"] += int(retried)


def load_spans(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def summarise(spans: list[dict]) -> list[dict]:
    """Aggregate spans by node: calls, errors, retries, latency, tokens, cost."""
    rows: dict[str, dict] = {}
    for s in spans:
        r = rows.setdefault(s["node"], {"node": s["node"], "calls": 0, "errors": 0, "retries": 0,
                                        "latency_ms": 0.0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0})
        r["calls"] += 1
        r["errors"] += s["status"] == "error"
        r["retries"] += s.get("retries", 0)
        for k in ("latency_ms", "tokens_in", "tokens_out", "cost_usd"):
            r[k] += s.get(k, 0)
    return sorted(rows.values(), key=lambda r: -r["latency_ms"])


def print_summary(spans: list[dict], title: str = "Trace summary") -> None:
    rows = summarise(spans)
    print(f"\n{title}")
    print(f"{'node':<20}{'calls':>6}{'err':>5}{'retry':>6}{'latency_ms':>12}{'tok_in':>8}{'tok_out':>8}{'cost_usd':>10}")
    for r in rows:
        print(f"{r['node']:<20}{r['calls']:>6}{r['errors']:>5}{r['retries']:>6}{r['latency_ms']:>12.0f}"
              f"{r['tokens_in']:>8}{r['tokens_out']:>8}{r['cost_usd']:>10.4f}")
    print(f"{'TOTAL':<20}{sum(r['calls'] for r in rows):>6}{sum(r['errors'] for r in rows):>5}"
          f"{sum(r['retries'] for r in rows):>6}{sum(r['latency_ms'] for r in rows):>12.0f}"
          f"{sum(r['tokens_in'] for r in rows):>8}{sum(r['tokens_out'] for r in rows):>8}"
          f"{sum(r['cost_usd'] for r in rows):>10.4f}")
