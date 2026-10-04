"""Input and output guardrails. All deterministic: a guardrail you cannot test is not a control."""
from __future__ import annotations

import re

INJECTION_PATTERNS = [
    r"ignore (all |any )?(prior|previous|above) instructions",
    r"disregard (all |any )?(prior|previous|above)",
    r"(system|developer) (note|message|prompt)",
    r"approve this invoice (immediately|now)",
    r"without (matching|review|approval)",
]
_BANK = re.compile(r"(Bank Account:\s*)([A-Z]{2}[A-Z0-9]{10,32})")


def scan_for_injection(text: str) -> tuple[str, list[str]]:
    """Return (text with suspicious lines removed, list of findings)."""
    kept, findings = [], []
    for line in text.splitlines():
        if any(re.search(p, line, re.I) for p in INJECTION_PATTERNS):
            findings.append(line.strip()[:120])
        else:
            kept.append(line)
    return "\n".join(kept), findings


def capture_bank_account(text: str) -> str:
    m = _BANK.search(text)
    return m.group(2) if m else ""


def mask_bank_account(text: str) -> str:
    """Replace the bank account with its last four characters before the model sees it."""
    return _BANK.sub(lambda m: f"{m.group(1)}****{m.group(2)[-4:]}", text)


def validate_memo(memo: dict, allowed_citations: set[str], disposition: str) -> list[str]:
    """Output guardrail: block a memo that cites unknown policy or contradicts the decision."""
    problems = []
    for c in memo.get("citations", []):
        if c not in allowed_citations:
            problems.append(f"citation '{c}' was not in the retrieved policy")
    if not memo.get("citations"):
        problems.append("memo has no policy citation")
    text = (memo.get("summary", "") + " " + memo.get("recommended_action", "")).lower()
    if disposition != "AUTO_APPROVE" and "approve immediately" in text:
        problems.append("memo recommends immediate approval, which contradicts the disposition")
    if re.search(r"[A-Z]{2}\d{2}[A-Z0-9]{10,}", memo.get("summary", "") + " ".join(memo.get("facts", []))):
        problems.append("memo contains an unmasked bank account")
    return problems
