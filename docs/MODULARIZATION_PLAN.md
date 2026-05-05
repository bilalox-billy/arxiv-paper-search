# ArXiv Paper Search System - Modularization Plan

## 📊 Project Overview

**Goal:** Refactor monolithic `complete.py` (1413 lines) into 12 modular, testable components

**Approach:** Incremental refactoring with testing after each phase

**Timeline:** 2-3 weeks with testing checkpoints

---

## 📋 Component Overview & Execution Order

| Phase | Component | Lines in complete.py | Template File | Priority | Dependencies |
|-------|-----------|---------------------|---------------|----------|--------------|
| **Phase 1: Foundation** |
| 1.1 | Database Schema & Connection | 151-295, 347-356 | `database.py` | 🔴 Critical | None |
| 1.2 | ArXiv API Client | 299-388, 328-338 | `arxiv_client.py` | 🔴 Critical | None |
| **Phase 2: Data Collection** |
| 2.1 | PDF Downloader | 390-402 | `pdf_downloader.py` | 🟡 High | arxiv_client |
| 2.2 | PDF Text Extraction | 404-454, 643-882 | `pdf_extraction_info.py` | 🟡 High | None |
| **Phase 3: Processing Pipeline** |
| 3.1 | Text Chunking | Not explicit in complete.py | `text_chunking.py` | 🟡 High | pdf_extraction |
| 3.2 | Embedding Generation | 456-462, 630-636 | `embedding.py` | 🔴 Critical | None |
| 3.3 | Embedding Pipeline | 464-536 | `embedding_pipeline.py` | 🟡 High | embedding, text_chunking, database |
| 3.4 | Paper Processor (Orchestrator) | 538-566, 299-536 | `pdf_processor.py` | 🟡 High | All above |
| **Phase 4: Search & Retrieval** |
| 4.1 | Similarity Search Engine | 887-1007, 1009-1028 | `similarity_search.py` | 🟡 High | database, embedding |
| **Phase 5: Analysis & UI** |
| 5.1 | Analytics Module | 1034-1207 | `search.py` (extended) | 🟢 Medium | database, search |
| 5.2 | Web UI (FastAPI) | 1212-1380 | `ui.py` | 🟢 Medium | search, database |
| 5.3 | CLI Interface | Already templated | `ui.py` | 🟢 Low | All components |

---

## 📝 Detailed Phase-by-Phase Implementation

### **PHASE 1: Foundation Layer**
**Goal:** Establish database connectivity and ArXiv API access  
**Status:** ⏳ Pending

#### Component 1.1: Database Module (`src/database.py`)

**Responsibilities:**
- PostgreSQL connection management
- pgvector extension setup
- Schema creation and migration
- CRUD operations for papers, chunks, embeddings
- Vector index management

**Code to Extract from complete.py:**
- Lines 40-52: pgvector setup functions
- Lines 151-295: Complete schema SQL
- Lines 347-356: Database connection
- Lines 464-536: Store paper methods

**Key Functions to Implement:**
```python
class DatabaseManager:
    def __init__(db_config: dict)
    def setup_schema()
    def verify_pgvector()
    def create_indexes()
    def get_connection()
    def insert_paper(paper: ArxivPaper) -> int
    def insert_chunks(paper_id: int, chunks: List[Dict])
    def get_paper(paper_id: int) -> Dict
    def paper_exists(arxiv_id: str) -> bool
```

**Testing Strategy:**
```bash
# Test 1: Connection
python -m pytest tests/test_database.py::test_connection

# Test 2: Schema creation
python -m pytest tests/test_database.py::test_schema_creation

# Test 3: Insert/retrieve paper
python -m pytest tests/test_database.py::test_paper_operations

# Test 4: Vector operations
python -m pytest tests/test_database.py::test_vector_operations
```

**Success Criteria:**
- [ ] Can connect to PostgreSQL
- [ ] pgvector extension enabled
- [ ] All tables created
- [ ] Can insert and retrieve papers
- [ ] Vector columns working

---

#### Component 1.2: ArXiv Client (`src/arxiv_client.py`)

**Responsibilities:**
- Query ArXiv API
- Rate limiting (3 seconds between requests)
- Error handling and retries
- Parse API responses into ArxivPaper dataclass

**Code to Extract from complete.py:**
- Lines 328-338: PaperMetadata dataclass (map to ArxivPaper)
- Lines 357-388: Fetch papers with backoff
- ArxivPipeline.fetch_papers() method

**Key Functions to Implement:**
```python
class ArxivClient:
    def __init__(rate_limit_seconds: float = 3.0)
    def search_papers(query: str, max_results: int) -> Generator[ArxivPaper]
    def fetch_by_ids(arxiv_ids: List[str]) -> Generator[ArxivPaper]
    def search_recent_papers(categories: List[str], days_back: int) -> Generator[ArxivPaper]
    def _parse_result(result: arxiv.Result) -> ArxivPaper
    def _enforce_rate_limit()
```

**Testing Strategy:**
```bash
# Test 1: Simple query
python -c "from src.arxiv_client import ArxivClient; 
           client = ArxivClient(); 
           papers = list(client.search_papers('cat:cs.AI', 5));
           print(f'Found {len(papers)} papers')"

# Test 2: Rate limiting
python -m pytest tests/test_arxiv_client.py::test_rate_limiting

# Test 3: Error handling
python -m pytest tests/test_arxiv_client.py::test_error_handling

# Test 4: Fetch by IDs
python -m pytest tests/test_arxiv_client.py::test_fetch_by_ids
```

**Success Criteria:**
- [ ] Can search ArXiv with query
- [ ] Rate limiting enforced
- [ ] ArxivPaper dataclass populated correctly
- [ ] Error handling works (network failures, API limits)
- [ ] Generator pattern works efficiently

---

### **PHASE 2: Data Collection Layer**
**Goal:** Download and extract PDF content  
**Status:** ⏳ Pending

#### Component 2.1: PDF Downloader (`src/pdf_downloader.py`)

**Responsibilities:**
- Download PDFs from ArXiv
- Organize file storage
- Validate downloaded files
- Retry logic for failed downloads
- Track storage statistics

**Code to Extract from complete.py:**
- Lines 390-402: Download PDF method

**Key Functions to Implement:**
```python
class PDFDownloader:
    def __init__(storage_path: str, max_retries: int, timeout: int)
    def download_pdf(pdf_url: str, arxiv_id: str, published_date: datetime) -> Tuple[bool, Path, str]
    def _get_pdf_path(arxiv_id: str, published_date: datetime) -> Path
    def _validate_pdf(pdf_path: Path) -> bool
    def get_storage_stats() -> Dict
    def cleanup_old_pdfs(days_to_keep: int)
```

**Storage Structure:**
```
data/pdfs/
├── 2024/
│   ├── 01/
│   │   ├── 2401.12345.pdf
│   │   └── 2401.12346.pdf
│   └── 02/
└── 2025/
```

**Testing Strategy:**
```bash
# Test 1: Download single PDF
python -m pytest tests/test_pdf_downloader.py::test_download_single

# Test 2: Validate PDF
python -m pytest tests/test_pdf_downloader.py::test_validate_pdf

# Test 3: Retry logic
python -m pytest tests/test_pdf_downloader.py::test_retry_logic

# Test 4: Storage organization
python -m pytest tests/test_pdf_downloader.py::test_storage_structure
```

**Success Criteria:**
- [ ] PDFs download successfully
- [ ] Files organized by date
- [ ] Validation catches corrupt files
- [ ] Retry logic works
- [ ] Storage stats accurate

---

#### Component 2.2: PDF Text Extraction (`src/pdf_extraction_info.py`)

**Responsibilities:**
- Extract text from PDFs with structure preservation
- Handle multi-column layouts
- Detect sections, tables, formulas
- Calculate extraction confidence
- Clean and normalize text

**Code to Extract from complete.py:**
- Lines 404-454: Basic PDF processing
- Lines 643-882: ContentProcessor class (extract_sections, extract_images, extract_formulas, extract_tables)

**Key Functions to Implement:**
```python
class PDFTextExtractor:
    def __init__()
    def extract_paper_text(pdf_path: str) -> Dict[str, any]
    def _extract_page(page, page_num: int) -> ExtractedPage
    def _detect_columns(blocks: Dict) -> bool
    def _extract_multicolumn(blocks: Dict) -> List[Dict]
    def _extract_singlecolumn(blocks: Dict) -> List[Dict]
    def _identify_sections(text: str) -> List[Dict]
    def _clean_extracted_text(text: str) -> str
    def _calculate_confidence(pages: List[ExtractedPage]) -> float
```

**Testing Strategy:**
```bash
# Test 1: Single column PDF
python -m pytest tests/test_pdf_extraction.py::test_single_column

# Test 2: Multi-column PDF
python -m pytest tests/test_pdf_extraction.py::test_multi_column

# Test 3: Section detection
python -m pytest tests/test_pdf_extraction.py::test_section_detection

# Test 4: Confidence calculation
python -m pytest tests/test_pdf_extraction.py::test_confidence_score
```

**Success Criteria:**
- [ ] Text extracted with reasonable accuracy
- [ ] Multi-column layouts handled
- [ ] Sections identified
- [ ] Confidence scores meaningful
- [ ] Text cleaned properly

---

### **PHASE 3: Processing Pipeline**
**Goal:** Convert raw text to searchable embeddings  
**Status:** ⏳ Pending

#### Component 3.1: Text Chunking (`src/text_chunking.py`)

**Responsibilities:**
- Split text into semantic chunks
- Maintain context with overlaps
- Respect section boundaries
- Optimize chunk sizes for embeddings
- Preserve metadata

**Key Functions to Implement:**
```python
class TextChunker:
    def __init__(target_chunk_size: int, min_chunk_size: int, max_chunk_size: int, overlap_size: int)
    def chunk_paper(text: str, sections: List[Dict], preserve_sections: bool) -> List[Dict]
    def _chunk_text(text: str, section_name: str) -> List[Dict]
    def _get_overlap_sentences(sentences: List[str], target_tokens: int) -> List[str]
```

**Chunk Structure:**
```python
{
    'text': str,              # The chunk text
    'section': str,           # Section name (if known)
    'start_char': int,        # Position in original text
    'end_char': int,          # End position
    'chunk_index': int,       # Sequential number
    'has_overlap': bool,      # Has overlap with previous
    'token_count': int,       # Approximate tokens
    'metadata': dict          # Additional info
}
```

**Testing Strategy:**
```bash
# Test 1: Basic chunking
python -m pytest tests/test_text_chunking.py::test_basic_chunking

# Test 2: Section preservation
python -m pytest tests/test_text_chunking.py::test_section_preservation

# Test 3: Overlap calculation
python -m pytest tests/test_text_chunking.py::test_overlap

# Test 4: Chunk size constraints
python -m pytest tests/test_text_chunking.py::test_size_constraints
```

**Success Criteria:**
- [ ] Chunks within size constraints
- [ ] Overlaps calculated correctly
- [ ] Section boundaries respected
- [ ] Metadata preserved
- [ ] No data loss

---

#### Component 3.2: Embedding Generator (`src/embedding.py`)

**Responsibilities:**
- Load and manage SentenceTransformer model
- Generate embeddings for text chunks
- Batch processing for efficiency
- Singleton pattern for model reuse
- Query embedding generation

**Code to Extract from complete.py:**
- Lines 456-462: generate_embeddings method
- Lines 630-636: Text embedder initialization

**Issues to Fix:**
- Lines 14-92 have duplicate code (needs cleanup)
- Singleton pattern needs refinement

**Key Functions to Implement:**
```python
class EmbeddingGenerator:
    # Singleton instance
    _instance = None
    
    def __new__(cls, *args, **kwargs)
    def __init__(model_name: str = 'all-MiniLM-L6-v2')
    def generate_embeddings(texts: List[str], show_progress: bool) -> np.ndarray
    def generate_query_embedding(query: str) -> np.ndarray
    def _preprocess_text(text: str) -> str
```

**Testing Strategy:**
```bash
# Test 1: Model loading
python -m pytest tests/test_embedding.py::test_model_loading

# Test 2: Single embedding
python -m pytest tests/test_embedding.py::test_single_embedding

# Test 3: Batch embeddings
python -m pytest tests/test_embedding.py::test_batch_embeddings

# Test 4: Singleton pattern
python -m pytest tests/test_embedding.py::test_singleton

# Test 5: Embedding dimensions
python -m pytest tests/test_embedding.py::test_embedding_dimensions
```

**Success Criteria:**
- [ ] Model loads successfully
- [ ] Embeddings generated correctly
- [ ] Singleton pattern works
- [ ] Batch processing efficient
- [ ] Correct dimensions (384 for MiniLM)

---

#### Component 3.3: Embedding Pipeline (`src/embedding_pipeline.py`)

**Responsibilities:**
- Orchestrate chunking → embedding → storage
- Batch processing for efficiency
- Progress tracking
- Content type detection (math, code, references)
- Database integration

**Code to Extract from complete.py:**
- Lines 464-536: Store paper method
- Lines 506-516: Store sections with embeddings

**Key Functions to Implement:**
```python
class EmbeddingPipeline:
    def __init__(db_config: dict, embedding_generator: EmbeddingGenerator, batch_size: int)
    def process_paper(paper_id: int, chunks: List[Dict]) -> Dict[str, any]
    def _store_chunks_with_embeddings(paper_id: int, chunks: List[Dict], embeddings: np.ndarray)
    def _detect_math(text: str) -> bool
    def _detect_code(text: str) -> bool
    def _detect_references(text: str) -> bool
    def process_pending_papers(limit: int) -> Dict[str, any]
```

**Testing Strategy:**
```bash
# Test 1: Process single paper
python -m pytest tests/test_embedding_pipeline.py::test_process_single_paper

# Test 2: Batch processing
python -m pytest tests/test_embedding_pipeline.py::test_batch_processing

# Test 3: Content detection
python -m pytest tests/test_embedding_pipeline.py::test_content_detection

# Test 4: Database storage
python -m pytest tests/test_embedding_pipeline.py::test_storage
```

**Success Criteria:**
- [ ] Chunks processed and stored
- [ ] Embeddings in database
- [ ] Content types detected
- [ ] Progress tracking works
- [ ] Error handling robust

---

#### Component 3.4: Paper Processor (`src/pdf_processor.py`)

**Responsibilities:**
- Main orchestrator for entire pipeline
- Coordinate: ArXiv → Download → Extract → Chunk → Embed → Store
- Parallel processing with ThreadPoolExecutor
- Queue management
- Statistics tracking

**Code to Extract from complete.py:**
- Lines 339-566: ArxivPipeline class
- Lines 538-566: run_pipeline method

**Key Functions to Implement:**
```python
class PaperProcessor:
    def __init__(db_config: dict, arxiv_client: ArxivClient, pdf_downloader: PDFDownloader, max_workers: int)
    def process_paper(query: str, max_papers: int, skip_existing: bool) -> dict
    def _upsert_paper(cursor, paper: ArxivPaper) -> int
    def process_queue(conn, stats: dict)
    def _process_download(item: dict) -> bool
```

**Processing Flow:**
```
ArXiv Query → Papers List
    ↓
Check DB (skip existing)
    ↓
Download Queue → ThreadPoolExecutor
    ↓
Extract Text → Chunk → Embed
    ↓
Store in Database
    ↓
Statistics Report
```

**Testing Strategy:**
```bash
# Test 1: Process 5 papers end-to-end
python -m pytest tests/test_paper_processor.py::test_process_batch

# Test 2: Skip existing papers
python -m pytest tests/test_paper_processor.py::test_skip_existing

# Test 3: Parallel processing
python -m pytest tests/test_paper_processor.py::test_parallel_processing

# Test 4: Error handling
python -m pytest tests/test_paper_processor.py::test_error_handling

# Test 5: Statistics
python -m pytest tests/test_paper_processor.py::test_statistics
```

**Success Criteria:**
- [ ] End-to-end processing works
- [ ] Parallel processing functional
- [ ] Skip existing papers
- [ ] Statistics accurate
- [ ] Error recovery

---

### **PHASE 4: Search & Retrieval**
**Goal:** Enable semantic and hybrid search  
**Status:** ⏳ Pending

#### Component 4.1: Similarity Search Engine (`src/similarity_search.py`)

**Responsibilities:**
- Vector similarity search using pgvector
- Hybrid search (vector + keyword)
- Traditional keyword search
- Result ranking and filtering
- Find similar papers

**Code to Extract from complete.py:**
- Lines 887-1007: ArxivSearchEngine class
- Lines 1009-1028: Calculate paper relevance

**Key Functions to Implement:**
```python
class PaperSearchEngine:
    def __init__(db_config: dict, embedding_generator: EmbeddingGenerator)
    def search(query: str, mode: SearchMode, limit: int, filters: Dict) -> List[SearchResult]
    def _vector_search(query: str, limit: int, filters: Dict) -> List[SearchResult]
    def _hybrid_search(query: str, limit: int, filters: Dict) -> List[SearchResult]
    def _keyword_search(query: str, limit: int, filters: Dict) -> List[SearchResult]
    def _build_filter_clause(filters: Dict) -> Tuple[str, List]
    def _combine_results(vector_results, keyword_results, vector_weight, keyword_weight) -> List[SearchResult]
    def find_similar_papers(paper_id: int, limit: int) -> List[SearchResult]
```

**Search Modes:**
- **Vector:** Pure semantic similarity using embeddings
- **Hybrid:** 60% vector + 40% keyword
- **Keyword:** Traditional PostgreSQL full-text search

**Filters:**
```python
{
    'authors': List[str],        # Filter by author names
    'categories': List[str],     # ArXiv categories
    'date_from': str,            # Minimum date (ISO format)
    'date_to': str,              # Maximum date
    'min_score': float           # Minimum similarity score
}
```

**Testing Strategy:**
```bash
# Test 1: Vector search
python -m pytest tests/test_search.py::test_vector_search

# Test 2: Hybrid search
python -m pytest tests/test_search.py::test_hybrid_search

# Test 3: Keyword search
python -m pytest tests/test_search.py::test_keyword_search

# Test 4: Filters
python -m pytest tests/test_search.py::test_filters

# Test 5: Find similar
python -m pytest tests/test_search.py::test_find_similar

# Test 6: Relevance ranking
python -m pytest tests/test_search.py::test_relevance_ranking
```

**Success Criteria:**
- [ ] Vector search returns relevant results
- [ ] Hybrid search improves accuracy
- [ ] Filters work correctly
- [ ] Result ranking makes sense
- [ ] Performance acceptable (<2s for typical query)

---

### **PHASE 5: Analysis & UI (Optional)**
**Goal:** Provide user interfaces and analytics  
**Status:** ⏳ Pending

#### Component 5.1: Analytics Module (`src/search.py` extended)

**Responsibilities:**
- Citation network analysis
- Clustering and trend analysis
- Multimodal pattern detection
- Visualization support

**Code to Extract from complete.py:**
- Lines 1034-1207: Analytics functions

**Key Functions:**
```python
def build_citation_network(citations: List[Dict]) -> nx.DiGraph
def calculate_paper_influence(G: nx.DiGraph) -> Dict[str, float]
def cluster_similar_images(embeddings: np.ndarray) -> np.ndarray
def analyze_table_trends(table_data: List[Dict]) -> pd.DataFrame
def detect_outliers(df: pd.DataFrame, threshold: float) -> pd.DataFrame
def analyze_multimodal_patterns(paper_id: str, conn) -> Dict
def visualize_citation_network(G: nx.DiGraph, influence_scores: Dict)
def generate_trend_report(conn, timeframe: str) -> pd.DataFrame
```

**Testing Strategy:**
```bash
# Test with sample data
python -m pytest tests/test_analytics.py::test_citation_network
python -m pytest tests/test_analytics.py::test_clustering
python -m pytest tests/test_analytics.py::test_trends
```

**Success Criteria:**
- [ ] Citation network builds correctly
- [ ] Clustering produces meaningful groups
- [ ] Visualizations render
- [ ] Trend analysis accurate

---

#### Component 5.2: Web UI (`src/ui.py` - FastAPI)

**Responsibilities:**
- FastAPI web server
- Search interface
- Result display
- Interactive exploration

**Code to Extract from complete.py:**
- Lines 1212-1380: FastAPI application

**Endpoints:**
```python
GET  /                          # Main page
GET  /search-form/{search_type} # Dynamic search forms
GET  /search/semantic           # Semantic search
POST /search/formula            # Formula search
GET  /search/author             # Author search
GET  /paper/{paper_id}          # Paper details
GET  /similar/{paper_id}        # Similar papers
```

**Testing Strategy:**
```bash
# Start server
uvicorn src.ui:app --reload

# Test endpoints
curl http://localhost:8000/
curl "http://localhost:8000/search/semantic?semantic_query=machine+learning"
```

**Success Criteria:**
- [ ] Server starts successfully
- [ ] Search forms work
- [ ] Results display correctly
- [ ] Navigation functional

---

#### Component 5.3: CLI Interface (`src/ui.py` - Click)

**Responsibilities:**
- Command-line interface
- Interactive paper exploration
- Database management commands
- Export functionality

**Already Templated:** Yes (lines 1-92 in current ui.py)

**Commands:**
```bash
# Search
arxiv-search search -q "machine learning" -m hybrid -l 10

# Fetch papers
arxiv-search fetch -c cs.LG -c cs.AI -d 7 -m 100

# Database stats
arxiv-search stats

# Database management
arxiv-search manage --init
arxiv-search manage --rebuild-index
arxiv-search manage --cleanup
```

**Testing Strategy:**
```bash
# Manual testing
python -m src.ui search -q "transformers" -m vector
python -m src.ui fetch -c cs.AI -d 3
python -m src.ui stats
```

**Success Criteria:**
- [ ] All commands work
- [ ] Interactive exploration functional
- [ ] Export works
- [ ] Help text clear

---

## 🧪 Testing Strategy

### Unit Tests
Each component should have comprehensive unit tests:

```
tests/
├── test_database.py
├── test_arxiv_client.py
├── test_pdf_downloader.py
├── test_pdf_extraction.py
├── test_text_chunking.py
├── test_embedding.py
├── test_embedding_pipeline.py
├── test_paper_processor.py
├── test_search.py
└── test_analytics.py
```

### Integration Tests

```bash
# Phase 1: Database + ArXiv
tests/integration/test_phase1_integration.py

# Phase 2: Download + Extract
tests/integration/test_phase2_integration.py

# Phase 3: Full Pipeline
tests/integration/test_phase3_integration.py

# Phase 4: Search
tests/integration/test_phase4_integration.py
```

### End-to-End Test

```python
# tests/e2e/test_complete_workflow.py
def test_complete_workflow():
    """Test: Query → Download → Process → Search"""
    # 1. Fetch 5 papers from ArXiv
    # 2. Process all 5 papers
    # 3. Search for related content
    # 4. Verify results
    pass
```

---

## 🚀 Execution Timeline

### **Week 1: Foundation + Data Collection**
- **Day 1-2:** Phase 1.1 - Database Module
  - Implement + Unit Tests
  - Checkpoint: Can connect, create schema, insert/retrieve
  
- **Day 3:** Phase 1.2 - ArXiv Client
  - Implement + Unit Tests
  - Checkpoint: Can fetch papers with rate limiting
  
- **Day 4:** Phase 2.1 - PDF Downloader
  - Implement + Unit Tests
  - Checkpoint: Can download and validate PDFs
  
- **Day 5:** Phase 2.2 - PDF Extraction
  - Implement + Unit Tests
  - Checkpoint: Can extract text from PDFs

### **Week 2: Processing Pipeline**
- **Day 1:** Phase 3.1 - Text Chunking
  - Implement + Unit Tests
  - Checkpoint: Text chunked correctly
  
- **Day 2:** Phase 3.2 - Embedding Generation
  - Implement + Unit Tests
  - Checkpoint: Embeddings generated
  
- **Day 3:** Phase 3.3 - Embedding Pipeline
  - Implement + Unit Tests
  - Checkpoint: Chunks stored with embeddings
  
- **Day 4:** Phase 3.4 - Paper Processor
  - Implement + Unit Tests
  - Checkpoint: End-to-end processing works
  
- **Day 5:** Integration Testing Phase 1-3
  - Run integration tests
  - Fix issues
  - Performance testing

### **Week 3: Search + Polish**
- **Day 1-2:** Phase 4.1 - Search Engine
  - Implement all search modes
  - Unit + Integration Tests
  - Checkpoint: Search returns relevant results
  
- **Day 3:** Phase 5 (Optional)
  - CLI or Web UI
  - Basic functionality
  
- **Day 4:** End-to-End Testing
  - Complete workflow test
  - Performance optimization
  - Bug fixes
  
- **Day 5:** Documentation + Cleanup
  - Update README
  - Add usage examples
  - Clean up code
  - Remove complete.py (or archive it)

---

## 📦 Configuration & Setup

### Database Configuration

Create `config/settings.py`:
```python
import os
from pathlib import Path

# Database
DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'arxiv_search'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'password'),
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432')
}

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
PDF_DIR = DATA_DIR / 'pdfs'
LOG_DIR = DATA_DIR / 'logs'

# Embedding
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
EMBEDDING_DIMENSION = 384

# Processing
CHUNK_SIZE = 768
CHUNK_OVERLAP = 128
BATCH_SIZE = 100
MAX_WORKERS = 4

# ArXiv
ARXIV_RATE_LIMIT = 3.0  # seconds
ARXIV_MAX_RESULTS = 100

# Search
DEFAULT_SEARCH_MODE = 'hybrid'
DEFAULT_LIMIT = 10
```

### Environment Variables

Create `.env`:
```bash
POSTGRES_DB=arxiv_search
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Optional
EMBEDDING_MODEL=all-MiniLM-L6-v2
LOG_LEVEL=INFO
```

### Requirements

Already have `requirements.txt`, but key dependencies:
- `psycopg2-binary` - PostgreSQL adapter
- `pgvector` - Vector extension
- `arxiv` - ArXiv API client
- `sentence-transformers` - Embeddings
- `PyMuPDF` (fitz) - PDF processing
- `nltk` - Text processing
- `numpy` - Numerical operations
- `fastapi` - Web API (optional)
- `click` - CLI (optional)

---

## 🎯 Success Criteria

### Phase Completion Checklist

#### Phase 1: Foundation
- [ ] Database connection established
- [ ] pgvector extension enabled
- [ ] All tables created
- [ ] Can fetch papers from ArXiv
- [ ] Rate limiting works
- [ ] Integration test passes

#### Phase 2: Data Collection
- [ ] PDFs download successfully
- [ ] File validation works
- [ ] Text extraction accurate
- [ ] Multi-column handling works
- [ ] Integration test passes

#### Phase 3: Processing Pipeline
- [ ] Text chunked correctly
- [ ] Embeddings generated
- [ ] Chunks stored in database
- [ ] End-to-end processing works
- [ ] Can process 100+ papers
- [ ] Integration test passes

#### Phase 4: Search
- [ ] Vector search works
- [ ] Hybrid search improves results
- [ ] Filters function correctly
- [ ] Find similar papers works
- [ ] Performance < 2s per query
- [ ] Integration test passes

#### Phase 5: UI (Optional)
- [ ] CLI commands work
- [ ] Web interface functional (if implemented)
- [ ] Export works
- [ ] User-friendly

### Final Acceptance Criteria
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] End-to-end test passes
- [ ] Documentation complete
- [ ] Performance acceptable
- [ ] Code is maintainable
- [ ] Can be deployed easily

---

## 🔧 Key Decisions

### Already Made:
- ✅ Using PostgreSQL + pgvector
- ✅ Using sentence-transformers for embeddings
- ✅ Using PyMuPDF for PDF extraction
- ✅ Modular architecture with clear separation

### Need to Decide:
1. **Embedding Model:**
   - Current: `all-MiniLM-L6-v2` (384 dimensions, fast)
   - Alternative: `all-mpnet-base-v2` (768 dimensions, more accurate)
   - **Recommendation:** Start with MiniLM, upgrade if needed

2. **Search Default:**
   - Pure vector vs Hybrid
   - **Recommendation:** Hybrid (60% vector, 40% keyword)

3. **PDF Storage:**
   - Keep all PDFs vs Delete after processing
   - **Recommendation:** Keep PDFs for reprocessing

4. **Phase 5 Priority:**
   - CLI only vs CLI + Web UI
   - **Recommendation:** CLI first, Web UI if time permits

5. **Parallel Processing:**
   - ThreadPoolExecutor vs ProcessPoolExecutor
   - **Recommendation:** ThreadPoolExecutor (I/O bound tasks)

---

## 📚 Additional Resources

### SQL Schema File
Already have `sql/schema.sql` - will be populated from complete.py lines 151-295

### Scripts
- `scripts/setup_db.py` - Initialize database
- `scripts/fetch_papers.py` - Fetch papers
- `scripts/build_index.py` - Build vector index
- `scripts/verification.py` - Verify setup

### Documentation
- `README.md` - Main documentation
- `docs/api.md` - API documentation
- `docs/deployment.md` - Deployment guide
- `docs/troubleshooting.md` - Common issues

---

## 🐛 Known Issues & Workarounds

### Issue 1: Duplicate Code in embedding.py
**Problem:** Lines 14-92 have duplicate class definitions  
**Fix:** Clean up in Phase 3.2

### Issue 2: Schema Mismatch
**Problem:** complete.py schema uses different column names than templates  
**Fix:** Standardize in Phase 1.1

### Issue 3: Missing Error Handling
**Problem:** Some functions lack error handling  
**Fix:** Add during implementation

---

## 📞 Next Steps

1. **Review this plan** and approve/modify
2. **Set up environment** (PostgreSQL, Python packages)
3. **Start with Phase 1.1** (Database Module)
4. **Test after each component**
5. **Progress to next phase** only after tests pass

---

## 📝 Progress Tracking

| Component | Status | Tests Pass | Notes |
|-----------|--------|------------|-------|
| 1.1 Database | ⏳ Pending | - | - |
| 1.2 ArXiv Client | ⏳ Pending | - | - |
| 2.1 PDF Downloader | ⏳ Pending | - | - |
| 2.2 PDF Extraction | ⏳ Pending | - | - |
| 3.1 Text Chunking | ⏳ Pending | - | - |
| 3.2 Embedding | ⏳ Pending | - | - |
| 3.3 Embedding Pipeline | ⏳ Pending | - | - |
| 3.4 Paper Processor | ⏳ Pending | - | - |
| 4.1 Search Engine | ⏳ Pending | - | - |
| 5.1 Analytics | ⏳ Pending | - | Optional |
| 5.2 Web UI | ⏳ Pending | - | Optional |
| 5.3 CLI | ⏳ Pending | - | Optional |

**Legend:**
- ⏳ Pending
- 🚧 In Progress
- ✅ Complete
- ❌ Failed
- ⏭️ Skipped

---

**Last Updated:** 2026-05-05  
**Version:** 1.0
