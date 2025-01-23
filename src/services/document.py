from datetime import datetime
from pathlib import Path
import json
from typing import Optional
from loguru import logger
from ..models import DocumentState

class DocumentService:
    def __init__(self, workproduct_dir: str = "_workproduct", output_dir: str = "output"):
        """
        Initialize document service
        
        Args:
            workproduct_dir: Directory for intermediate work products
            output_dir: Directory for final documents
        """
        self.workproduct_dir = Path(workproduct_dir)
        self.output_dir = Path(output_dir)
        
        # Ensure directories exist
        self.workproduct_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

    def create_new(self, content: str, topic: str) -> DocumentState:
        """
        Create initial document state
        
        Args:
            content: Initial document content
            topic: Main document topic
            
        Returns:
            New DocumentState instance
        """
        return DocumentState(
            content=content,
            topics=[topic],
            version=1,
            metadata={
                "created_at": datetime.now().isoformat(),
                "last_modified": datetime.now().isoformat()
            },
            sources=[]
        )

    def append_content(self, current: DocumentState, new_content: str, topic: str) -> DocumentState:
        """
        Handle document expansions by appending new content
        
        Args:
            current: Current document state
            new_content: Content to append
            topic: New topic being added
            
        Returns:
            Updated DocumentState
        """
        # Update document state
        current.content = f"{current.content}\n\n# {topic}\n\n{new_content}"
        current.topics.append(topic)
        current.version += 1
        current.metadata["last_modified"] = datetime.now().isoformat()
        
        return current

    def save_version(self, state: DocumentState, stage: str) -> Path:
        """
        Save document version to appropriate directory with proper naming
        
        Args:
            state: Current document state
            stage: Current processing stage (e.g., 'initial_research', 'expansion', 'editor_draft')
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        topic_slug = "_".join(state.topics[0].lower().split())
        
        # Determine prefix based on stage
        prefix_map = {
            "initial_research": "01",
            "expansion": "02",
            "editor_draft": "03",
            "judge_review": "04",
            "final": "final"
        }
        prefix = prefix_map.get(stage, "xx")
        
        # Determine target directory and filename
        is_final = stage == "final"
        target_dir = self.output_dir if is_final else self.workproduct_dir
        
        filename = f"{prefix}_{stage}_{topic_slug}_{timestamp}.md"
        file_path = target_dir / filename
        
        # Save document content
        try:
            # Add metadata as YAML front matter
            metadata_yaml = "---\n"
            metadata_yaml += f"version: {state.version}\n"
            metadata_yaml += f"topics: {', '.join(state.topics)}\n"
            metadata_yaml += f"last_modified: {state.metadata['last_modified']}\n"
            metadata_yaml += "---\n\n"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(metadata_yaml + state.content)
                
            logger.info(f"Saved document version to {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save document version: {str(e)}")
            raise

    def get_latest_version(self, topic: Optional[str] = None) -> Optional[DocumentState]:
        """
        Retrieve the latest version of a document
        
        Args:
            topic: Optional topic to filter by
            
        Returns:
            Latest DocumentState if found, None otherwise
        """
        try:
            # Get all markdown files in workproduct directory
            files = list(self.workproduct_dir.glob("*.md"))
            if not files:
                return None
                
            # Sort by timestamp in filename (assuming our naming convention)
            files.sort(key=lambda x: x.stem.split('_')[-1], reverse=True)
            
            # If topic provided, filter for matching files
            if topic:
                topic_slug = "_".join(topic.lower().split())
                files = [f for f in files if topic_slug in f.stem]
                
            if not files:
                return None
                
            # Read latest file
            latest_file = files[0]
            with open(latest_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse metadata and content
            metadata_end = content.find('---\n\n')
            if metadata_end != -1:
                metadata_str = content[4:metadata_end]  # Skip initial '---\n'
                metadata = {}
                for line in metadata_str.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip()
                        
                actual_content = content[metadata_end + 5:]  # Skip '---\n\n'
                
                return DocumentState(
                    content=actual_content,
                    topics=metadata.get('topics', '').split(', '),
                    version=int(metadata.get('version', 1)),
                    metadata={'last_modified': metadata.get('last_modified')},
                    sources=[]
                )
                
        except Exception as e:
            logger.error(f"Failed to retrieve latest version: {str(e)}")
            return None