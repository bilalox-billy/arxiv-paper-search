import numpy as np
from typing import List, Dict, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .embedding import EmbeddingGenerator

logger = logging.getLogger(__name__)

class SearchMode(Enum):
    VECTOR = "vector"
    HYBRID = "hybrid"
    KEYWORD = "keyword"

@dataclass
class SearchResult:
    """Structured search result."""
    paper_id: int
    arxiv_id: str
    title: str
    abstract: str
    authors: List[str]
    score: float
    matched_chunks: List[Dict]
    published_date: str
    categories: List[str]

class PaperSearchEngine:
    """Advanced search engine for academic papers."""
    
    def __init__(self,
                 db_config: dict,
                 embedding_generator: EmbeddingGenerator):
        """
        Initialize search engine.
        
        Args:
            db_config: Database connection parameters
            embedding_generator: EmbeddingGenerator instance for query embedding
        """
        self.db_config = db_config
        self.embedding_generator = embedding_generator
        self._conn = None
        logger.info("PaperSearchEngine initialized")
    
    def get_connection(self):
        """Get or create database connection."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(**self.db_config)
            self._conn.set_client_encoding('UTF8')
        return self._conn
    
    def search(self,
              query: str,
              mode: SearchMode = SearchMode.HYBRID,
              limit: int = 10,
              filters: Optional[Dict] = None) -> List[SearchResult]:
        """
        Main search interface supporting multiple modes.
        
        Args:
            query: Search query string
            mode: Search mode (VECTOR, HYBRID, or KEYWORD)
            limit: Maximum number of results
            filters: Optional filters dictionary
        
        Filters can include:
        - authors: List[str] - Author names to filter
        - categories: List[str] - ArXiv categories
        - date_from: str - Minimum publication date
        - date_to: str - Maximum publication date
        - min_score: float - Minimum similarity score
        
        Returns:
            List of SearchResult objects
        """
        logger.info(f"Searching: query='{query[:50]}...', mode={mode.value}, limit={limit}")
        
        if mode == SearchMode.VECTOR:
            results = self._vector_search(query, limit, filters)
        elif mode == SearchMode.KEYWORD:
            results = self._keyword_search(query, limit, filters)
        else:  # HYBRID
            results = self._hybrid_search(query, limit, filters)
        
        logger.info(f"Found {len(results)} results")
        return results
    
    def _vector_search(self,
                      query: str,
                      limit: int,
                      filters: Optional[Dict]) -> List[SearchResult]:
        """
        Pure vector similarity search using embeddings.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            filters: Optional filters
            
        Returns:
            List of SearchResult objects
        """
        # Generate query embedding
        query_embedding = self.embedding_generator.generate_query_embedding(query)
        embedding_str = '[' + ','.join(map(str, query_embedding.tolist())) + ']'
        
        # Build filter clause
        filter_clause, filter_params = self._build_filter_clause(filters)
        
        # Vector similarity search with chunk-level matching
        sql = """
            WITH ranked_chunks AS (
                SELECT 
                    pc.paper_id,
                    pc.chunk_text,
                    pc.section_name,
                    pc.chunk_index,
                    pc.embedding <=> %s::vector AS distance,
                    1.0 - (pc.embedding <=> %s::vector) AS similarity
                FROM paper_chunks pc
                JOIN papers p ON pc.paper_id = p.id
                WHERE 1=1
        """
        
        params = [embedding_str, embedding_str] + filter_params
        sql += filter_clause
        
        # Group by paper and aggregate top chunks
        sql += """
            ),
            paper_scores AS (
                SELECT 
                    paper_id,
                    AVG(similarity) as avg_similarity,
                    MAX(similarity) as max_similarity,
                    json_agg(
                        json_build_object(
                            'text', chunk_text,
                            'section', section_name,
                            'index', chunk_index,
                            'score', similarity
                        ) ORDER BY similarity DESC
                    ) FILTER (WHERE similarity > 0.3) as chunks
                FROM ranked_chunks
                GROUP BY paper_id
            )
            SELECT 
                p.id,
                p.arxiv_id,
                p.title,
                p.abstract,
                COALESCE(p.authors, ARRAY[]::text[]) as authors,
                COALESCE(p.categories, ARRAY[]::text[]) as categories,
                p.published_date,
                ps.avg_similarity * 0.4 + ps.max_similarity * 0.6 as score,
                COALESCE(ps.chunks, '[]'::json) as matched_chunks
            FROM papers p
            JOIN paper_scores ps ON p.id = ps.paper_id
            ORDER BY score DESC
            LIMIT %s
        """
        
        params.append(limit)
        
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        
        return self._rows_to_results(rows)
    
    def _hybrid_search(self,
                      query: str,
                      limit: int,
                      filters: Optional[Dict]) -> List[SearchResult]:
        """
        Hybrid search combining vector similarity and keyword matching.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            filters: Optional filters
            
        Returns:
            List of SearchResult objects
        """
        # Get results from both methods (fetch more to have candidates for merging)
        vector_results = self._vector_search(query, limit * 2, filters)
        keyword_results = self._keyword_search(query, limit * 2, filters)
        
        # Combine results with weighted scores
        # Vector search: 70% weight, Keyword search: 30% weight
        combined = self._combine_results(
            vector_results,
            keyword_results,
            vector_weight=0.7,
            keyword_weight=0.3
        )
        
        return combined[:limit]
    
    def _keyword_search(self,
                       query: str,
                       limit: int,
                       filters: Optional[Dict]) -> List[SearchResult]:
        """
        Traditional keyword search using PostgreSQL full-text search.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            filters: Optional filters
            
        Returns:
            List of SearchResult objects
        """
        filter_clause, filter_params = self._build_filter_clause(filters)
        
        # Full-text search on paper title and abstract
        sql = """
            WITH text_search AS (
                SELECT 
                    p.id,
                    p.arxiv_id,
                    p.title,
                    p.abstract,
                    p.published_date,
                    ts_rank(
                        to_tsvector('english', p.title || ' ' || p.abstract),
                        plainto_tsquery('english', %s)
                    ) as text_score
                FROM papers p
                WHERE 
                    to_tsvector('english', p.title || ' ' || p.abstract) @@ plainto_tsquery('english', %s)
        """
        
        params = [query, query] + filter_params
        sql += filter_clause
        
        sql += """
            )
            SELECT 
                p.id,
                p.arxiv_id,
                p.title,
                p.abstract,
                COALESCE(p.authors, ARRAY[]::text[]) as authors,
                COALESCE(p.categories, ARRAY[]::text[]) as categories,
                p.published_date,
                ts.text_score as score,
                '[]'::json as matched_chunks
            FROM text_search ts
            JOIN papers p ON ts.id = p.id
            ORDER BY score DESC
            LIMIT %s
        """
        
        params.append(limit)
        
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        
        return self._rows_to_results(rows)
    
    def _build_filter_clause(self, 
                            filters: Optional[Dict]) -> Tuple[str, List]:
        """
        Build SQL filter clause from filter dictionary.
        
        Args:
            filters: Dictionary of filter criteria
            
        Returns:
            Tuple of (SQL clause string, parameter list)
        """
        if not filters:
            return ("", [])
        
        clauses = []
        params = []
        
        # Author filter (using array overlap operator)
        if 'authors' in filters and filters['authors']:
            author_list = filters['authors']
            clauses.append(" AND p.authors && %s")
            params.append(author_list)
        
        # Category filter (using array overlap operator)
        if 'categories' in filters and filters['categories']:
            category_list = filters['categories']
            clauses.append(" AND p.categories && %s")
            params.append(category_list)
        
        # Date range filters
        if 'date_from' in filters and filters['date_from']:
            clauses.append(" AND p.published_date >= %s")
            params.append(filters['date_from'])
        
        if 'date_to' in filters and filters['date_to']:
            clauses.append(" AND p.published_date <= %s")
            params.append(filters['date_to'])
        
        return (' '.join(clauses), params)
    
    def _combine_results(self,
                        vector_results: List[SearchResult],
                        keyword_results: List[SearchResult],
                        vector_weight: float,
                        keyword_weight: float) -> List[SearchResult]:
        """
        Combine and re-rank results from different search methods.
        
        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            vector_weight: Weight for vector search scores
            keyword_weight: Weight for keyword search scores
            
        Returns:
            Combined and re-ranked list of SearchResult objects
        """
        # Normalize scores for each result set
        def normalize_scores(results: List[SearchResult]) -> Dict[str, float]:
            if not results:
                return {}
            
            scores = {r.arxiv_id: r.score for r in results}
            max_score = max(scores.values()) if scores else 1.0
            min_score = min(scores.values()) if scores else 0.0
            
            # Min-max normalization
            if max_score > min_score:
                return {
                    arxiv_id: (score - min_score) / (max_score - min_score)
                    for arxiv_id, score in scores.items()
                }
            else:
                return dict.fromkeys(scores.keys(), 1.0)
        
        vector_scores = normalize_scores(vector_results)
        keyword_scores = normalize_scores(keyword_results)
        
        # Build paper ID to result mapping
        result_map: Dict[str, SearchResult] = {}
        for result in vector_results + keyword_results:
            if result.arxiv_id not in result_map:
                result_map[result.arxiv_id] = result
        
        # Calculate combined scores
        combined_scores = []
        for arxiv_id, result in result_map.items():
            vec_score = vector_scores.get(arxiv_id, 0.0)
            kw_score = keyword_scores.get(arxiv_id, 0.0)
            
            # Weighted combination
            combined_score = (vector_weight * vec_score + keyword_weight * kw_score)
            
            # Update result with combined score
            combined_result = SearchResult(
                paper_id=result.paper_id,
                arxiv_id=result.arxiv_id,
                title=result.title,
                abstract=result.abstract,
                authors=result.authors,
                score=combined_score,
                matched_chunks=result.matched_chunks,
                published_date=result.published_date,
                categories=result.categories
            )
            combined_scores.append((combined_score, combined_result))
        
        # Sort by combined score
        combined_scores.sort(key=lambda x: x[0], reverse=True)
        
        return [result for _, result in combined_scores]
    
    def find_similar_papers(self,
                           paper_id: int,
                           limit: int = 10) -> List[SearchResult]:
        """
        Find papers similar to a given paper using its embeddings.
        
        Args:
            paper_id: Database ID of the paper
            limit: Maximum number of similar papers to return
            
        Returns:
            List of SearchResult objects
        """
        logger.info(f"Finding similar papers to paper_id={paper_id}, limit={limit}")
        
        # Use average of paper's chunk embeddings as paper representation
        sql = """
            WITH paper_embedding AS (
                SELECT AVG(embedding) as avg_embedding
                FROM paper_chunks
                WHERE paper_id = %s
            ),
            similar_chunks AS (
                SELECT 
                    pc.paper_id,
                    AVG(pc.embedding <=> (SELECT avg_embedding FROM paper_embedding)) AS avg_distance,
                    MIN(pc.embedding <=> (SELECT avg_embedding FROM paper_embedding)) AS min_distance
                FROM paper_chunks pc
                WHERE pc.paper_id != %s
                GROUP BY pc.paper_id
            )
            SELECT 
                p.id,
                p.arxiv_id,
                p.title,
                p.abstract,
                COALESCE(p.authors, ARRAY[]::text[]) as authors,
                COALESCE(p.categories, ARRAY[]::text[]) as categories,
                p.published_date,
                1.0 - (sc.avg_distance * 0.6 + sc.min_distance * 0.4) as score,
                '[]'::json as matched_chunks
            FROM papers p
            JOIN similar_chunks sc ON p.id = sc.paper_id
            WHERE p.id != %s
            ORDER BY score DESC
            LIMIT %s
        """
        
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, (paper_id, paper_id, paper_id, limit))
            rows = cursor.fetchall()
        
        logger.info(f"Found {len(rows)} similar papers")
        return self._rows_to_results(rows)
    
    def _rows_to_results(self, rows: List[Dict]) -> List[SearchResult]:
        """
        Convert database rows to SearchResult objects.
        
        Args:
            rows: List of database result dictionaries
            
        Returns:
            List of SearchResult objects
        """
        results = []
        for row in rows:
            # Parse matched chunks if present
            matched_chunks = row.get('matched_chunks', [])
            if isinstance(matched_chunks, str):
                import json
                try:
                    matched_chunks = json.loads(matched_chunks)
                except (json.JSONDecodeError, TypeError):
                    matched_chunks = []
            
            result = SearchResult(
                paper_id=row['id'],
                arxiv_id=row['arxiv_id'],
                title=row['title'],
                abstract=row['abstract'] or '',
                authors=row.get('authors', []),
                score=float(row['score']),
                matched_chunks=matched_chunks if matched_chunks else [],
                published_date=str(row['published_date']) if row.get('published_date') else '',
                categories=row.get('categories', [])
            )
            results.append(result)
        
        return results
    
    def close(self):
        """Close database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()