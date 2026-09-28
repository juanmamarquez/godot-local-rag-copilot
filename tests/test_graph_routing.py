"""Unit tests for routing decisions that do not require Ollama or ChromaDB."""

from src.graph import parse_router_decision, route_decision


def test_route_decision_for_each_value_when_local_rag_is_enabled() -> None:
    assert route_decision("docs", disable_local=False) == ["retrieve_docs_node"]
    assert route_decision("local", disable_local=False) == ["retrieve_local_node"]
    assert route_decision("both", disable_local=False) == [
        "retrieve_docs_node",
        "retrieve_local_node",
    ]
    assert route_decision("none", disable_local=False) == ["generate_node"]


def test_route_decision_for_each_value_when_local_rag_is_disabled() -> None:
    assert route_decision("docs", disable_local=True) == ["retrieve_docs_node"]
    assert route_decision("local", disable_local=True) == ["generate_node"]
    assert route_decision("both", disable_local=True) == ["retrieve_docs_node"]
    assert route_decision("none", disable_local=True) == ["generate_node"]


def test_parse_router_decision_accepts_noisy_model_output() -> None:
    assert parse_router_decision('"DOCS."') == "docs"
    assert parse_router_decision("Use local context, please.") == "local"
    assert parse_router_decision("both sources") == "both"
    assert parse_router_decision("none") == "none"


def test_parse_router_decision_falls_back_to_both() -> None:
    assert parse_router_decision("I am not sure") == "both"
