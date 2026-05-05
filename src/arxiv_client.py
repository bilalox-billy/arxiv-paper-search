import time
import logging
from typing import List, Dict, Optional, Generator
from datetime import datetime, timedelta
import arxiv
from dataclasses import dataclass
from urllib.parse import quote

logger = logging.getLogger(__name__)


@dataclass
class ArxivPaper:
    """Structured representation of an Arxiv paper."""
    arxiv_id: str
    title: str
    abstract: str
    authors: List[str]
    categories: List[str]
    primary_category: str
    published_date: datetime
    updated_date: datetime
    pdf_url: str
    comment: Optional[str] = None
    journal_ref: Optional[str] = None
    doi: Optional[str] = None



class ArxivClient:
    """Robust ArXiv API client with rate limiting and error handling."""
    
    def __init__(self, 
                 rate_limit_seconds: float = 3.0,
                 max_results_per_query: int = 100):
        """
        Initialize ArXiv client.
        
        Args:
            rate_limit_seconds: Minimum seconds between API requests
            max_results_per_query: Maximum results to fetch per query
        """
        self.rate_limit_seconds = rate_limit_seconds
        self.max_results_per_query = max_results_per_query
        self.last_request_time = 0.0
        self.client = arxiv.Client()
        logger.info(f"ArxivClient initialized with rate limit: {rate_limit_seconds}s")
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting between API requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_seconds:
            sleep_time = self.rate_limit_seconds - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _parse_result(self, result: arxiv.Result) -> ArxivPaper:
        """
        Parse arxiv.Result into ArxivPaper dataclass.
        
        Args:
            result: arxiv.Result object from API
            
        Returns:
            ArxivPaper dataclass instance
        """
        # Extract arxiv ID from entry_id URL
        arxiv_id = result.entry_id.split('/')[-1]
        
        # Extract author names
        authors = [author.name for author in result.authors]
        
        # Get primary category
        primary_category = result.primary_category
        
        # Get all categories
        categories = result.categories
        
        return ArxivPaper(
            arxiv_id=arxiv_id,
            title=result.title.strip(),
            abstract=result.summary.strip(),
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published_date=result.published,
            updated_date=result.updated,
            pdf_url=result.pdf_url,
            comment=result.comment,
            journal_ref=result.journal_ref,
            doi=result.doi
        )

    def search_papers(self, 
                      query: str,
                      max_results: int = 100,
                      sort_by: arxiv.SortCriterion = arxiv.SortCriterion.SubmittedDate,
                      sort_order: arxiv.SortOrder = arxiv.SortOrder.Descending
                      ) -> Generator[ArxivPaper, None, None]:
        """
        Search for papers matching the query.
        
        Query examples:
        - 'cat:cs.LG' - Machine learning papers
        - 'au:Bengio' - Papers by author
        - 'ti:transformer' - Title contains word
        - 'cat:cs.LG AND (ti:attention OR ti:transformer)' - Complex query
        
        Args:
            query: ArXiv search query
            max_results: Maximum number of results to return
            sort_by: Sort criterion
            sort_order: Sort order (Ascending or Descending)
            
        Yields:
            ArxivPaper objects
        """
        logger.info(f"Searching ArXiv: query='{query}', max_results={max_results}")
        
        try:
            # Enforce rate limiting
            self._enforce_rate_limit()
            
            # Create search
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            # Fetch and yield results
            count = 0
            for result in self.client.results(search):
                try:
                    paper = self._parse_result(result)
                    count += 1
                    logger.debug(f"Fetched paper {count}/{max_results}: {paper.arxiv_id}")
                    yield paper
                except Exception as e:
                    logger.warning(f"Error parsing result: {e}")
                    continue
            
            logger.info(f"Successfully fetched {count} papers")
            
        except arxiv.ArxivError as e:
            logger.error(f"ArXiv API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            raise

    def fetch_by_ids(self, arxiv_ids: List[str]) -> Generator[ArxivPaper, None, None]:
        """
        Fetch specific papers by their Arxiv IDs.
        
        Args:
            arxiv_ids: List of ArXiv IDs (e.g., ['2301.12345', '1706.03762'])
            
        Yields:
            ArxivPaper objects
        """
        if not arxiv_ids:
            logger.warning("Empty arxiv_ids list provided")
            return
        
        logger.info(f"Fetching {len(arxiv_ids)} papers by ID")
        
        try:
            # Enforce rate limiting
            self._enforce_rate_limit()
            
            # Create search by ID list
            search = arxiv.Search(id_list=arxiv_ids)
            
            # Fetch and yield results
            count = 0
            for result in self.client.results(search):
                try:
                    paper = self._parse_result(result)
                    count += 1
                    logger.debug(f"Fetched paper {count}/{len(arxiv_ids)}: {paper.arxiv_id}")
                    yield paper
                except Exception as e:
                    logger.warning(f"Error parsing result: {e}")
                    continue
            
            logger.info(f"Successfully fetched {count}/{len(arxiv_ids)} papers")
            
        except arxiv.ArxivError as e:
            logger.error(f"ArXiv API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching by IDs: {e}")
            raise
    
    def search_recent_papers(self, 
                           categories: List[str], 
                           days_back: int = 7) -> Generator[ArxivPaper, None, None]:
        """
        Fetch papers from specified categories published in the last N days.
        
        Args:
            categories: List of ArXiv categories (e.g., ['cs.AI', 'cs.LG'])
            days_back: Number of days to look back
            
        Yields:
            ArxivPaper objects
        """
        if not categories:
            logger.warning("Empty categories list provided")
            return
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Build query for multiple categories
        category_query = " OR ".join([f"cat:{cat}" for cat in categories])
        query = f"({category_query})"
        
        logger.info(f"Searching recent papers: categories={categories}, days_back={days_back}")
        logger.debug(f"Date range: {start_date.date()} to {end_date.date()}")
        
        try:
            # Search papers
            count = 0
            for paper in self.search_papers(
                query=query,
                max_results=self.max_results_per_query,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            ):
                # Filter by date (ArXiv API doesn't have date filtering)
                if paper.published_date.replace(tzinfo=None) >= start_date:
                    count += 1
                    yield paper
                else:
                    # Since results are sorted by date (descending), we can stop
                    logger.debug(f"Reached papers older than {days_back} days, stopping")
                    break
            
            logger.info(f"Found {count} recent papers in categories {categories}")
            
        except Exception as e:
            logger.error(f"Error searching recent papers: {e}")
            raise






