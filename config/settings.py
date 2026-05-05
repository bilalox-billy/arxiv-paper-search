"""
Configuration settings for ArXiv Paper Search System
"""
import os
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv

# Base directories
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
PDF_DIR = DATA_DIR / 'pdfs'
LOG_DIR = DATA_DIR / 'logs'

# Ensure directories exist
PDF_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# load .env file
load_dotenv()

# Database Configuration
DB_CONFIG: Dict[str, str] = {
    'dbname': os.getenv('DB_NAME', 'arxiv_search'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5433'),
    'client_encoding': 'utf8'
}

# Embedding Configuration
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
EMBEDDING_DIMENSION = 384  # For all-MiniLM-L6-v2

# Alternative models:
# - all-mpnet-base-v2: 768 dimensions, more accurate but slower
# - all-MiniLM-L12-v2: 384 dimensions, good balance
# - paraphrase-multilingual-MiniLM-L12-v2: 384 dimensions, multilingual

# Text Processing
CHUNK_SIZE = 768           # Target chunk size in tokens
MIN_CHUNK_SIZE = 256       # Minimum chunk size
MAX_CHUNK_SIZE = 1024      # Maximum chunk size
CHUNK_OVERLAP = 128        # Overlap between chunks

# Processing Configuration
BATCH_SIZE = 100           # Batch size for embedding generation
MAX_WORKERS = 4            # Parallel workers for PDF processing
MAX_RETRIES = 3            # Maximum retry attempts

# ArXiv API Configuration
ARXIV_RATE_LIMIT = 3.0     # Seconds between requests
ARXIV_MAX_RESULTS = 100    # Maximum results per query
ARXIV_TIMEOUT = 30         # Request timeout in seconds

# PDF Configuration
PDF_TIMEOUT = 30           # Download timeout in seconds
PDF_MAX_SIZE_MB = 50       # Maximum PDF size in MB
PDF_RETENTION_DAYS = 90    # Days to keep PDFs

# Search Configuration
DEFAULT_SEARCH_MODE = 'hybrid'  # vector, hybrid, or keyword
DEFAULT_LIMIT = 10              # Default number of search results
VECTOR_WEIGHT = 0.6             # Weight for vector search in hybrid mode
KEYWORD_WEIGHT = 0.4            # Weight for keyword search in hybrid mode
MIN_SIMILARITY_SCORE = 0.3      # Minimum similarity threshold

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Feature Flags
ENABLE_PDF_DOWNLOAD = True
ENABLE_WEB_UI = True
ENABLE_ANALYTICS = True

# SQL Schema Path
SCHEMA_PATH = BASE_DIR / 'sql' / 'schema.sql'
