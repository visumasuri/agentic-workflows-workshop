"""Structured outputs (Pydantic) and the shared graph state (TypedDict)."""
from __future__ import annotations

import operator
from typing import Annotated, Literal, Optional, TypedDict

from pydantic import BaseModel, Field


# ---------- structured outputs the model must return ----------
class LineItem(BaseModel):
    sku: str
    description: str
    qty: float
    unit_price: float
    amount: float


class InvoiceFields(BaseModel):
    invoice_number: str
    invoice_date: str = Field(description="ISO date, YYYY-MM-DD")
    vendor_id: str
    po_number: Optional[str] = Field(default=None, description="null when the invoice quotes no PO")
    currency: str
    lines: list[LineItem]
    subtotal: float
    tax: float
    total: float


class ResolutionMemo(BaseModel):
    summary: str = Field(description="One or two sentences: what is wrong and what happens next")
    facts: list[str] = Field(description="Figures taken from the invoice, PO, receipt or vendor record")
    recommended_action: str
    citations: list[str] = Field(description="Policy section ids, e.g. 'AP-POL-01 §1.1'")


class Critique(BaseModel):
    passed: bool
    issues: list[str]


class JudgeScore(BaseModel):
    groundedness: int = Field(ge=1, le=5)
    relevance: int = Field(ge=1, le=5)
    correctness: int = Field(ge=1, le=5)
    rationale: str


Disposition = Literal["AUTO_APPROVE", "ROUTE_FOR_APPROVAL", "HOLD", "REJECT"]


# ---------- shared state: every node reads it and returns a partial update ----------
class AgentState(TypedDict, total=False):
    doc_id: str
    raw_text: str
    clean_text: str                      # text the model is allowed to see
    invoice_bank_account: str            # captured by code, never sent to the model
    security_flags: Annotated[list[str], operator.add]
    invoice: dict                        # InvoiceFields as a dict
    extraction_attempts: int
    validation_errors: list[str]
    po_lines: list[dict]
    grn_lines: list[dict]
    vendor: Optional[dict]
    history_hits: list[dict]
    tools_called: Annotated[list[str], operator.add]   # reducer: parallel nodes append
    tool_errors: Annotated[list[str], operator.add]
    exceptions: list[dict]
    primary_exception: str
    disposition: str
    approver: str
    policy_chunks: list[dict]
    memo: dict
    critique: dict
    revisions: int
    approval: dict
    posting: dict
    status: str


class MemoState(TypedDict, total=False):
    """State of the resolution subgraph: only what the memo loop needs.

    A subgraph with its own, narrower schema cannot touch the rest of the run,
    and keys with reducers (tools_called, security_flags) are not passed through it.
    """
    doc_id: str
    invoice: dict
    exceptions: list[dict]
    primary_exception: str
    disposition: str
    approver: str
    policy_chunks: list[dict]
    memo: dict
    critique: dict
    revisions: int
