# Document Expansion Writer - Comprehensive MVP Implementation Plan

## 1. Project Setup with UV

### A. UV Package Management
1. Create virtual environment and install UV:
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install uv
```

2. Initialize project with pyproject.toml:
```toml
[project]
name = "document_writer"
version = "0.1.0"
requires-python = ">=3.10"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 120
```

3. Install dependencies using UV:
```bash
uv pip install --upgrade pip
uv add pydantic openai loguru typer python-dotenv tavily-python rich dirtyjson
```

## 2. Core Workflow Patterns (from article)

### A. Prompt Chaining Implementation
1. Research Flow
   - User Input → Tavily Search → Clean Data → Document Creation
2. Expansion Flow
   - New Topic → Research → Clean → Document Append
3. Editing Flow
   - Raw Document → Editor Review → Judge Review → Final/Revision

### B. Evaluator-Optimizer Implementation
1. Editor-Judge Loop
   - Editor Agent processes document
   - Judge Agent evaluates and provides structured feedback
   - Loop continues until approved

## 3. Data Models & Cleaning Strategy

### A. Core Pydantic Models
```python
class TavilySearchResult(BaseModel):
    content: str
    raw_content: Optional[str]
    publication_date: Optional[datetime]
    url: str
    title: Optional[str]

class DocumentState(BaseModel):
    content: str
    topics: List[str]
    version: int
    metadata: Dict[str, Any]
    sources: List[str]

class EditorResponse(BaseModel):
    content: str
    revision_notes: Optional[List[str]]
    version: int

class JudgeFeedback(BaseModel):
    approved: bool
    recommendations: List[str]
    revision_required: bool
```

### B. Data Cleaning Pipeline
1. Tavily Response Cleaning:
```python
def clean_tavily_response(raw_response: Dict) -> List[TavilySearchResult]:
    """
    1. Extract relevant fields (content, raw_content, url, date)
    2. Prefer raw_content over content when available
    3. Deduplicate by URL
    4. Remove entries with missing critical data
    5. Return cleaned, typed results
    """
```

## 4. File Management Structure

### A. Directory Organization
```
project/
├── src/
│   ├── models/
│   ├── agents/
│   ├── services/
│   └── utils/
├── _workproduct/
│   ├── 01_initial_research_[topic]_[timestamp].md
│   ├── 02_expansion_[topic]_[timestamp].md
│   ├── 03_editor_draft_[timestamp].md
│   └── 04_judge_review_[timestamp].md
└── output/
    └── final_document_[timestamp].md
```

### B. Version Control Strategy
- Iterative prefixes (01_, 02_, etc.)
- Descriptive naming pattern: `[prefix]_[stage]_[topic]_[timestamp].md`
- Each stage saved as separate file
- Full state captured in metadata section

## 5. Core Services Implementation

### A. Research Service:
```python
class ResearchService:
    def search(self, topic: str) -> List[TavilySearchResult]:
        """
        1. Execute Tavily search
        2. Clean response
        3. Extract relevant content
        4. Return typed results
        """

    def process_results(self, results: List[TavilySearchResult]) -> str:
        """
        1. Combine relevant content
        2. Format for document
        3. Include source attribution
        """
```

### B. Document Service:
```python
class DocumentService:
    def create_new(self, content: str, topic: str) -> DocumentState:
        """Initial document creation"""
    
    def append_content(self, current: DocumentState, new_content: str, topic: str) -> DocumentState:
        """Handle expansions"""
    
    def save_version(self, state: DocumentState, stage: str) -> Path:
        """Save to _workproduct with proper naming"""
```

## 6. Agent Implementation

### A. Editor Agent:
```python
class EditorAgent:
    def process_document(self, doc: DocumentState) -> EditorResponse:
        """
        Use GPT-4o-mini to:
        1. Analyze document structure
        2. Rewrite for coherence
        3. Return structured response
        """
```

### B. Judge Agent:
```python
class JudgeAgent:
    def review_document(self, original: DocumentState, edited: EditorResponse) -> JudgeFeedback:
        """
        1. Review changes
        2. Assess coherence
        3. Provide structured feedback
        """
```

## 7. Main Loop Implementation
```python
class DocumentWriter:
    def initial_research(self, topic: str) -> DocumentState:
        """Handle initial document creation"""

    def expansion_loop(self) -> bool:
        """
        1. Get user choice (expand/finalize)
        2. Handle new topic if expanding
        3. Return True if continuing
        """

    def editing_loop(self, doc: DocumentState) -> DocumentState:
        """
        1. Submit to editor
        2. Get judge review
        3. Loop until approved
        """
```

## 8. Implementation Order Checklist

1. [ ] Basic project setup with uv
2. [ ] Data models implementation
3. [ ] Tavily service & cleaning
4. [ ] Document management service
5. [ ] Editor agent implementation
6. [ ] Judge agent implementation
7. [ ] Main loop logic
8. [ ] File management & versioning
9. [ ] Integration testing