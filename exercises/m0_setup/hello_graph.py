"""Module 0 - environment check. Run:  python exercises/m0_setup/hello_graph.py"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from typing import TypedDict

import langgraph
from importlib.metadata import version
from langgraph.graph import END, START, StateGraph

from finagent.config import FAST_MODEL, MAIN_MODEL, PROVIDER
from finagent.graph import load_invoice
from finagent.llm import get_llm
from finagent.schemas import InvoiceFields


class State(TypedDict, total=False):
    raw_text: str
    invoice_number: str
    total: float
    message: str


def read_invoice(state: State) -> dict:
    """Model node: one structured-output call."""
    invoice = get_llm().structured(InvoiceFields, f"Extract the invoice fields.\n<invoice>\n{state['raw_text']}\n</invoice>")
    return {"invoice_number": invoice.invoice_number, "total": invoice.total}


def greet(state: State) -> dict:
    """Action node: plain Python."""
    return {"message": f"Read {state['invoice_number']} for {state['total']:,.2f}. Environment is ready."}


builder = StateGraph(State)
builder.add_node("read_invoice", read_invoice)
builder.add_node("greet", greet)
builder.add_edge(START, "read_invoice")
builder.add_edge("read_invoice", "greet")
builder.add_edge("greet", END)
graph = builder.compile()

if __name__ == "__main__":
    print(f"python {sys.version.split()[0]} | langgraph {version('langgraph')} | provider {PROVIDER} "
          f"| main {MAIN_MODEL} | fast {FAST_MODEL}")
    print(graph.invoke({"raw_text": load_invoice("DOC-01")})["message"])
    print(graph.get_graph().draw_mermaid())
