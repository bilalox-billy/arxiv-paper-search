import sys
import os
from pathlib import Path
from dotenv import load_dotenv

def check_imports():
    """Verify all required packages are importable."""
    print("=" * 60)
    print("Checking package imports...")
    print("=" * 60)
    
    required_packages = {
        'arxiv': 'arxiv',
        'fitz': 'PyMuPDF',
        'psycopg2': 'psycopg2-binary',
        'sentence_transformers': 'sentence-transformers',
        'requests': 'requests',
        'numpy': 'numpy',
        'tqdm': 'tqdm',
        'dotenv': 'python-dotenv',
        'pgvector': 'pgvector'
    }
    
    failed_imports = []
    
    for module_name, package_name in required_packages.items():
        try:
            __import__(module_name)
            print(f"✓ {package_name:25s} - OK")
        except ImportError as e:
            print(f"✗ {package_name:25s} - FAILED")
            failed_imports.append((package_name, str(e)))
    
    if failed_imports:
        print("\n" + "=" * 60)
        print("FAILED IMPORTS:")
        for pkg, error in failed_imports:
            print(f"  - {pkg}: {error}")
        return False
    
    print("\nAll imports successful!\n")
    return True

def check_postgresql():
    """Verify PostgreSQL connection and pgvector extension."""
    print("=" * 60)
    print("Checking PostgreSQL connection...")
    print("=" * 60)
    
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        config_path = Path(__file__).parent.parent / "config" / ".env"
        load_dotenv(config_path)
        
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'arxiv_papers'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '')
        }
        
        print("Connecting to PostgreSQL:")
        print(f"  Host: {db_config['host']}:{db_config['port']}")
        print(f"  Database: {db_config['database']}")
        print(f"  User: {db_config['user']}")
        
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print("\n✓ PostgreSQL connection successful")
        print(f"  Version: {version.split(',')[0]}")
        
        cursor.execute("""
            SELECT EXISTS(
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            );
        """)
        has_pgvector = cursor.fetchone()[0]
        
        if has_pgvector:
            cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
            pgvector_version = cursor.fetchone()[0]
            print(f"✓ pgvector extension installed (version {pgvector_version})")
        else:
            print("✗ pgvector extension NOT installed")
            print("  Run: CREATE EXTENSION vector;")
            cursor.close()
            conn.close()
            return False
        
        cursor.close()
        conn.close()
        print("\nPostgreSQL check passed!\n")
        return True
        
    except Exception as e:
        print(f"\n✗ PostgreSQL check failed: {e}\n")
        return False

def check_model_download():
    """Verify the embedding model can be loaded."""
    print("=" * 60)
    print("Checking embedding model...")
    print("=" * 60)
    
    try:
        from sentence_transformers import SentenceTransformer
        
        config_path = Path(__file__).parent.parent / "config" / ".env"
        load_dotenv(config_path)
        
        model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        device = os.getenv('EMBEDDING_DEVICE', 'cpu')
        
        print(f"Loading model: {model_name}")
        print(f"Device: {device}")
        print("(This may take a moment on first run...)\n")
        
        model = SentenceTransformer(model_name, device=device)
        
        test_text = "This is a test sentence."
        embedding = model.encode(test_text)
        
        print("✓ Model loaded successfully")
        print(f"  Embedding dimension: {len(embedding)}")
        print(f"  Model max sequence length: {model.max_seq_length}")
        
        print("\nEmbedding model check passed!\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Model check failed: {e}\n")
        return False

def main():
    """Run all verification checks"""
    print("\n" + "=" * 60)
    print("ARXIV PAPER SEARCH - ENVIRONMENT VERIFICATION")
    print("=" * 60 + "\n")
    
    results = []
    
    results.append(("Package Imports", check_imports()))
    results.append(("PostgreSQL Connection", check_postgresql()))
    results.append(("Embedding Model", check_model_download()))
    
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for check_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{check_name:25s}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ All checks passed! Environment is ready.\n")
        return 0
    else:
        print("\n✗ Some checks failed. Please fix the issues above.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())



