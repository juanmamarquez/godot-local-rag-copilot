# Godot 4.7 Local RAG Copilot

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![Built with LangGraph](https://img.shields.io/badge/Built%20with-LangGraph-1C3C3C.svg)](https://www.langchain.com/langgraph)
[![Tests](https://github.com/juanmamarquez/godot-local-rag-copilot/actions/workflows/tests.yml/badge.svg)](https://github.com/juanmamarquez/godot-local-rag-copilot/actions/workflows/tests.yml)

> [Leer en español](README.es.md)

A local-first RAG copilot for Godot 4.7 game development. LangGraph routes questions between the official Godot documentation and GDScript files in a local project. Use it through a Streamlit chat UI or an OpenAI-compatible FastAPI endpoint.

![Streamlit UI preview](assets/streamlit_ui.png)

![LangGraph routing diagram](graph.png)

<video src="assets/vscode.mp4" width="1280" height="720" controls></video>

## Architecture and stack

- **Orchestration:** LangGraph and LangChain.
- **Local inference:** Ollama with `qwen2.5-coder:14b` for generation and `nomic-embed-text` for embeddings.
- **Vector storage:** ChromaDB indexes under `data/`.
- **Interfaces:** Streamlit UI and FastAPI/Uvicorn endpoint compatible with the OpenAI chat-completions format.
- **Maintenance:** Typer CLI for rebuilding the documentation and local-code indexes.

## Requirements and installation

Python 3.12+ and [Ollama](https://ollama.com/) are required. Ollama can run on the same machine or on a reachable inference host.

```bash
ollama pull qwen2.5-coder:14b
ollama pull nomic-embed-text
git clone https://github.com/juanmamarquez/godot-local-rag-copilot.git
cd godot-local-rag-copilot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Configure `.env`:

```env
GODOT_PROJECT_PATH=/absolute/path/to/your/godot-project
OLLAMA_HOST=http://localhost:11434
DISABLE_LOCAL_RAG_ROUTING=false
CORS_ALLOWED_ORIGINS=
```

## Build the local indexes

The first command downloads the `4.7` branch of the official `godot-docs` repository and builds its ChromaDB index. The second indexes every `.gd` file in `GODOT_PROJECT_PATH` and adds a synthetic project overview for broad architecture queries.

```bash
python scripts/cli.py reset-docs
python scripts/cli.py reset-local
```

`reset-local` indexes the GDScript files in `GODOT_PROJECT_PATH`.

## Usage

### Streamlit UI

Start the web UI with `streamlit run src/ui.py` and open <http://localhost:8501>. It shows the route chosen for each answer, token metrics, and a cloud-cost reference for the local session.

### OpenAI-compatible API

Start the streaming API to use the agent from a client such as Continue.dev:

```bash
DISABLE_LOCAL_RAG_ROUTING=true uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Set `DISABLE_LOCAL_RAG_ROUTING=true` when the client already sends relevant project code as context. The graph then skips local retrieval: a `local` route goes straight to generation, and a `both` route retrieves only the official documentation. The default is `false`, which keeps local retrieval enabled. Setting this variable in `.env` affects both FastAPI and Streamlit; setting it on the API command line limits it to that process.

The endpoint is `http://localhost:8000/v1/chat/completions`.

### CORS

CORS is disabled by default. Continue.dev calls the API from its extension host process, and the Streamlit UI imports the LangGraph workflow directly in-process — neither goes through a browser, so neither needs it.

Enable it only if you build a browser-based client that calls the API directly, by setting `CORS_ALLOWED_ORIGINS` in `.env` to a comma-separated list of the origins that should be allowed:

```env
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

The endpoint has no authentication, so keep this list as narrow as the client actually requires.

## Project layout

```text
src/       LangGraph workflow, Streamlit UI, and FastAPI service
scripts/   Typer CLI and ingestion pipelines
data/      Local vector indexes and source documents (ignored by Git)
assets/    README visuals
tests/     Pure unit tests for routing logic
```

## Testing

The unit tests cover only pure routing behavior; they do not mock or need Ollama or ChromaDB.

```bash
pytest tests
```

## Known limitations

- The API supports only Server-Sent Events streaming. Requests with `stream: false` return an explicit error.
- Routing relies on the textual output of the Qwen router. It tolerates common extra punctuation or prose, but unexpected output falls back to querying both sources.
- This is a single-user local prototype; it has no authentication, multi-tenant configuration, or production deployment setup.

## Conversation history

The Streamlit UI persists conversation history in a local `chat_history.json` file at the application layer, rather than as memory managed by the graph. That is sufficient for a single-user prototype that should survive a browser refresh or Streamlit restart.

LangGraph checkpointers such as `MemorySaver` and `SqliteSaver` solve a different layer: concurrent conversation threads, automatic long-context summaries, and state time-travel. They are deliberately not part of this prototype.

## License and related articles

The repository code is licensed under [MIT](LICENSE). The Bitacora.dev articles are separate works and remain licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). Neither license changes the other work.

This project accompanies the Spanish series on [Bitacora.dev](https://bitacora.dev): [part 1](https://bitacora.dev/engineering/desarrolla-copilot-privado-rag-parte-1), [part 2](https://bitacora.dev/engineering/desarrolla-copilot-privado-rag-parte-2), [part 3](https://bitacora.dev/engineering/desarrolla-copilot-privado-rag-parte-3), and [part 4](https://bitacora.dev/engineering/desarrolla-copilot-privado-rag-parte-4).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Small, focused contributions that preserve the educational and local-first nature of the project are welcome.
