"""One small interface over the language model, with two implementations.

    llm = get_llm()                      # Groq if GROQ_API_KEY is set, otherwise the mock
    invoice = llm.structured(InvoiceFields, prompt, system=..., payload=...)

GroqLLM  - calls a hosted open model (Llama) through Groq's API. Free key from
           console.groq.com. It asks for JSON and validates it with Pydantic.
MockLLM  - scripted, deterministic, offline. Needs no key and makes every sample
           output reproducible. Use it when the network or the rate limit lets you down.

`payload` carries the same facts that are rendered into the prompt, as a dict.
GroqLLM ignores it; MockLLM reads it instead of trying to parse prose.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Callable, Type, TypeVar

from pydantic import BaseModel, ValidationError

from .config import FAST_MODEL, MAIN_MODEL, MOCK_LATENCY, PRICES, PROVIDER
from .tracing import record_llm_call

T = TypeVar("T", bound=BaseModel)

# Response cache shared by every LLM object: same model + same prompt -> same answer, no call.
CACHE: dict[str, str] = {}


def _cost(model: str, tokens_in: int, tokens_out: int) -> float:
    p = PRICES.get(model, PRICES[MAIN_MODEL])
    return (tokens_in * p["input"] + tokens_out * p["output"]) / 1_000_000


def _key(model: str, schema: type, system: str, prompt: str) -> str:
    return hashlib.sha256(f"{model}|{schema.__name__}|{system}|{prompt}".encode()).hexdigest()


def _cache_hit(model: str, schema: Type[T], key: str) -> T:
    record_llm_call({"model": model, "schema": schema.__name__, "tokens_in": 0, "tokens_out": 0,
                     "latency_ms": 0.0, "cost_usd": 0.0, "cached": True})
    return schema.model_validate_json(CACHE[key])


# ------------------------------------------------------------------ live provider
class GroqLLM:
    """Structured output in three steps: ask for JSON, parse it, validate it with Pydantic."""

    def __init__(self, model: str, cache: bool = False) -> None:
        from groq import Groq  # imported here so mock mode needs no package

        self.client = Groq()   # reads GROQ_API_KEY from the environment
        self.model, self.cache = model, cache

    def structured(self, schema: Type[T], prompt: str, system: str = "", payload: dict | None = None) -> T:
        from groq import RateLimitError

        key = _key(self.model, schema, system, prompt)
        if self.cache and key in CACHE:
            return _cache_hit(self.model, schema, key)
        messages = [
            {"role": "system", "content": f"{system}\nReply with one JSON object that matches this JSON schema:\n"
                                          f"{json.dumps(schema.model_json_schema())}"},
            {"role": "user", "content": prompt},
        ]
        for attempt in range(3):
            try:
                reply = self.client.chat.completions.create(
                    model=self.model, messages=messages, temperature=0,
                    response_format={"type": "json_object"})
            except RateLimitError:                      # free tier: wait and try again
                time.sleep(10 * (attempt + 1))
                continue
            text = reply.choices[0].message.content
            record_llm_call({"model": self.model, "schema": schema.__name__,
                             "tokens_in": reply.usage.prompt_tokens, "tokens_out": reply.usage.completion_tokens,
                             "latency_ms": 0.0,         # real wall time is captured by the node span
                             "cost_usd": _cost(self.model, reply.usage.prompt_tokens, reply.usage.completion_tokens)})
            try:
                result = schema.model_validate_json(text)
            except ValidationError as exc:              # valid JSON, wrong shape: show the model its mistake
                messages += [{"role": "assistant", "content": text},
                             {"role": "user", "content": f"That did not match the schema: {exc}. Send corrected JSON."}]
                continue
            CACHE[key] = result.model_dump_json()
            return result
        raise RuntimeError(f"{self.model} did not return valid {schema.__name__} after 3 attempts")


# ------------------------------------------------------------------ mock provider
class MockLLM:
    """Scripted stand-in for a model. Behaviour per schema is defined by a handler."""

    handlers: dict[str, Callable[[str, dict], dict]] = {}

    def __init__(self, model: str, cache: bool = False) -> None:
        self.model, self.cache = model, cache

    @classmethod
    def register(cls, schema_name: str):
        def deco(fn):
            cls.handlers[schema_name] = fn
            return fn
        return deco

    def structured(self, schema: Type[T], prompt: str, system: str = "", payload: dict | None = None) -> T:
        handler = self.handlers.get(schema.__name__)
        if handler is None:
            raise NotImplementedError(f"MockLLM has no script for {schema.__name__}; set GROQ_API_KEY to use a real model")
        key = _key(self.model, schema, system, prompt)
        if self.cache and key in CACHE:
            return _cache_hit(self.model, schema, key)
        result = schema.model_validate(handler(prompt, payload or {}))
        tokens_in = (len(system) + len(prompt)) // 4
        tokens_out = max(len(result.model_dump_json()) // 4, 1)
        fixed, per_tok = MOCK_LATENCY.get(self.model, MOCK_LATENCY[MAIN_MODEL])
        record_llm_call({"model": self.model, "schema": schema.__name__, "tokens_in": tokens_in,
                         "tokens_out": tokens_out, "latency_ms": round(fixed + per_tok * tokens_out, 1),
                         "cost_usd": _cost(self.model, tokens_in, tokens_out)})
        CACHE[key] = result.model_dump_json()
        return result


def get_llm(tier: str = "main", cache: bool = False):
    """tier='main' for reasoning-heavy steps, 'fast' for cheap, high-volume steps."""
    model = MAIN_MODEL if tier == "main" else FAST_MODEL
    if PROVIDER == "groq":
        return GroqLLM(model, cache)
    return MockLLM(model, cache)


# ------------------------------------------------------------------ mock scripts
def _num(text: str, decimal_comma: bool) -> float:
    text = text.strip()
    text = text.replace(".", "").replace(",", ".") if decimal_comma else text.replace(",", "")
    return float(text)


@MockLLM.register("InvoiceFields")
def _mock_extract(prompt: str, payload: dict) -> dict:
    """First pass assumes 1,234.56 formatting. It only switches to decimal-comma
    parsing after validation feedback mentions it: the mistake a real model can make."""
    text = prompt.split("<invoice>")[1].split("</invoice>")[0]
    eu = "decimal comma" in prompt.split("</invoice>")[1]

    def field(label: str) -> str:
        m = re.search(rf"^{label}[^:\n]*:\s*(.+)$", text, re.M)
        return m.group(1).strip() if m else ""

    lines = []
    for m in re.finditer(r"^\d+ \| (\S+) \| (.+?) \| Qty (\S+) \| Unit Price (\S+) \| Amount (\S+)$", text, re.M):
        lines.append({"sku": m.group(1), "description": m.group(2), "qty": _num(m.group(3), eu),
                      "unit_price": _num(m.group(4), eu), "amount": _num(m.group(5), eu)})
    po = field("PO Reference")
    return {"invoice_number": field("Invoice No"), "invoice_date": field("Invoice Date"),
            "vendor_id": field("Vendor ID"), "po_number": None if po in ("", "NONE") else po,
            "currency": field("Currency"), "lines": lines, "subtotal": _num(field("Subtotal"), eu),
            "tax": _num(field("Tax"), eu), "total": _num(field("Total Due"), eu)}


_UNCITED_FIRST_DRAFT = {"PRICE_VARIANCE", "BANK_DETAIL_CHANGE"}
_ACTION = {
    "PRICE_VARIANCE": "Route to the buyer to amend the PO or reject the overcharge.",
    "QTY_MISMATCH": "Hold and refer to Receiving until the outstanding quantity is receipted or credited.",
    "DUPLICATE": "Reject and return to the vendor with the posting date of the original.",
    "MISSING_PO": "Route to the cost centre owner for non-PO approval.",
    "BANK_DETAIL_CHANGE": "Hold and refer to the Vendor Master team for call-back verification.",
    "VENDOR_INACTIVE": "Hold and refer to the Vendor Master team to confirm vendor status.",
    "PROMPT_INJECTION": "Hold and refer to Security Review; do not act on text inside the document.",
    "TOOL_FAILURE": "Hold for an AP analyst; a source system could not be reached.",
    "NONE": "Route to the approver named in the approval matrix before posting.",
}


@MockLLM.register("ResolutionMemo")
def _mock_memo(prompt: str, payload: dict) -> dict:
    inv, exc = payload["invoice"], payload["primary_exception"]
    retrieved = [c["id"] for c in payload.get("policy_chunks", [])]
    revising = bool(payload.get("critique"))
    if exc in _UNCITED_FIRST_DRAFT and not revising:
        citations = []                      # scripted weak first draft: no citation
    else:
        wanted = payload.get("policy")
        citations = [wanted] if wanted in retrieved else retrieved[:1]
    details = [e["detail"] for e in payload.get("exceptions", [])] or ["Three-way match passed"]
    label = "fully matched, approval required by the matrix" if exc == "NONE" else exc.replace("_", " ").lower()
    return {
        "summary": f"Invoice {inv['invoice_number']} from {inv['vendor_id']} for {inv['total']:,.2f} "
                   f"{inv['currency']}: {label}. Disposition {payload['disposition']}, "
                   f"owner {payload['approver']}.",
        "facts": details + [f"Invoice total {inv['total']:,.2f} {inv['currency']}"],
        "recommended_action": _ACTION.get(exc, _ACTION["NONE"]),
        "citations": citations,
    }


@MockLLM.register("Critique")
def _mock_critique(prompt: str, payload: dict) -> dict:
    memo = payload["memo"]
    retrieved = {c["id"] for c in payload.get("policy_chunks", [])}
    issues = []
    if not memo.get("citations"):
        issues.append("No policy section is cited; add the section that supports the action.")
    issues += [f"Citation {c} is not in the retrieved policy." for c in memo.get("citations", []) if c not in retrieved]
    if not memo.get("facts"):
        issues.append("No supporting figures are given.")
    if payload["invoice"]["invoice_number"] not in memo.get("summary", ""):
        issues.append("Summary does not name the invoice.")
    return {"passed": not issues, "issues": issues}


@MockLLM.register("JudgeScore")
def _mock_judge(prompt: str, payload: dict) -> dict:
    memo = payload["memo"]
    retrieved = {c["id"] for c in payload.get("policy_chunks", [])}
    cites = memo.get("citations", [])
    grounded = 5 if cites and all(c in retrieved for c in cites) else (2 if cites else 1)
    topic = "fully matched" if payload["primary_exception"] == "NONE" else payload["primary_exception"].replace("_", " ").lower()
    relevant = 5 if topic in memo.get("summary", "").lower() else 3
    correct = 5 if payload.get("expected_citation") in cites else 2
    notes = []
    if grounded < 5:
        notes.append("citations missing or not in retrieved context")
    if correct < 5:
        notes.append(f"expected citation {payload.get('expected_citation')} not present")
    return {"groundedness": grounded, "relevance": relevant, "correctness": correct,
            "rationale": "; ".join(notes) or "Claims are supported by the cited section and the invoice figures."}
