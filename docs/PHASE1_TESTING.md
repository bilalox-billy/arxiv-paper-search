# Phase 1.1: Database Module - Testing Guide

## ✅ What Was Implemented

- **`config/settings.py`** - Configuration management for the entire system
- **`src/database.py`** - Complete database module with all CRUD operations
- **`tests/test_database_setup.py`** - Comprehensive test suite
- **`.env.example`** - Environment variables template

## 🚀 Quick Start

### Step 1: Prerequisites

Ensure you have:
- PostgreSQL 14+ installed and running
- Python 3.8+ installed
- pgvector extension installed

**Check PostgreSQL:**
```bash
psql --version
```

**Check if PostgreSQL is running:**
```bash
# Windows
pg_ctl status

# Or check services
services.msc  # Look for "postgresql-x64-14" or similar
```

### Step 2: Install pgvector Extension

**Option A: If you have PostgreSQL from installer:**
```bash
# Download pgvector from: https://github.com/pgvector/pgvector
# Or use pre-built binaries for Windows
```

**Option B: Using Docker (Recommended for testing):**
```bash
docker run -d \
  --name arxiv-postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=arxiv_search \
  -p 5432:5432 \
  ankane/pgvector
```

### Step 3: Configure Database Connection

**Create `.env` file from template:**
```bash
cp .env.example .env
```

**Edit `.env` with your credentials:**
```bash
POSTGRES_DB=arxiv_search
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

**Alternative: Edit `config/settings.py` directly** if not using `.env`

### Step 4: Install Python Dependencies

```bash
# Activate your virtual environment first
# Windows
.\venv\Scripts\activate

# Then install dependencies
pip install psycopg2-binary numpy
```

### Step 5: Run Tests

```bash
python tests/test_database_setup.py
```

## 📊 Expected Output

If everything is configured correctly, you should see:

```
============================================================
ARXIV PAPER SEARCH - DATABASE MODULE TEST SUITE
Phase 1.1: Database Setup Verification
============================================================

============================================================
TEST 1: Database Connection
============================================================
✓ Connected to PostgreSQL
  Version: PostgreSQL 14.x ...
✓ Connection closed successfully

============================================================
TEST 2: PostgreSQL Extensions
============================================================
✓ Extensions setup completed
✓ pgvector extension verified

============================================================
TEST 3: Schema Creation
============================================================
✓ Schema created successfully
✓ Found 7 tables:
  ✓ authors
  ✓ categories
  ✓ paper_authors
  ✓ paper_chunks
  ✓ papers
  ✓ processing_queue
  ✓ search_history

============================================================
TEST 4: Paper CRUD Operations
============================================================
✓ Paper inserted with ID: 1
✓ Paper exists check: True
✓ Paper retrieved: Test Paper: Database Connectivity
✓ Paper status updated: True
✓ Test paper cleaned up

============================================================
TEST 5: Chunk Operations with Vectors
============================================================
✓ Test paper created with ID: 2
✓ Chunks inserted: True
✓ Retrieved 3 chunks
✓ Test data cleaned up

============================================================
TEST 6: Database Statistics
============================================================
✓ Database Statistics:
  Total Papers: 0
  Papers Downloaded: 0
  Papers Processed: 0
  Papers Embedded: 0
  Total Chunks: 0
  Papers with Errors: 0
  Database Size: 8337 kB
  Latest Paper Date: None

============================================================
TEST SUMMARY
============================================================
✓ PASS - Connection
✓ PASS - Extensions
✓ PASS - Schema Creation
✓ PASS - Paper Operations
✓ PASS - Chunk Operations
✓ PASS - Database Stats

Passed: 6/6

🎉 All tests passed! Database module is ready.

Next Steps:
1. Review the output above
2. Proceed to Phase 1.2: ArXiv Client
```

## 🐛 Troubleshooting

### Problem: Connection Refused
```
psycopg2.OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused
```

**Solution:**
- Check if PostgreSQL is running: `pg_ctl status`
- Start PostgreSQL service
- Verify port 5432 is not blocked by firewall

### Problem: pgvector Extension Not Found
```
✗ pgvector extension not found
```

**Solution:**
- Install pgvector extension for PostgreSQL
- For Docker: Use `ankane/pgvector` image
- For manual install: Follow https://github.com/pgvector/pgvector#installation

### Problem: Authentication Failed
```
psycopg2.OperationalError: FATAL: password authentication failed
```

**Solution:**
- Check username and password in `.env` or `config/settings.py`
- Verify PostgreSQL user exists: `psql -U postgres -c "\du"`
- Reset password if needed

### Problem: Database Does Not Exist
```
psycopg2.OperationalError: FATAL: database "arxiv_search" does not exist
```

**Solution:**
```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE arxiv_search;
```

### Problem: Permission Denied on Extension Creation
```
ERROR: permission denied to create extension "vector"
```

**Solution:**
- Use a superuser account (default: postgres)
- Or grant permissions: `ALTER USER your_user WITH SUPERUSER;`

## 📝 Database Module Features

### Core Functionality Implemented

✅ **Connection Management**
- `get_connection()` - Create/reuse connection
- `close_connection()` - Clean up
- Context manager support (`with` statement)

✅ **Setup Operations**
- `setup_extensions()` - Enable pgvector, pg_trgm, btree_gin
- `setup_schema()` - Create all tables from SQL file
- `verify_pgvector()` - Check extension availability

✅ **Paper Operations**
- `paper_exists()` - Check if paper already in DB
- `insert_paper()` - Insert or update paper metadata
- `get_paper()` - Retrieve by ID or ArXiv ID
- `update_paper_status()` - Update processing flags

✅ **Chunk Operations**
- `insert_chunks()` - Batch insert chunks with embeddings
- `get_paper_chunks()` - Retrieve all chunks for a paper

✅ **Maintenance**
- `get_database_stats()` - Database statistics
- `rebuild_vector_index()` - Rebuild HNSW index
- `cleanup_old_data()` - Remove old papers
- `get_papers_needing_processing()` - Queue management

## 🎯 Success Criteria Checklist

- [x] Can connect to PostgreSQL
- [x] pgvector extension enabled
- [x] All tables created from schema.sql
- [x] Can insert and retrieve papers
- [x] Vector columns working (chunks with embeddings)
- [x] CRUD operations functional
- [x] Statistics retrieval working
- [x] Context manager support
- [x] Error handling and logging

## 📈 Next Phase

Once all tests pass, you're ready for **Phase 1.2: ArXiv Client**

This will implement:
- Querying ArXiv API
- Rate limiting
- Paper metadata parsing
- Error handling and retries

## 💡 Usage Examples

### Basic Usage

```python
from src.database import DatabaseManager
from config.settings import DB_CONFIG, SCHEMA_PATH

# Initialize
db = DatabaseManager(DB_CONFIG, SCHEMA_PATH)

# Setup (first time only)
db.setup_extensions()
db.setup_schema()

# Insert a paper
paper_id = db.insert_paper({
    'arxiv_id': '2301.12345',
    'title': 'My Research Paper',
    'abstract': 'This paper discusses...',
    'authors': ['John Doe', 'Jane Smith'],
    'categories': ['cs.AI', 'cs.LG'],
    # ... more fields
})

# Check stats
stats = db.get_database_stats()
print(f"Total papers: {stats['total_papers']}")

# Close connection
db.close_connection()
```

### Using Context Manager

```python
from src.database import DatabaseManager
from config.settings import DB_CONFIG

with DatabaseManager(DB_CONFIG) as db:
    # Connection automatically managed
    paper = db.get_paper(arxiv_id='2301.12345')
    print(paper['title'])
    
# Connection automatically closed
```

## 📞 Questions?

If you encounter any issues:
1. Check the error message carefully
2. Review the troubleshooting section
3. Verify PostgreSQL and pgvector are properly installed
4. Check database credentials in `.env` or `config/settings.py`

Ready to proceed? Run the tests and let me know the results!
