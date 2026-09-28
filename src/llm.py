import os
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.embeddings import Embeddings
from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

def get_llm() -> ChatOllama:
    """Returns the configured LLM instance for local inference."""
    return ChatOllama(
        model="qwen2.5-coder:14b",
        base_url=OLLAMA_HOST,
        validate_model_on_init=True,
        temperature=0
    )

def get_embeddings() -> Embeddings:
    """Returns the configured embeddings instance."""
    return OllamaEmbeddings(
        model="nomic-embed-text",
        base_url=OLLAMA_HOST,
        validate_model_on_init=True
    )
