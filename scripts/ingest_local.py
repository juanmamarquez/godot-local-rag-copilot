import os, sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document

sys.path.append(str(Path(__file__).parent.parent))
from src.llm import get_embeddings

load_dotenv()

GODOT_PROJECT_PATH = os.getenv("GODOT_PROJECT_PATH")
DATA_DIR = Path(__file__).parent.parent / "data"
CHROMA_LOCAL_DIR = DATA_DIR / "chroma_local"
COLLECTION_NAME = "godot_local_project"

def run_ingestion():
    if not GODOT_PROJECT_PATH or not os.path.exists(GODOT_PROJECT_PATH):
        print(f"ERROR: The project path is invalid ({GODOT_PROJECT_PATH}).")
        print("Make sure to configure GODOT_PROJECT_PATH in your .env file.")
        return

    print(f"📄 Scanning local project at: {GODOT_PROJECT_PATH}")
    loader = DirectoryLoader(
        GODOT_PROJECT_PATH, 
        glob="**/*.gd", 
        loader_cls=TextLoader,
        show_progress=True,
        use_multithreading=True,
        max_concurrency=8
    )
    docs = loader.load()
    
    if not docs:
        print("No .gd files found in the specified path.")
        return
        
    print(f"{len(docs)} .gd scripts loaded.")

    # Add each document's relative path to its metadata for use in the synthetic document.
    relative_paths = []
    for doc in docs:
        abs_path = doc.metadata.get("source", "")
        if abs_path:
            try:
                rel_path = os.path.relpath(abs_path, GODOT_PROJECT_PATH)
                doc.metadata["relative_path"] = rel_path
                relative_paths.append(rel_path)
            except ValueError:
                pass

    print("Chunking source code...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True,
    )
    splits = text_splitter.split_documents(docs)
    
    # RAG's "hack": injecting the synthetic document
    print("Generating synthetic global architecture document...")
    tree_structure = "\n".join(f"- {p}" for p in relative_paths)
    synthetic_content = f"""Global summary of the local project architecture:
The project contains a total exact of {len(docs)} .gd scripts.
The complete list of script files and folders is the following:
{tree_structure}

Use this information exclusively if the user asks how many scripts they have, how the project is organized, or which files exist in general.
"""
    synthetic_doc = Document(
        page_content=synthetic_content,
        metadata={
            "source": "synthetic_global_summary", 
            "relative_path": "Resumen_Global.txt"
        }
    )
    
    # Add the synthetic document to the splits so it can be retrieved by the RAG agent
    splits.append(synthetic_doc)
    # ------------------------------------------------------------

    print(f"{len(splits)} local chunks generated (including the global summary).")

    print("Saving embeddings in local ChromaDB...")
    Chroma.from_documents(
        documents=splits,
        embedding=get_embeddings(),
        persist_directory=str(CHROMA_LOCAL_DIR),
        collection_name=COLLECTION_NAME
    )
    print(f"Data ingestion completed successfully. Vector database ready at: {CHROMA_LOCAL_DIR}")

if __name__ == "__main__":
    run_ingestion()
