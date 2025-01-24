import asyncio
import os
import sys
import signal
import atexit
from datetime import datetime
from rich.console import Console
from rich.prompt import Prompt, Confirm
from loguru import logger
from dotenv import load_dotenv
from src.document_writer import DocumentWriter
import shutil

# Initialize console globally
console = Console()

# Load environment variables
load_dotenv()

def setup_logging():
    """Configure logging with proper file handling"""
    try:
        # Remove default logger
        logger.remove()
        
        # Configure timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join("logs", f"document_writer_{timestamp}.log")
        
        # Add file handler with rotation and retention
        logger.add(
            log_file,
            rotation="1 day",
            retention="7 days",
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            enqueue=True,  # Thread-safe logging
            catch=True,    # Catch exceptions
        )
        
        # Add console logger for immediate feedback
        logger.add(
            sys.stderr,
            format="{time:HH:mm:ss} | {level: <8} | {message}",
            level="INFO",
            enqueue=True,
            catch=True,
        )
        
        return log_file
    except Exception as e:
        console.print(f"[red]Error setting up logging: {str(e)}[/]")
        sys.exit(1)

def cleanup_logging(log_file):
    """Ensure proper cleanup of logging resources"""
    try:
        logger.info("Shutting down logging...")
        logger.remove()  # Remove all handlers
        
        # Small delay to ensure final messages are written
        from time import sleep
        sleep(0.1)
        
    except Exception as e:
        console.print(f"[red]Error during logging cleanup: {str(e)}[/]")

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    logger.info(f"Received signal {signum}")
    cleanup_logging(current_log_file)
    sys.exit(0)

async def create_document():
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
        console.print("\n[bold blue]Document Writer[/]")
            
        # Get topic from user
        topic = Prompt.ask("\n[bold blue]Enter the topic you want to research[/]")
        
        if not topic.strip():
            console.print("[red]Topic cannot be empty[/]")
            logger.warning("Empty topic provided")
            return
        
        # Log topic selection    
        logger.info(f"Selected topic: {topic}")
        console.print(f"[green]Selected Topic:[/] {topic}")
        
        # Create document writer and process document
        writer = DocumentWriter()
        await writer.process_document(topic)

    except Exception as e:
        logger.error(f"Error in document creation: {str(e)}")
        console.print(f"[red]Error: {str(e)}[/]")
        raise

async def continue_document():
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
        await writer.continue_latest(topic_filter)
        
    except Exception as e:
        logger.error(f"Error in continue document: {str(e)}")
        console.print(f"[red]Error: {str(e)}[/]")

def setup_directories():
    """Clean and recreate working directories"""
    # Remove default logger to prevent duplicate logging
    logger.remove()
    
    directories = ['logs', '_workproduct']
    
    for directory in directories:
        # Remove directory if it exists
        if os.path.exists(directory):
            try:
                print(f"Cleaning directory: {directory}")  # Use print instead of logger
                shutil.rmtree(directory)
            except Exception as e:
                print(f"Error cleaning {directory}: {str(e)}")
                
        # Create fresh directory
        try:
            print(f"Creating directory: {directory}")  # Use print instead of logger
            os.makedirs(directory)
        except Exception as e:
            print(f"Error creating {directory}: {str(e)}")
            raise

def main():
    """Main entry point for the document writer application"""
    try:
        writer = DocumentWriter()
        
        while True:
            console.print("\nChoose an action:")
            console.print("1. Create New Document")
            console.print("2. Continue Latest Document")
            console.print("3. Exit")
            
            choice = Prompt.ask("Choose an action", choices=["1", "2", "3"], default="1")
            logger.info(f"User selected option: {choice}")
            
            if choice == "1":
                logger.info("Starting document creation process")
                console.print("\nDocument Writer")
                asyncio.run(create_document())
            elif choice == "2":
                logger.info("Starting document continuation process")
                console.print("\nContinue Latest Document")
                asyncio.run(continue_document())
            else:
                logger.info("User chose to exit")
                break
                
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        console.print("\n[yellow]Shutting down gracefully...[/]")
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        console.print(f"\n[red]Critical error: {str(e)}[/]")
    finally:
        cleanup_logging(current_log_file)

if __name__ == "__main__":
    # Import here to avoid circular imports
    import shutil
    from src.document_writer import DocumentWriter
    from rich.prompt import Prompt
    from rich.console import Console
    
    console = Console()
    
    try:
        # Clean and setup directories before any logging
        setup_directories()
        
        # Now configure logging
        current_log_file = setup_logging()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Register cleanup for normal exit
        atexit.register(cleanup_logging, current_log_file)
        
        # Start application
        logger.info("Starting Document Writer Application")
        main()
    except Exception as e:
        console.print(f"\n[red]Critical error: {str(e)}[/]")