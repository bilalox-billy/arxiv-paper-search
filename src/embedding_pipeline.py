"""
Embedding Pipeline Module
Orchestrates chunking, embedding generation, and database storage
"""

from typing import List, Dict, Any
import numpy as np
import re
import logging
from src.embedding import EmbeddingGenerator
from src.database import DatabaseManager

logger = logging.getLogger(__name__)


class EmbeddingPipeline:
    """Complete pipeline for generating and storing embeddings."""
    
    def __init__(self,
                 db_config: dict,
                 embedding_generator: EmbeddingGenerator,
                 batch_size: int = 100):
        """
        Initialize embedding pipeline.
        
        Args:
            db_config: Database configuration dictionary
            embedding_generator: EmbeddingGenerator instance
            batch_size: Batch size for embedding generation
        """
        self.db_config = db_config
        self.embedding_generator = embedding_generator
        self.batch_size = batch_size
        self.db_manager = DatabaseManager(db_config)
        
        # Patterns for content detection
        self.math_pattern = re.compile(
            r'[\∫∑∏√∂∇≈≠≤≥±×÷∈∉⊂⊃∪∩]|'
            r'\$[^\$]+\$|'
            r'\\[a-zA-Z]+\{|'
            r'\b[a-z]\s*[=<>]\s*[0-9]'
        )
        
        self.code_pattern = re.compile(
            r'```|'
            r'def\s+\w+\s*\(|'
            r'class\s+\w+\s*[:\(]|'
            r'import\s+\w+|'
            r'from\s+\w+\s+import|'
            r'function\s+\w+\s*\(',
            re.IGNORECASE
        )
        
        self.reference_pattern = re.compile(
            r'\[\d+\]|'
            r'\(\w+\s+et\s+al\.,?\s+\d{4}\)|'
            r'\(\w+,?\s+\d{4}\)|'
            r'References?$|'
            r'Bibliography$',
            re.MULTILINE | re.IGNORECASE
        )
        
        logger.info(f"EmbeddingPipeline initialized with batch_size={batch_size}")
    
    def process_paper(self, 
                     paper_id: int,
                     chunks: List[Dict]) -> Dict[str, Any]:
        """
        Process all chunks for a single paper.
        Generates embeddings and stores in database.
        
        Args:
            paper_id: Database ID of the paper
            chunks: List of chunk dictionaries from TextChunker
            
        Returns:
            Dictionary with processing statistics
        """
        if not chunks:
            logger.warning(f"No chunks provided for paper {paper_id}")
            return {'success': False, 'error': 'No chunks'}
        
        try:
            logger.info(f"Processing {len(chunks)} chunks for paper {paper_id}")
            
            # Extract texts from chunks
            chunk_texts = [chunk['text'] for chunk in chunks]
            
            # Generate embeddings in batches
            logger.debug(f"Generating embeddings...")
            embeddings = self.embedding_generator.generate_embeddings(
                chunk_texts,
                batch_size=self.batch_size,
                show_progress=len(chunks) > 10  # Show progress for large papers
            )
            
            # Detect content types and standardize chunk format
            for i, chunk in enumerate(chunks):
                # Standardize key names for database
                # TextChunker uses 'text', database expects 'chunk_text'
                if 'text' in chunk and 'chunk_text' not in chunk:
                    chunk['chunk_text'] = chunk['text']
                elif 'chunk_text' not in chunk:
                    logger.warning(f"Chunk {i} missing text content")
                    chunk['chunk_text'] = ''
                
                # Clean text (remove NULL bytes which PostgreSQL can't handle)
                chunk['chunk_text'] = chunk['chunk_text'].replace('\x00', '')
                
                # Truncate section_name if too long (DB has VARCHAR(255) limit)
                if 'section_name' in chunk and chunk['section_name']:
                    if len(chunk['section_name']) > 255:
                        chunk['section_name'] = chunk['section_name'][:252] + '...'
                
                # Use the text for content detection
                text = chunk.get('chunk_text', chunk.get('text', ''))
                chunk['has_math'] = self._detect_math(text)
                chunk['has_code'] = self._detect_code(text)
                chunk['has_references'] = self._detect_references(text)
                chunk['embedding'] = embeddings[i]
            
            # Store in database
            logger.debug(f"Storing chunks in database...")
            success = self.db_manager.insert_chunks(paper_id, chunks)
            
            if success:
                # Update paper status
                self.db_manager.update_paper_status(paper_id, {
                    'embedding_generated': True
                })
                
                logger.info(f"Successfully processed paper {paper_id}: {len(chunks)} chunks")
                
                return {
                    'success': True,
                    'paper_id': paper_id,
                    'chunks_processed': len(chunks),
                    'chunks_with_math': sum(1 for c in chunks if c.get('has_math')),
                    'chunks_with_code': sum(1 for c in chunks if c.get('has_code')),
                    'chunks_with_references': sum(1 for c in chunks if c.get('has_references'))
                }
            else:
                logger.error(f"Failed to store chunks for paper {paper_id}")
                return {'success': False, 'error': 'Database storage failed'}
            
        except Exception as e:
            logger.error(f"Error processing paper {paper_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _store_chunks_with_embeddings(self,
                                     paper_id: int,
                                     chunks: List[Dict],
                                     embeddings: np.ndarray):
        """
        Store chunks and their embeddings in database.
        
        Args:
            paper_id: Database ID of the paper
            chunks: List of chunk dictionaries
            embeddings: Numpy array of embeddings
        """
        # Add embeddings to chunks
        for i, chunk in enumerate(chunks):
            chunk['embedding'] = embeddings[i]
        
        # Store in database
        self.db_manager.insert_chunks(paper_id, chunks)
    
    def _detect_math(self, text: str) -> bool:
        """
        Detect mathematical content in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if mathematical content detected
        """
        return bool(self.math_pattern.search(text))
    
    def _detect_code(self, text: str) -> bool:
        """
        Detect code snippets in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if code detected
        """
        return bool(self.code_pattern.search(text))
    
    def _detect_references(self, text: str) -> bool:
        """
        Detect reference citations in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if references detected
        """
        return bool(self.reference_pattern.search(text))
    
    def process_pending_papers(self, limit: int = 10) -> Dict[str, Any]:
        """
        Process papers that need embedding generation.
        
        Args:
            limit: Maximum number of papers to process
            
        Returns:
            Dictionary with processing statistics
        """
        try:
            # Get papers that need embedding
            papers = self.db_manager.get_papers_needing_processing('embedding', limit)
            
            if not papers:
                logger.info("No papers need embedding generation")
                return {
                    'success': True,
                    'papers_processed': 0,
                    'total_chunks': 0
                }
            
            logger.info(f"Processing {len(papers)} papers needing embeddings")
            
            stats = {
                'success': True,
                'papers_processed': 0,
                'papers_failed': 0,
                'total_chunks': 0,
                'failed_papers': []
            }
            
            for paper in papers:
                paper_id = paper['id']
                
                try:
                    # Get chunks for this paper
                    chunks = self.db_manager.get_paper_chunks(paper_id)
                    
                    if not chunks:
                        logger.warning(f"No chunks found for paper {paper_id}, skipping")
                        continue
                    
                    # Process paper
                    result = self.process_paper(paper_id, chunks)
                    
                    if result['success']:
                        stats['papers_processed'] += 1
                        stats['total_chunks'] += result['chunks_processed']
                    else:
                        stats['papers_failed'] += 1
                        stats['failed_papers'].append({
                            'paper_id': paper_id,
                            'error': result.get('error')
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing paper {paper_id}: {e}")
                    stats['papers_failed'] += 1
                    stats['failed_papers'].append({
                        'paper_id': paper_id,
                        'error': str(e)
                    })
            
            logger.info(
                f"Batch processing complete: {stats['papers_processed']} succeeded, "
                f"{stats['papers_failed']} failed"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in process_pending_papers: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def close(self):
        """Close database connection."""
        self.db_manager.close_connection()