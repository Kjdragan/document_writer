import re
from typing import List
from pathlib import Path

def sanitize_filename(text: str) -> str:
    """
    Convert text to a safe filename
    
    Args:
        text: Text to convert
        
    Returns:
        Safe filename string
    """
    # Remove invalid characters
    text = re.sub(r'[<>:"/\\|?*]', '', text)
    # Replace spaces with underscores
    text = text.replace(' ', '_')
    # Convert to lowercase
    return text.lower()

def get_document_files(directory: Path, pattern: str = "*.md") -> List[Path]:
    """
    Get all document files in a directory matching pattern
    
    Args:
        directory: Directory to search
        pattern: File pattern to match
        
    Returns:
        List of matching file paths
    """
    return sorted(directory.glob(pattern))

def extract_metadata(content: str) -> tuple[dict, str]:
    """
    Extract YAML front matter metadata from document content
    
    Args:
        content: Document content with potential front matter
        
    Returns:
        Tuple of (metadata dict, remaining content)
    """
    if content.startswith('---\n'):
        # Find end of front matter
        end_idx = content.find('\n---\n', 4)
        if end_idx != -1:
            # Extract and parse metadata
            metadata_str = content[4:end_idx]
            metadata = {}
            for line in metadata_str.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()
            
            # Return metadata and remaining content
            return metadata, content[end_idx + 5:]
    
    # No metadata found
    return {}, content