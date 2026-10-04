"""Policy retrieval: split the policy files into sections and rank them with BM25.

BM25 is a keyword ranking function. It needs no model and no vector database, so
it runs anywhere. In production you would usually combine it with embeddings
(hybrid search); the interface, `search(query, k)`, stays the same.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from .config import DATA

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = set("a an the of to is and or for in on by with be it that this as at are not from which who its".split())


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


def load_chunks() -> list[dict]:
    """One chunk per policy section, with an id usable as a citation: 'AP-POL-01 §1.1'."""
    chunks = []
    for path in sorted((DATA / "policies").glob("*.md")):
        policy_id = path.name.split("_")[0]
        for block in re.split(r"\n## ", path.read_text())[1:]:
            heading, _, body = block.partition("\n")
            section = heading.split()[0]
            chunks.append({"id": f"{policy_id} {section}", "title": heading[len(section):].strip(),
                           "text": body.strip(), "source": path.name})
    return chunks


class PolicyRetriever:
    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = load_chunks()
        self.k1, self.b = k1, b
        self.docs = [_tokens(c["title"] + " " + c["text"]) for c in self.chunks]
        self.avg_len = sum(map(len, self.docs)) / len(self.docs)
        df = Counter(t for d in self.docs for t in set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int = 3) -> list[dict]:
        q = _tokens(query)
        scored = []
        for chunk, doc in zip(self.chunks, self.docs):
            tf = Counter(doc)
            score = sum(self.idf.get(t, 0) * tf[t] * (self.k1 + 1)
                        / (tf[t] + self.k1 * (1 - self.b + self.b * len(doc) / self.avg_len)) for t in q)
            scored.append({**chunk, "score": round(score, 3)})
        return sorted(scored, key=lambda c: -c["score"])[:k]
