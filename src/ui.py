import streamlit as st
import asyncio
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

sys.path.append(str(Path(__file__).parent.parent))
from src.graph import app as workflow_app

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
HISTORY_FILE = DATA_DIR / "chat_history.json"
GODOT_PROJECT_PATH = os.getenv("GODOT_PROJECT_PATH", "Not configured")

# Claude Sonnet 5 API prices (USD per million tokens).
CLAUDE_PRICE_INPUT_1M = 2.00
CLAUDE_PRICE_OUTPUT_1M = 10.00

st.set_page_config(page_title="Godot RAG Copilot", page_icon="🤖", layout="wide")

# --- State initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_input_tokens" not in st.session_state:
    st.session_state.total_input_tokens = 0
if "total_output_tokens" not in st.session_state:
    st.session_state.total_output_tokens = 0

# --- Helper functions ---
def load_history():
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                messages = []
                
                if isinstance(data, list):
                    msg_list = data
                else:
                    msg_list = data.get("messages", [])
                    st.session_state.total_input_tokens = data.get("total_input_tokens", 0)
                    st.session_state.total_output_tokens = data.get("total_output_tokens", 0)

                for msg in msg_list:
                    if msg["type"] == "human":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["type"] == "ai":
                        messages.append(AIMessage(content=msg["content"]))
                
                return messages
        except Exception:
            return []
    return []

def save_history(messages):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "total_input_tokens": st.session_state.total_input_tokens,
        "total_output_tokens": st.session_state.total_output_tokens,
        "messages": []
    }
    for msg in messages:
        if isinstance(msg, HumanMessage):
            data["messages"].append({"type": "human", "content": msg.content})
        elif isinstance(msg, AIMessage):
            data["messages"].append({"type": "ai", "content": msg.content})
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def clear_context():
    st.session_state.messages = []
    st.session_state.total_input_tokens = 0
    st.session_state.total_output_tokens = 0
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()

if not st.session_state.messages and HISTORY_FILE.exists():
    st.session_state.messages = load_history()

# --- Sidebar ---
with st.sidebar:
    st.title("Settings")
    st.write(f"**Local project:**\n`{GODOT_PROJECT_PATH}`")
    
    st.markdown("### Vector database status")
    docs_exists = (DATA_DIR / "chroma_docs").exists()
    local_exists = (DATA_DIR / "chroma_local").exists()
    
    st.write(f"{'✅' if docs_exists else '❌'} **Godot 4.7 API docs**")
    st.write(f"{'✅' if local_exists else '❌'} **Local project code**")
    
    st.markdown("---")
    st.markdown("### Usage metrics")
    
    token_turn_placeholder = st.empty()
    token_global_placeholder = st.empty()
    money_saved_placeholder = st.empty()
    
    def render_token_stats(turn_in=0, turn_out=0, turn_reasoning=0):
        with token_turn_placeholder.container():
            st.caption("Tokens — Latest turn")
            col1, col2 = st.columns(2)
            col1.metric("Input", turn_in)
            col2.metric("Output", turn_out)
            
            if turn_reasoning > 0:
                st.metric("Reasoning", turn_reasoning)
            
        with token_global_placeholder.container():
            st.caption("Tokens — Session total")
            col3, col4 = st.columns(2)
            col3.metric("Total Input", st.session_state.total_input_tokens)
            col4.metric("Total Output", st.session_state.total_output_tokens)
            
        with money_saved_placeholder.container():
            st.markdown("---")
            st.markdown("### 💰 Local vs. cloud cost")
            
            # Calculate the estimated savings in USD.
            cost_input = (st.session_state.total_input_tokens / 1_000_000) * CLAUDE_PRICE_INPUT_1M
            cost_output = (st.session_state.total_output_tokens / 1_000_000) * CLAUDE_PRICE_OUTPUT_1M
            total_saved = cost_input + cost_output
            
            st.metric("Estimated cloud cost", f"${total_saved:.4f}")
            st.caption("Based on Claude Sonnet 5 pricing (`$2/MTok` input, `$10/MTok` output). *Inference for this session is free on your GPU.*")

    render_token_stats()
        
    st.markdown("---")
    if st.button("🗑️ Clear context", use_container_width=True):
        clear_context()
        st.rerun()

# --- Main application ---
st.logo("https://godotengine.org/assets/press/logo_large_monochrome_dark.png", size="large")
st.image("https://godotengine.org/assets/press/logo_large_monochrome_dark.png", width=120)
st.title("Copilot for Godot 4")
st.caption("A local development assistant with hybrid RAG. Get answers grounded in the official Godot documentation and your project code.")

for msg in st.session_state.messages:
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(msg.content)

if prompt := st.chat_input("Ask a question (e.g., How do I instantiate a scene?)..."):
    st.session_state.messages.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)
        
    with st.chat_message("assistant"):
        status_placeholder = st.empty()
        response_placeholder = st.empty()
        
        async def process_stream():
            initial_state = {"messages": st.session_state.messages}
            full_response = ""
            decision = ""
            turn_input = 0
            turn_output = 0
            turn_reasoning = 0
            
            async for event in workflow_app.astream_events(initial_state):
                
                if event["event"] == "on_chain_end" and event["name"] == "router_node":
                    output = event["data"].get("output", {})
                    if isinstance(output, dict) and "router_decision" in output:
                        decision = output["router_decision"]
                    
                    badges = {
                        "docs": "📘 **Context:** Godot documentation",
                        "local": "📁 **Context:** Local project",
                        "both": "🧠 **Hybrid context:** Godot docs + project",
                        "none": "💬 **Context:** General chat"
                    }
                    badge = badges.get(decision, "🧠 **Hybrid context**")
                    status_placeholder.caption(badge)
                    
                if event["event"] == "on_chat_model_stream" and event.get("metadata", {}).get("langgraph_node") == "generate_node":
                    chunk = event["data"]["chunk"]
                    token = chunk.content
                    if token:
                        full_response += token
                        response_placeholder.markdown(full_response + "▌")
                        
                    if hasattr(chunk, "usage_metadata") and chunk.usage_metadata is not None:
                        turn_input = chunk.usage_metadata.get("input_tokens", 0)
                        turn_output = chunk.usage_metadata.get("output_tokens", 0)
                        
                        if "reasoning_tokens" in chunk.usage_metadata:
                            turn_reasoning = chunk.usage_metadata.get("reasoning_tokens", 0)
            
            response_placeholder.markdown(full_response)
            return full_response, turn_input, turn_output, turn_reasoning
            
        final_text, t_in, t_out, t_reasoning = asyncio.run(process_stream())
        
        st.session_state.total_input_tokens += t_in
        st.session_state.total_output_tokens += t_out
        
        render_token_stats(t_in, t_out, t_reasoning)
        
        st.session_state.messages.append(AIMessage(content=final_text))
        save_history(st.session_state.messages)
