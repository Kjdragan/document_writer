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
    from datetime import datetime
    sys.path.append(str(Path(__file__).parent.parent))

from src.document_writer import DocumentWriter

# Initialize console globally
console = Console()

# Load environment variables
load_dotenv()

# Configure logger
logger.remove()

def main():
    """
    Main entry point for the document writer application
    """
    try:
        # Configure logging with timestamped file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"document_writer_{timestamp}.log")
        
        # Add file handler with timestamp
        logger.add(
            log_file,
            rotation="1 day",
            retention="7 days",
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )
        
        # Add console logger for immediate feedback
        logger.add(
            sys.stderr,
            format="{time:HH:mm:ss} | {level: <8} | {message}",
            level="INFO"
        )

        # Log application start
        logger.info("Document Writer Application Started")
        console.print("[bold green]Document Writer Application[/]")
        
        while True:
            # Display menu
            console.print("\nChoose an action:")
            console.print("1. Create New Document")
            console.print("2. Continue Latest Document")
            console.print("3. Exit")
            
            # Get user choice
            choice = Prompt.ask("Choose an action [1/2/3]", default="1")
            
            # Log user choice
            logger.info(f"User selected option: {choice}")
            
            if choice == "1":
                create_document()
            elif choice == "2":
                continue_document()
            elif choice == "3":
                console.print("[yellow]Exiting Document Writer...[/]")
                logger.info("Application exit")
                break
            else:
                console.print("[red]Invalid choice. Please select 1, 2, or 3.[/]")
                logger.warning(f"Invalid menu choice: {choice}")
                
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/]")
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in main application: {str(e)}")
        console.print(f"[red]Critical error: {str(e)}[/]")

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
            logger.error(f"Missing environment variables: {missing_vars}")
            return
        
        # Log start of document creation process    
        logger.info("Starting document creation process")
        console.print("[bold blue]Document Writer[/]")
        console.print("[yellow]Checking environment and configuration...[/]")
            
        # Get topic from user
        topic = Prompt.ask("\n[bold blue]Enter the topic you want to research[/]")
        
        if not topic.strip():
            console.print("[red]Topic cannot be empty[/]")
            logger.warning("Empty topic provided")
            return
        
        # Log topic selection    
        logger.info(f"Selected topic: {topic}")
        console.print(f"[green]Selected Topic:[/] {topic}")
        
        # Create document writer
        writer = DocumentWriter()
        
        # Confirm document creation
        console.print("\n[yellow]Preparing to create document...[/]")
        if Prompt.ask("Do you want to proceed with document creation?", default=True):
            # Run document creation
            asyncio.run(writer.process_document(topic))
        else:
            console.print("[red]Document creation cancelled.[/]")
            logger.info("Document creation cancelled by user")

    except Exception as e:
        logger.exception("Error in document creation")
        console.print(f"[red]Error: {str(e)}[/]")

def continue_document():
    """
    Continue working on the latest document version with optional topic filter
    """
    try:
        # Log start of continue document process
        logger.info("Starting continue document process")
        console.print("[bold blue]Continue Document[/]")
        
        # Optional topic filter
        topic_filter = Prompt.ask(
            "\n[bold blue]Enter a topic filter (optional, press enter to skip)[/]", 
            default=""
        )
        
        # Log topic filter
        if topic_filter:
            logger.info(f"Using topic filter: {topic_filter}")
            console.print(f"[green]Topic Filter:[/] {topic_filter}")
        
        # Create document writer
        writer = DocumentWriter()
        
        # Run continue latest document
        asyncio.run(writer.continue_latest(topic_filter))
        
    except Exception as e:
        logger.error(f"Error in continue document: {str(e)}")
        console.print(f"[red]Error: {str(e)}[/]")

if __name__ == "__main__":
    main()