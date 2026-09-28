import os
from typing import TypedDict, Annotated, Sequence, Literal
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from src.llm import get_llm
from src.vector_store import get_docs_retriever, get_local_retriever
from src.prompts import ROUTER_PROMPT, GENERATOR_PROMPT

load_dotenv()

DISABLE_LOCAL_RAG_ROUTING = os.getenv("DISABLE_LOCAL_RAG_ROUTING", "false").strip().lower() == "true"

RouterDecision = Literal["docs", "local", "both", "none"]
NextNode = Literal["retrieve_docs_node", "retrieve_local_node", "generate_node"]

# Define AgentState
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    docs_context: str
    local_context: str
    router_decision: str

# GRAPH NODES that represents the steps in the workflow. 
# Each node is an async function that takes the current state and returns a dictionary 
# of outputs to be added to the state.
async def router_node(state: AgentState) -> dict[str, str]:
    """Analizes last message and decides routing."""
    llm = get_llm()

    # First step: isolate the last message to avoid the history confusing the router.
    last_message = state["messages"][-1].content

    messages = [
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=last_message)
    ]

    response = await llm.ainvoke(messages)

    decision = parse_router_decision(str(response.content))

    return {"router_decision": decision}

async def retrieve_docs_node(state: AgentState) -> dict[str, str]:
    """Retrieves chunks from Godot's official documentation."""
    retriever = get_docs_retriever()
    last_message = state["messages"][-1].content
    docs = await retriever.ainvoke(last_message)
    # Add the title of the source document (metadata generated during ingestion) 
    # so the LLM can cite which page each chunk comes from
    context = "\n\n".join([
        f"--- Source: {d.metadata.get('doc_title', "Godot\'s Documentation")} ---\n{d.page_content}"
        for d in docs
    ])
    return {"docs_context": context}

async def retrieve_local_node(state: AgentState) -> dict[str, str]:
    """Retrieves chunks from the user's local .gd scripts."""
    retriever = get_local_retriever()
    last_message = state["messages"][-1].content
    docs = await retriever.ainvoke(last_message)
    # Add the path of the file (and the function, if detected during ingestion)
    # so the LLM knows which script and which part it is reading
    def label(d: Document) -> str:
        path = d.metadata.get("relative_path", "Unknown path")
        fn = d.metadata.get("function")
        return f"{path} (function: {fn})" if fn else path

    context = "\n\n".join([
        f"--- File: {label(d)} ---\n{d.page_content}"
        for d in docs
    ])
    return {"local_context": context}

async def generate_node(state: AgentState) -> dict[str, str]:
    """Generates the final response by combining the available contexts."""
    llm = get_llm()
    # Empty strings over nonsense text like "No context available" as defined on 
    # system prompt GENERATOR_PROMPT, so rule 5 ("if a block is empty, ignore it")
    # applies properly instead of giving the LLM a phrase it might end up quoting.
    docs_ctx = state.get("docs_context", "")
    local_ctx = state.get("local_context", "")

    sys_msg = SystemMessage(content=GENERATOR_PROMPT.format(
        docs_context=docs_ctx,
        local_context=local_ctx
    ))

    # Merging messages to send to the LLM
    messages = [sys_msg] + list(state["messages"])
    response = await llm.ainvoke(messages)

    return {"messages": [response]}

# CONDITIONAL GRAPH NODES are defined as functions that determine the next node(s) 
# to execute based on the current state.

def parse_router_decision(decision_text: str) -> RouterDecision:
    """Extract a routing decision from a tolerant LLM response."""
    normalized = decision_text.lower()
    if "both" in normalized:
        return "both"
    if "docs" in normalized:
        return "docs"
    if "local" in normalized:
        return "local"
    if "none" in normalized:
        return "none"
    return "both"


def route_decision(
    decision: RouterDecision,
    disable_local: bool = DISABLE_LOCAL_RAG_ROUTING,
) -> list[NextNode]:
    """Return the graph nodes required for a router decision."""
    if decision == "docs":
        return ["retrieve_docs_node"]
    elif decision == "local":
        return ["generate_node"] if disable_local else ["retrieve_local_node"]
    elif decision == "both":
        # LangGraph will parallelize the execution of these two nodes
        return ["retrieve_docs_node"] if disable_local else ["retrieve_docs_node", "retrieve_local_node"]

    # If it's "none", we skip directly to generating the response (e.g., out of context challenges, greetings, etc.)
    return ["generate_node"]

# GRAPH DEFINITION: We define the workflow graph using the StateGraph class, adding nodes and edges and configure 
# the flow of the graph, starting from the router node and defining conditional edges based on the routing decision.

workflow = StateGraph(AgentState)

workflow.add_node("router_node", router_node)
workflow.add_node("retrieve_docs_node", retrieve_docs_node)
workflow.add_node("retrieve_local_node", retrieve_local_node)
workflow.add_node("generate_node", generate_node)

workflow.set_entry_point("router_node")

# Add conditional edges from the router to the retrievers or directly to generation
workflow.add_conditional_edges(
    "router_node",
    lambda state: route_decision(state["router_decision"]),
    [
        "retrieve_docs_node",
        "generate_node",
    ] if DISABLE_LOCAL_RAG_ROUTING else [
        "retrieve_docs_node",
        "retrieve_local_node",
        "generate_node",
    ]
)

# After retrieving context, converge on generation
workflow.add_edge("retrieve_docs_node", "generate_node")
workflow.add_edge("retrieve_local_node", "generate_node")
workflow.add_edge("generate_node", END)

# Compile graph (optimized for asynchronous execution)
app = workflow.compile()
