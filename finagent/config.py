"""Paths, thresholds, model names and prices used across the workshop."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TRACES = ROOT / "traces"

# Business rules (mirrors data/policies)
PRICE_TOLERANCE_PCT = 2.0
AUTO_APPROVE_LIMIT = 10_000
AP_MANAGER_LIMIT = 50_000

# Loop limits
MAX_EXTRACTION_ATTEMPTS = 3
MAX_REVISIONS = 2
MAX_TOOL_RETRIES = 3

# Models. With GROQ_API_KEY set, the workshop calls Groq's hosted open models.
# Without a key (or with LLM_PROVIDER=mock) it runs offline on a scripted stand-in.
PROVIDER = os.getenv("LLM_PROVIDER", "groq" if os.getenv("GROQ_API_KEY") else "mock").lower()
MAIN_MODEL = os.getenv("MAIN_MODEL", "llama-3.3-70b-versatile")   # reasoning-heavy steps
FAST_MODEL = os.getenv("FAST_MODEL", "llama-3.1-8b-instant")      # cheap, high-volume steps

# USD per million tokens. Approximate Groq list prices; the free tier costs nothing.
# They are here so the cost exercise has numbers: replace them with your own rates.
PRICES = {
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
}

# Simulated latency for the mock provider: (fixed ms, ms per output token)
MOCK_LATENCY = {
    "llama-3.3-70b-versatile": (350, 4.0),
    "llama-3.1-8b-instant": (150, 1.5),
}
