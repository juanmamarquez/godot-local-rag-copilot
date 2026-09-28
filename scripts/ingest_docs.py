import shutil, sys, subprocess
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

sys.path.append(str(Path(__file__).parent.parent))
from src.llm import get_embeddings

REPO_URL = "https://github.com/godotengine/godot-docs.git"
BRANCH = "4.7"
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DOCS_DIR = DATA_DIR / "raw_docs"
CHROMA_DOCS_DIR = DATA_DIR / "chroma_docs"
COLLECTION_NAME = "godot_4_7_docs"

def clone_or_update_docs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    git_dir = RAW_DOCS_DIR / ".git"
    
    if not RAW_DOCS_DIR.exists() or not git_dir.exists():
        if RAW_DOCS_DIR.exists():
            print("raw_docs folder exists but isn't a valid Git repository. Cleaning...")            
            shutil.rmtree(RAW_DOCS_DIR)
            
        print(f"Cloning godot-docs repository (branch {BRANCH}). This may take a few minutes (git clone).")
        subprocess.run(
            ["git", "clone", "--branch", BRANCH, "--single-branch", REPO_URL, str(RAW_DOCS_DIR)],
            check=True
        )
        print("Repository has been cloned successfully.")
    else:
        print("The repository is already cloned. Fetching latest changes (git pull)")
        subprocess.run(["git", "-C", str(RAW_DOCS_DIR), "pull"], check=True)
        print("Repository updated.")

def run_ingestion():
    clone_or_update_docs()
    
    print("Loading .rst files...")
    loader = DirectoryLoader(
        str(RAW_DOCS_DIR), 
        glob="**/*.rst", 
        loader_cls=TextLoader,
        loader_kwargs={"autodetect_encoding": True},
        show_progress=True,
        use_multithreading=True,
        max_concurrency=8
    )
    docs = loader.load()
    
    if not docs:
        print(f"ERROR: No .rst files found in {RAW_DOCS_DIR}.")
        return

    print(f"{len(docs)} documents loaded from the Godot documentation.")

    print("Chunking documents...")
    text_splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.RST,
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True,
    )
    splits = text_splitter.split_documents(docs)
    total_splits = len(splits)
    print(f"{total_splits} chunks generated.")

    print("Saving embeddings in local ChromaDB...")
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_DOCS_DIR),
        embedding_function=get_embeddings()
    )

    # To prevent overloading Ollama, we ingest in batches of 100
    batch_size = 100
    for i in range(0, total_splits, batch_size):
        batch = splits[i:i + batch_size]
        vector_store.add_documents(batch)
        progress = min(i + batch_size, total_splits)
        print(f"Embeddings progress: {progress}/{total_splits} processed chunks...", end="\r")

    print(f"\n Data ingestion completed successfully. Vector database ready at: {CHROMA_DOCS_DIR}")

if __name__ == "__main__":
    run_ingestion()
