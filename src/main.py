import asyncio
import os
from typing import Optional
import typer
from loguru import logger
from rich.console import Console
from dotenv import load_dotenv

# Adjust imports for direct execution
if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))

from src.document_writer import DocumentWriter

# Load environment variables
load_dotenv()

# Configure logger
logger.add(
    "logs/document_writer.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO"
)

app = typer.Typer()
console = Console()

@app.command()
def create(
    topic: str = typer.Argument(..., help="Initial topic to research"),
):
    """
    Create a new document based on the given topic
    """
    try:
        # Verify required environment variables
        required_vars = ["OPENAI_API_KEY", "TAVILY_API_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            console.print(f"[red]Missing required environment variables: {', '.join(missing_vars)}[/]")
            raise typer.Exit(1)
            
        # Create document writer
        writer = DocumentWriter()
        
        # Run main process
        asyncio.run(writer.process_document(topic))
        
    except Exception as e:
        logger.error(f"Error during document creation: {str(e)}")
        console.print(f"[red]Error: {str(e)}[/]")
        raise typer.Exit(1)

@app.command()
def continue_doc(
    topic: Optional[str] = typer.Argument(None, help="Topic to filter by (optional)")
):
    """
    Continue working on the latest document version
    """
    try:
        # Verify required environment variables
        required_vars = ["OPENAI_API_KEY", "TAVILY_API_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            console.print(f"[red]Missing required environment variables: {', '.join(missing_vars)}[/]")
            raise typer.Exit(1)
            
        # Create document writer
        writer = DocumentWriter()
        
        # Get latest version
        latest_doc = writer.document_service.get_latest_version(topic)
        
        if not latest_doc:
            console.print("[yellow]No existing document found.[/]")
            raise typer.Exit(1)
            
        # Run expansion and editing process
        asyncio.run(writer.process_document(latest_doc.topics[0]))
        
    except Exception as e:
        logger.error(f"Error while continuing document: {str(e)}")
        console.print(f"[red]Error: {str(e)}[/]")
        raise typer.Exit(1)

def main():
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Run CLI
    app()

if __name__ == "__main__":
    main()