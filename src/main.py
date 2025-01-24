import asyncio
import os
from typing import Optional
from loguru import logger
from rich.console import Console
from rich.prompt import Prompt
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

console = Console()

def create_document():
    """
    Create a new document by prompting for a topic
    """
    try:
        # Verify required environment variables
        required_vars = ["OPENAI_API_KEY", "TAVILY_API_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            console.print(f"[red]Missing required environment variables: {', '.join(missing_vars)}[/]")
            return
            
        # Get topic from user
        topic = Prompt.ask("\n[bold blue]Enter the topic you want to research[/]")
        
        if not topic.strip():
            console.print("[red]Topic cannot be empty[/]")
            return
            
        # Create document writer
        writer = DocumentWriter()
        
        # Run main process
        asyncio.run(writer.process_document(topic))
        
    except Exception as e:
        logger.exception("Error in document creation")
        console.print(f"[red]Error: {str(e)}[/]")

def continue_document():
    """
    Continue working on the latest document version with optional topic filter
    """
    try:
        use_filter = Prompt.ask(
            "\n[bold blue]Do you want to filter by topic?[/]",
            choices=["y", "n"],
            default="n"
        )
        
        topic = None
        if use_filter.lower() == "y":
            topic = Prompt.ask("[bold blue]Enter topic to filter by[/]")
        
        writer = DocumentWriter()
        asyncio.run(writer.continue_latest(topic))
        
    except Exception as e:
        logger.exception("Error in document continuation")
        console.print(f"[red]Error: {str(e)}[/]")

def main():
    while True:
        console.print("\n[bold green]Document Writer[/]")
        choice = Prompt.ask(
            "Choose an action",
            choices=["1", "2", "3"],
            default="1"
        )
        
        if choice == "1":
            create_document()
        elif choice == "2":
            continue_document()
        else:
            break

if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    main()