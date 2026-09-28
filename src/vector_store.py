from pathlib import Path
from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStoreRetriever
from src.llm import get_embeddings

BASE_DIR = Path(__file__).parent.parent
CHROMA_DOCS_DIR = BASE_DIR / "data" / "chroma_docs"
CHROMA_LOCAL_DIR = BASE_DIR / "data" / "chroma_local"

def _get_vectorstore(collection_name: str, persist_directory: Path) -> Chroma:
    return Chroma(
        collection_name=collection_name,
        persist_directory=str(persist_directory),
        embedding_function=get_embeddings(),
    )

def get_docs_vectorstore() -> Chroma:
    return _get_vectorstore("godot_official_docs", CHROMA_DOCS_DIR)

def get_local_vectorstore() -> Chroma:
    return _get_vectorstore("godot_local_project", CHROMA_LOCAL_DIR)

def get_docs_retriever(k: int = 4) -> VectorStoreRetriever:
    return get_docs_vectorstore().as_retriever(search_kwargs={"k": k})

def get_local_retriever(k: int = 4) -> VectorStoreRetriever:
    return get_local_vectorstore().as_retriever(search_kwargs={"k": k})
