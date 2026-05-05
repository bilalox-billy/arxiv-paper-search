"""
Database Management Module for ArXiv Paper Search System
Handles PostgreSQL connections, schema setup, and CRUD operations
"""

import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection as Connection
from psycopg2.extras import RealDictCursor, execute_values
from typing import Optional, Dict, List, Any, Tuple
import logging
from pathlib import Path
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages all database operations for the ArXiv Paper Search System.
    Handles connections, schema setup, and CRUD operations.
    """
    
    def __init__(self, db_config: Dict[str, str], schema_path: Optional[Path] = None):
        """
        Initialize database manager.
        
        Args:
            db_config: Dictionary with database connection parameters
                      (dbname, user, password, host, port)
            schema_path: Path to SQL schema file (optional)
        """
        self.db_config = db_config
        self.schema_path = schema_path
        self._conn: Optional[Connection] = None
        logger.info("DatabaseManager initialized")
    
    def get_connection(self) -> Connection:
        """
        Get or create a database connection.
        
        Returns:
            PostgreSQL connection object
        """
        if self._conn is None or self._conn.closed:
            try:
                self._conn = psycopg2.connect(**self.db_config)
                # Ensure UTF-8 encoding
                self._conn.set_client_encoding('UTF8')
                logger.info("Database connection established")
            except psycopg2.Error as e:
                logger.error(f"Failed to connect to database: {e}")
                raise
            except UnicodeDecodeError as e:
                logger.error(f"Unicode encoding error during connection: {e}")
                raise
        return self._conn
    
    def close_connection(self):
        """Close the database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.info("Database connection closed")
    
    def verify_pgvector(self) -> bool:
        """
        Check if pgvector extension is installed.
        
        Returns:
            True if pgvector is available, False otherwise
        """
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
                result = cur.fetchone()
                is_installed = result is not None
                
                if is_installed:
                    logger.info("pgvector extension verified")
                else:
                    logger.warning("pgvector extension not found")
                
                return is_installed
        except psycopg2.Error as e:
            logger.error(f"Error verifying pgvector: {e}")
            return False
    
    def setup_extensions(self):
        """
        Enable required PostgreSQL extensions.
        Creates vector, pg_trgm, and btree_gin extensions.
        """
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                # Enable pgvector for vector operations
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                logger.info("pgvector extension enabled")
                
                # Enable pg_trgm for text similarity
                cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
                logger.info("pg_trgm extension enabled")
                
                # Enable btree_gin for better indexing
                cur.execute("CREATE EXTENSION IF NOT EXISTS btree_gin;")
                logger.info("btree_gin extension enabled")
                
                conn.commit()
                logger.info("All extensions setup successfully")
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Error setting up extensions: {e}")
            raise
    
    def setup_schema(self, schema_path: Optional[Path] = None):
        """
        Create database schema from SQL file.
        
        Args:
            schema_path: Path to schema.sql file (uses instance path if not provided)
        """
        schema_file = schema_path or self.schema_path
        
        if not schema_file or not schema_file.exists():
            logger.error(f"Schema file not found: {schema_file}")
            raise FileNotFoundError(f"Schema file not found: {schema_file}")
        
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                # Read and execute schema file
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                
                cur.execute(schema_sql)
                conn.commit()
                logger.info(f"Database schema created from {schema_file}")
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Error creating schema: {e}")
            raise
        except IOError as e:
            logger.error(f"Error reading schema file: {e}")
            raise
    
    def paper_exists(self, arxiv_id: str) -> bool:
        """
        Check if a paper already exists in the database.
        
        Args:
            arxiv_id: ArXiv paper ID
            
        Returns:
            True if paper exists, False otherwise
        """
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT EXISTS(SELECT 1 FROM papers WHERE arxiv_id = %s)",
                    (arxiv_id,)
                )
                exists = cur.fetchone()[0]
                return exists
        except psycopg2.Error as e:
            logger.error(f"Error checking if paper exists: {e}")
            return False
    
    def insert_paper(self, paper_data: Dict[str, Any]) -> Optional[int]:
        """
        Insert a new paper or update if it exists.
        
        Args:
            paper_data: Dictionary containing paper metadata
                Required fields: arxiv_id, title, abstract
                Optional fields: authors, categories, published_date, etc.
        
        Returns:
            Paper ID (primary key) or None on failure
        """
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO papers (
                        arxiv_id, title, abstract, authors, categories,
                        primary_category, published_date, updated_date,
                        pdf_url, comment, journal_ref, doi
                    ) VALUES (
                        %(arxiv_id)s, %(title)s, %(abstract)s, %(authors)s,
                        %(categories)s, %(primary_category)s, %(published_date)s,
                        %(updated_date)s, %(pdf_url)s, %(comment)s,
                        %(journal_ref)s, %(doi)s
                    )
                    ON CONFLICT (arxiv_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        abstract = EXCLUDED.abstract,
                        updated_date = EXCLUDED.updated_date,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, paper_data)
                
                paper_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"Paper inserted/updated: {paper_data.get('arxiv_id')} (ID: {paper_id})")
                return paper_id
                
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Error inserting paper: {e}")
            return None
    
    def get_paper(self, paper_id: Optional[int] = None, arxiv_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve paper by ID or ArXiv ID.
        
        Args:
            paper_id: Database paper ID (primary key)
            arxiv_id: ArXiv paper ID
        
        Returns:
            Dictionary with paper data or None if not found
        """
        if not paper_id and not arxiv_id:
            logger.error("Either paper_id or arxiv_id must be provided")
            return None
        
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if paper_id:
                    cur.execute("SELECT * FROM papers WHERE id = %s", (paper_id,))
                else:
                    cur.execute("SELECT * FROM papers WHERE arxiv_id = %s", (arxiv_id,))
                
                result = cur.fetchone()
                return dict(result) if result else None
                
        except psycopg2.Error as e:
            logger.error(f"Error retrieving paper: {e}")
            return None
    
    def update_paper_status(self, paper_id: int, status_fields: Dict[str, Any]) -> bool:
        """
        Update paper processing status fields.
        
        Args:
            paper_id: Database paper ID
            status_fields: Dictionary with fields to update
                         (e.g., {'pdf_downloaded': True, 'pdf_processed': False})
        
        Returns:
            True if successful, False otherwise
        """
        if not status_fields:
            return True
        
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                # Build dynamic UPDATE query
                set_clause = ", ".join([f"{key} = %s" for key in status_fields.keys()])
                values = list(status_fields.values()) + [paper_id]
                
                cur.execute(
                    f"UPDATE papers SET {set_clause} WHERE id = %s",
                    values
                )
                conn.commit()
                logger.debug(f"Paper {paper_id} status updated: {status_fields}")
                return True
                
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Error updating paper status: {e}")
            return False
    
    def insert_chunks(self, paper_id: int, chunks: List[Dict[str, Any]]) -> bool:
        """
        Insert text chunks with embeddings for a paper.
        
        Args:
            paper_id: Database paper ID
            chunks: List of dictionaries containing chunk data
                   Required: chunk_text, chunk_index, embedding
                   Optional: section_name, page_number, has_math, etc.
        
        Returns:
            True if successful, False otherwise
        """
        if not chunks:
            logger.warning(f"No chunks to insert for paper {paper_id}")
            return True
        
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                # Prepare data for batch insert
                insert_data = []
                for chunk in chunks:
                    embedding_str = self._numpy_to_pgvector(chunk['embedding'])
                    insert_data.append((
                        paper_id,
                        chunk['chunk_index'],
                        chunk['chunk_text'],
                        chunk.get('chunk_tokens', 0),
                        embedding_str,
                        chunk.get('section_name'),
                        chunk.get('page_number'),
                        chunk.get('char_start'),
                        chunk.get('char_end'),
                        chunk.get('has_math', False),
                        chunk.get('has_code', False),
                        chunk.get('has_references', False)
                    ))
                
                # Batch insert
                execute_values(
                    cur,
                    """
                    INSERT INTO paper_chunks (
                        paper_id, chunk_index, chunk_text, chunk_tokens,
                        embedding, section_name, page_number, char_start,
                        char_end, has_math, has_code, has_references
                    ) VALUES %s
                    ON CONFLICT (paper_id, chunk_index) DO UPDATE SET
                        chunk_text = EXCLUDED.chunk_text,
                        embedding = EXCLUDED.embedding
                    """,
                    insert_data
                )
                
                conn.commit()
                logger.info(f"Inserted {len(chunks)} chunks for paper {paper_id}")
                return True
                
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Error inserting chunks: {e}")
            return False
    
    def get_paper_chunks(self, paper_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve all chunks for a paper.
        
        Args:
            paper_id: Database paper ID
        
        Returns:
            List of dictionaries containing chunk data
        """
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, chunk_index, chunk_text, section_name,
                           page_number, has_math, has_code, has_references
                    FROM paper_chunks
                    WHERE paper_id = %s
                    ORDER BY chunk_index
                    """,
                    (paper_id,)
                )
                return [dict(row) for row in cur.fetchall()]
                
        except psycopg2.Error as e:
            logger.error(f"Error retrieving chunks: {e}")
            return []
    
    def get_papers_needing_processing(self, operation: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get papers that need processing (download, extraction, embedding).
        
        Args:
            operation: Type of operation ('download', 'extraction', 'embedding')
            limit: Maximum number of papers to return
        
        Returns:
            List of paper dictionaries
        """
        status_field_map = {
            'download': 'pdf_downloaded',
            'extraction': 'pdf_processed',
            'embedding': 'embedding_generated'
        }
        
        status_field = status_field_map.get(operation)
        if not status_field:
            logger.error(f"Unknown operation: {operation}")
            return []
        
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT * FROM papers
                    WHERE {status_field} = FALSE
                      AND processing_error IS NULL
                    ORDER BY published_date DESC
                    LIMIT %s
                    """,
                    (limit,)
                )
                return [dict(row) for row in cur.fetchall()]
                
        except psycopg2.Error as e:
            logger.error(f"Error retrieving papers needing processing: {e}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the database.
        
        Returns:
            Dictionary with various statistics
        """
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                stats = {}
                
                # Total papers
                cur.execute("SELECT COUNT(*) as total FROM papers")
                stats['total_papers'] = cur.fetchone()['total']
                
                # Papers with PDFs downloaded
                cur.execute("SELECT COUNT(*) as count FROM papers WHERE pdf_downloaded = TRUE")
                stats['papers_downloaded'] = cur.fetchone()['count']
                
                # Papers processed
                cur.execute("SELECT COUNT(*) as count FROM papers WHERE pdf_processed = TRUE")
                stats['papers_processed'] = cur.fetchone()['count']
                
                # Papers with embeddings
                cur.execute("SELECT COUNT(*) as count FROM papers WHERE embedding_generated = TRUE")
                stats['papers_embedded'] = cur.fetchone()['count']
                
                # Total chunks
                cur.execute("SELECT COUNT(*) as total FROM paper_chunks")
                stats['total_chunks'] = cur.fetchone()['total']
                
                # Papers with errors
                cur.execute("SELECT COUNT(*) as count FROM papers WHERE processing_error IS NOT NULL")
                stats['papers_with_errors'] = cur.fetchone()['count']
                
                # Database size
                cur.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as size
                """)
                stats['database_size'] = cur.fetchone()['size']
                
                # Most recent paper date
                cur.execute("SELECT MAX(published_date) as latest FROM papers")
                latest = cur.fetchone()['latest']
                stats['latest_paper_date'] = latest.isoformat() if latest else None
                
                return stats
                
        except psycopg2.Error as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    def rebuild_vector_index(self, table: str = 'paper_chunks'):
        """
        Rebuild the HNSW vector index for better performance.
        
        Args:
            table: Table name (default: 'paper_chunks')
        """
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                # Drop existing index
                cur.execute(f"DROP INDEX IF EXISTS idx_chunks_embedding")
                
                # Recreate index
                cur.execute(f"""
                    CREATE INDEX idx_chunks_embedding ON {table}
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64)
                """)
                
                conn.commit()
                logger.info(f"Vector index rebuilt for {table}")
                
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Error rebuilding vector index: {e}")
            raise
    
    def cleanup_old_data(self, days: int = 90):
        """
        Remove papers older than specified days (optional maintenance).
        
        Args:
            days: Number of days to keep
        """
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM papers
                    WHERE published_date < CURRENT_DATE - INTERVAL '%s days'
                """, (days,))
                
                deleted_count = cur.rowcount
                conn.commit()
                logger.info(f"Deleted {deleted_count} papers older than {days} days")
                
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Error cleaning up old data: {e}")
            raise
    
    @staticmethod
    def _numpy_to_pgvector(array: np.ndarray) -> str:
        """
        Convert numpy array to pgvector format.
        
        Args:
            array: Numpy array
        
        Returns:
            String representation for pgvector
        """
        if isinstance(array, list):
            array = np.array(array)
        return '[' + ','.join(map(str, array.tolist())) + ']'
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_connection()
    
    def __del__(self):
        """Destructor to ensure connection is closed."""
        self.close_connection()
