"""
Test script for Database Module - Phase 1.1
Run this to verify database connectivity and setup
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import DatabaseManager
from config.settings import DB_CONFIG, SCHEMA_PATH
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_connection():
    """Test 1: Database Connection"""
    print("\n" + "="*60)
    print("TEST 1: Database Connection")
    print("="*60)
    
    try:
        db = DatabaseManager(DB_CONFIG)
        conn = db.get_connection()
        
        # Test basic query
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print(f"✓ Connected to PostgreSQL")
            print(f"  Version: {version}")
        
        db.close_connection()
        print("✓ Connection closed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def test_extensions():
    """Test 2: PostgreSQL Extensions"""
    print("\n" + "="*60)
    print("TEST 2: PostgreSQL Extensions")
    print("="*60)
    
    try:
        db = DatabaseManager(DB_CONFIG)
        
        # Setup extensions
        db.setup_extensions()
        print("✓ Extensions setup completed")
        
        # Verify pgvector
        if db.verify_pgvector():
            print("✓ pgvector extension verified")
        else:
            print("✗ pgvector extension not found")
            return False
        
        db.close_connection()
        return True
        
    except Exception as e:
        print(f"✗ Extension setup failed: {e}")
        return False


def test_schema_creation():
    """Test 3: Schema Creation"""
    print("\n" + "="*60)
    print("TEST 3: Schema Creation")
    print("="*60)
    
    try:
        db = DatabaseManager(DB_CONFIG, SCHEMA_PATH)
        
        # Create schema
        db.setup_schema()
        print("✓ Schema created successfully")
        
        # Verify tables exist
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]
            
            expected_tables = [
                'papers', 'paper_chunks', 'authors', 'paper_authors',
                'categories', 'search_history', 'processing_queue'
            ]
            
            print(f"✓ Found {len(tables)} tables:")
            for table in tables:
                status = "✓" if table in expected_tables else "?"
                print(f"  {status} {table}")
        
        db.close_connection()
        return True
        
    except Exception as e:
        print(f"✗ Schema creation failed: {e}")
        return False


def test_paper_operations():
    """Test 4: Paper CRUD Operations"""
    print("\n" + "="*60)
    print("TEST 4: Paper CRUD Operations")
    print("="*60)
    
    try:
        from datetime import datetime
        
        db = DatabaseManager(DB_CONFIG)
        
        # Sample paper data
        test_paper = {
            'arxiv_id': '2024.12345',
            'title': 'Test Paper: Database Connectivity',
            'abstract': 'This is a test paper to verify database operations.',
            'authors': ['Test Author 1', 'Test Author 2'],
            'categories': ['cs.AI', 'cs.LG'],
            'primary_category': 'cs.AI',
            'published_date': datetime(2024, 1, 1),
            'updated_date': datetime(2024, 1, 1),
            'pdf_url': 'https://arxiv.org/pdf/2024.12345.pdf',
            'comment': None,
            'journal_ref': None,
            'doi': None
        }
        
        # Insert paper
        paper_id = db.insert_paper(test_paper)
        if paper_id:
            print(f"✓ Paper inserted with ID: {paper_id}")
        else:
            print("✗ Failed to insert paper")
            return False
        
        # Check if paper exists
        exists = db.paper_exists('2024.12345')
        print(f"✓ Paper exists check: {exists}")
        
        # Retrieve paper
        paper = db.get_paper(paper_id=paper_id)
        if paper:
            print(f"✓ Paper retrieved: {paper['title']}")
        else:
            print("✗ Failed to retrieve paper")
            return False
        
        # Update status
        success = db.update_paper_status(paper_id, {
            'pdf_downloaded': True,
            'pdf_processed': False
        })
        print(f"✓ Paper status updated: {success}")
        
        # Clean up test data
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM papers WHERE arxiv_id = '2024.12345'")
            conn.commit()
        print("✓ Test paper cleaned up")
        
        db.close_connection()
        return True
        
    except Exception as e:
        print(f"✗ Paper operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chunk_operations():
    """Test 5: Chunk Operations with Vectors"""
    print("\n" + "="*60)
    print("TEST 5: Chunk Operations with Vectors")
    print("="*60)
    
    try:
        import numpy as np
        from datetime import datetime
        
        db = DatabaseManager(DB_CONFIG)
        
        # Insert test paper first
        test_paper = {
            'arxiv_id': '2024.67890',
            'title': 'Test Paper for Chunks',
            'abstract': 'Testing chunk operations',
            'authors': ['Test Author'],
            'categories': ['cs.AI'],
            'primary_category': 'cs.AI',
            'published_date': datetime(2024, 1, 1),
            'updated_date': datetime(2024, 1, 1),
            'pdf_url': 'https://arxiv.org/pdf/2024.67890.pdf',
            'comment': None,
            'journal_ref': None,
            'doi': None
        }
        
        paper_id = db.insert_paper(test_paper)
        print(f"✓ Test paper created with ID: {paper_id}")
        
        # Create test chunks with embeddings
        test_chunks = []
        for i in range(3):
            # Generate random embedding (384 dimensions for MiniLM)
            embedding = np.random.rand(384).astype(np.float32)
            
            chunk = {
                'chunk_index': i,
                'chunk_text': f'This is test chunk {i} with some content.',
                'chunk_tokens': 10,
                'embedding': embedding,
                'section_name': 'introduction',
                'page_number': 1,
                'char_start': i * 100,
                'char_end': (i + 1) * 100,
                'has_math': False,
                'has_code': False,
                'has_references': False
            }
            test_chunks.append(chunk)
        
        # Insert chunks
        success = db.insert_chunks(paper_id, test_chunks)
        print(f"✓ Chunks inserted: {success}")
        
        # Retrieve chunks
        chunks = db.get_paper_chunks(paper_id)
        print(f"✓ Retrieved {len(chunks)} chunks")
        
        # Clean up
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM papers WHERE arxiv_id = '2024.67890'")
            conn.commit()
        print("✓ Test data cleaned up")
        
        db.close_connection()
        return True
        
    except Exception as e:
        print(f"✗ Chunk operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_stats():
    """Test 6: Database Statistics"""
    print("\n" + "="*60)
    print("TEST 6: Database Statistics")
    print("="*60)
    
    try:
        db = DatabaseManager(DB_CONFIG)
        
        stats = db.get_database_stats()
        
        print("✓ Database Statistics:")
        print(f"  Total Papers: {stats.get('total_papers', 0)}")
        print(f"  Papers Downloaded: {stats.get('papers_downloaded', 0)}")
        print(f"  Papers Processed: {stats.get('papers_processed', 0)}")
        print(f"  Papers Embedded: {stats.get('papers_embedded', 0)}")
        print(f"  Total Chunks: {stats.get('total_chunks', 0)}")
        print(f"  Papers with Errors: {stats.get('papers_with_errors', 0)}")
        print(f"  Database Size: {stats.get('database_size', 'Unknown')}")
        print(f"  Latest Paper Date: {stats.get('latest_paper_date', 'None')}")
        
        db.close_connection()
        return True
        
    except Exception as e:
        print(f"✗ Stats retrieval failed: {e}")
        return False


def run_all_tests():
    """Run all database tests"""
    print("\n" + "="*60)
    print("ARXIV PAPER SEARCH - DATABASE MODULE TEST SUITE")
    print("Phase 1.1: Database Setup Verification")
    print("="*60)
    
    tests = [
        ("Connection", test_connection),
        ("Extensions", test_extensions),
        ("Schema Creation", test_schema_creation),
        ("Paper Operations", test_paper_operations),
        ("Chunk Operations", test_chunk_operations),
        ("Database Stats", test_database_stats)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Database module is ready.")
        print("\nNext Steps:")
        print("1. Review the output above")
        print("2. Proceed to Phase 1.2: ArXiv Client")
        return True
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        print("\nTroubleshooting:")
        print("- Check PostgreSQL is running")
        print("- Verify database credentials in config/settings.py")
        print("- Ensure pgvector extension is installed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
