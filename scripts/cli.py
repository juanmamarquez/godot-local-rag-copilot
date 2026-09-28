import shutil
import sys
from pathlib import Path
import typer

sys.path.append(str(Path(__file__).parent.parent))

from scripts.ingest_docs import run_ingestion as ingest_docs_run
from scripts.ingest_local import run_ingestion as ingest_local_run

cli = typer.Typer(
    help="CLI for maintaining the vector databases of the Godot local RAG agent.",
    add_completion=False
)

DATA_DIR = Path(__file__).parent.parent / "data"

@cli.command("reset-docs")
def reset_docs(
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion without asking for confirmation.")
):
    """
    Deletes the Chroma vector database of the official Godot documentation and re-launches data ingestion.
    """
    chroma_docs_dir = DATA_DIR / "chroma_docs"
    
    if not force:
        confirm = typer.confirm("⚠️ Are you sure you want to delete the Godot vector database and download it again?")
        if not confirm:
            typer.echo("Operation cancelled.")
            raise typer.Abort()
            
    if chroma_docs_dir.exists():
        shutil.rmtree(chroma_docs_dir)
        typer.secho(f"Directory {chroma_docs_dir} has been deleted.", fg=typer.colors.RED)
    else:
        typer.echo("The vector database did not exist previously.")
        
    typer.secho("Starting re-ingestion of the official documentation...", fg=typer.colors.GREEN)
    ingest_docs_run()


@cli.command("reset-local")
def reset_local(
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion without asking for confirmation.")
):
    """
    Deletes the Chroma vector database of your local project and rescans all .gd scripts.
    """
    chroma_local_dir = DATA_DIR / "chroma_local"
    
    if not force:
        confirm = typer.confirm("⚠️ Are you sure you want to delete the local vector database and rescan all .gd scripts?")
        if not confirm:
            typer.echo("Operation cancelled.")
            raise typer.Abort()
            
    if chroma_local_dir.exists():
        shutil.rmtree(chroma_local_dir)
        typer.secho(f"Directory {chroma_local_dir} has been deleted.", fg=typer.colors.RED)
    else:
        typer.echo("The local vector database did not exist previously.")
        
    typer.secho("Starting rescan and re-ingestion of your local code...", fg=typer.colors.GREEN)
    ingest_local_run()

if __name__ == "__main__":
    cli()
