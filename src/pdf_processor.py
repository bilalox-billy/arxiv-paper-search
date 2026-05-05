"""
Paper Processor Module
Main orchestrator that coordinates the entire paper processing pipeline
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from pathlib import Path

from src.arxiv_client import ArxivClient, ArxivPaper
from src.pdf_downloader import PDFDownloader
from src.pdf_extraction_info import PDFTextExtractor
from src.text_chunking import TextChunker
from src.embedding_pipeline import EmbeddingPipeline
from src.embedding import EmbeddingGenerator
from src.database import DatabaseManager

logger = logging.getLogger(__name__)


class PaperProcessor:
    """Orchestrates the complete paper processing pipeline."""
    
    def __init__(self, 
                 db_config: dict,
                 arxiv_client: Optional[ArxivClient] = None,
                 pdf_downloader: Optional[PDFDownloader] = None,
                 pdf_extractor: Optional[PDFTextExtractor] = None,
                 text_chunker: Optional[TextChunker] = None,
                 embedding_pipeline: Optional[EmbeddingPipeline] = None,
                 max_workers: int = 4):
        """
        Initialize paper processor with all components.
        
        Args:
            db_config: Database configuration
            arxiv_client: ArxivClient instance (creates default if None)
            pdf_downloader: PDFDownloader instance (creates default if None)
            pdf_extractor: PDFTextExtractor instance (creates default if None)
            text_chunker: TextChunker instance (creates default if None)
            embedding_pipeline: EmbeddingPipeline instance (creates default if None)
            max_workers: Number of parallel workers for processing
        """
        self.db_config = db_config
        self.db_manager = DatabaseManager(db_config)
        self.max_workers = max_workers
        
        # Initialize components (use provided or create defaults)
        self.arxiv_client = arxiv_client or ArxivClient()
        self.pdf_downloader = pdf_downloader or PDFDownloader()
        self.pdf_extractor = pdf_extractor or PDFTextExtractor()
        self.text_chunker = text_chunker or TextChunker()
        
        # Embedding pipeline (requires generator)
        if embedding_pipeline:
            self.embedding_pipeline = embedding_pipeline
        else:
            embedding_generator = EmbeddingGenerator()
            self.embedding_pipeline = EmbeddingPipeline(
                db_config=db_config,
                embedding_generator=embedding_generator
            )
        
        logger.info(
            f"PaperProcessor initialized with {max_workers} workers"
        )
    
    def process_papers(self, 
                      query: str, 
                      max_papers: int = 100, 
                      skip_existing: bool = True) -> Dict[str, Any]:
        """
        Process a batch of papers from ArXiv query.
        
        Args:
            query: ArXiv search query
            max_papers: Maximum number of papers to process
            skip_existing: Skip papers already in database
            
        Returns:
            Dictionary with processing statistics
        """
        stats = {
            'query': query,
            'max_papers': max_papers,
            'papers_fetched': 0,
            'papers_skipped': 0,
            'papers_downloaded': 0,
            'papers_extracted': 0,
            'papers_chunked': 0,
            'papers_embedded': 0,
            'papers_failed': 0,
            'failed_papers': [],
            'start_time': datetime.now(),
            'end_time': None
        }
        
        try:
            logger.info(f"Starting paper processing: query='{query}', max={max_papers}")
            
            # Step 1: Fetch papers from ArXiv
            logger.info("Step 1: Fetching papers from ArXiv...")
            papers = list(self.arxiv_client.search_papers(query, max_results=max_papers))
            stats['papers_fetched'] = len(papers)
            logger.info(f"Fetched {len(papers)} papers")
            
            if not papers:
                logger.warning("No papers found for query")
                stats['end_time'] = datetime.now()
                return stats
            
            # Step 2: Filter existing papers
            papers_to_process = []
            for paper in papers:
                if skip_existing and self.db_manager.paper_exists(paper.arxiv_id):
                    logger.debug(f"Skipping existing paper: {paper.arxiv_id}")
                    stats['papers_skipped'] += 1
                else:
                    papers_to_process.append(paper)
            
            logger.info(
                f"Processing {len(papers_to_process)} papers "
                f"(skipped {stats['papers_skipped']} existing)"
            )
            
            if not papers_to_process:
                logger.info("All papers already in database")
                stats['end_time'] = datetime.now()
                return stats
            
            # Step 3: Process papers (insert metadata first)
            paper_queue = []
            for paper in papers_to_process:
                # Insert paper metadata
                paper_data = {
                    'arxiv_id': paper.arxiv_id,
                    'title': paper.title,
                    'abstract': paper.abstract,
                    'authors': paper.authors,
                    'categories': paper.categories,
                    'primary_category': paper.primary_category,
                    'published_date': paper.published_date,
                    'updated_date': paper.updated_date,
                    'pdf_url': paper.pdf_url,
                    'comment': paper.comment,
                    'journal_ref': paper.journal_ref,
                    'doi': paper.doi
                }
                
                paper_id = self.db_manager.insert_paper(paper_data)
                
                if paper_id:
                    paper_queue.append({
                        'paper_id': paper_id,
                        'paper': paper
                    })
            
            # Step 4: Process papers in parallel
            logger.info(f"Processing {len(paper_queue)} papers with {self.max_workers} workers...")
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self._process_single_paper, item): item 
                    for item in paper_queue
                }
                
                for future in as_completed(futures):
                    item = futures[future]
                    try:
                        result = future.result()
                        
                        if result['success']:
                            if result.get('downloaded'):
                                stats['papers_downloaded'] += 1
                            if result.get('extracted'):
                                stats['papers_extracted'] += 1
                            if result.get('chunked'):
                                stats['papers_chunked'] += 1
                            if result.get('embedded'):
                                stats['papers_embedded'] += 1
                        else:
                            stats['papers_failed'] += 1
                            stats['failed_papers'].append({
                                'arxiv_id': item['paper'].arxiv_id,
                                'error': result.get('error', 'Unknown error')
                            })
                            
                    except Exception as e:
                        logger.error(f"Future failed for {item['paper'].arxiv_id}: {e}")
                        stats['papers_failed'] += 1
                        stats['failed_papers'].append({
                            'arxiv_id': item['paper'].arxiv_id,
                            'error': str(e)
                        })
            
            stats['end_time'] = datetime.now()
            duration = (stats['end_time'] - stats['start_time']).total_seconds()
            
            logger.info(
                f"Processing complete in {duration:.1f}s: "
                f"{stats['papers_embedded']} embedded, "
                f"{stats['papers_failed']} failed"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in process_papers: {e}")
            stats['end_time'] = datetime.now()
            stats['error'] = str(e)
            return stats
    
    def _process_single_paper(self, item: Dict) -> Dict[str, Any]:
        """
        Process a single paper through the complete pipeline.
        
        Args:
            item: Dictionary with paper_id and paper (ArxivPaper)
            
        Returns:
            Dictionary with processing result
        """
        paper_id = item['paper_id']
        paper = item['paper']
        
        result = {
            'success': False,
            'paper_id': paper_id,
            'arxiv_id': paper.arxiv_id,
            'downloaded': False,
            'extracted': False,
            'chunked': False,
            'embedded': False
        }
        
        try:
            logger.info(f"Processing paper: {paper.arxiv_id}")
            
            # Step 1: Download PDF
            logger.debug(f"Downloading PDF for {paper.arxiv_id}...")
            success, pdf_path, error = self.pdf_downloader.download_pdf(
                pdf_url=paper.pdf_url,
                arxiv_id=paper.arxiv_id,
                published_date=paper.published_date
            )
            
            if not success or not pdf_path:
                result['error'] = f"Download failed: {error}"
                self.db_manager.update_paper_status(paper_id, {
                    'processing_error': result['error']
                })
                return result
            
            result['downloaded'] = True
            self.db_manager.update_paper_status(paper_id, {'pdf_downloaded': True})
            
            # Step 2: Extract text from PDF
            logger.debug(f"Extracting text from {paper.arxiv_id}...")
            try:
                extraction_result = self.pdf_extractor.extract_paper_text(str(pdf_path))
                
                if not extraction_result or not extraction_result.get('full_text'):
                    result['error'] = "Text extraction returned empty"
                    self.db_manager.update_paper_status(paper_id, {
                        'processing_error': result['error']
                    })
                    return result
                
                result['extracted'] = True
                self.db_manager.update_paper_status(paper_id, {'pdf_processed': True})
                
            except Exception as e:
                result['error'] = f"Extraction failed: {str(e)}"
                logger.error(f"Extraction error for {paper.arxiv_id}: {e}")
                self.db_manager.update_paper_status(paper_id, {
                    'processing_error': result['error']
                })
                return result
            
            # Step 3: Chunk text
            logger.debug(f"Chunking text for {paper.arxiv_id}...")
            try:
                chunks = self.text_chunker.chunk_paper(
                    text=extraction_result['full_text'],
                    sections=extraction_result.get('sections', []),
                    preserve_sections=True
                )
                
                if not chunks:
                    result['error'] = "Text chunking produced no chunks"
                    self.db_manager.update_paper_status(paper_id, {
                        'processing_error': result['error']
                    })
                    return result
                
                result['chunked'] = True
                result['chunk_count'] = len(chunks)
                
            except Exception as e:
                result['error'] = f"Chunking failed: {str(e)}"
                logger.error(f"Chunking error for {paper.arxiv_id}: {e}")
                self.db_manager.update_paper_status(paper_id, {
                    'processing_error': result['error']
                })
                return result
            
            # Step 4: Generate embeddings and store
            logger.debug(f"Generating embeddings for {paper.arxiv_id} ({len(chunks)} chunks)...")
            try:
                embedding_result = self.embedding_pipeline.process_paper(
                    paper_id=paper_id,
                    chunks=chunks
                )
                
                if not embedding_result.get('success'):
                    result['error'] = f"Embedding failed: {embedding_result.get('error')}"
                    self.db_manager.update_paper_status(paper_id, {
                        'processing_error': result['error']
                    })
                    return result
                
                result['embedded'] = True
                result['success'] = True
                
                logger.info(
                    f"Successfully processed {paper.arxiv_id}: "
                    f"{result['chunk_count']} chunks embedded"
                )
                
            except Exception as e:
                result['error'] = f"Embedding failed: {str(e)}"
                logger.error(f"Embedding error for {paper.arxiv_id}: {e}")
                self.db_manager.update_paper_status(paper_id, {
                    'processing_error': result['error']
                })
                return result
            
            return result
            
        except Exception as e:
            result['error'] = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error processing {paper.arxiv_id}: {e}")
            self.db_manager.update_paper_status(paper_id, {
                'processing_error': result['error']
            })
            return result
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get statistics about paper processing.
        
        Returns:
            Dictionary with processing statistics
        """
        return self.db_manager.get_database_stats()
    
    def close(self):
        """Close all connections."""
        self.db_manager.close_connection()
        self.embedding_pipeline.close()
