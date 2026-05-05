import os
import hashlib
import requests
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PDFDownloader:
    """Download and save PDF files from ArXiv with retry logic and validation."""

    def __init__(self, 
                 storage_path: str = "./data/pdfs", 
                 max_retries: int = 3,
                 timeout: int = 30):
        """
        Initialize PDF downloader.
        
        Args:
            storage_path: Base directory for storing PDFs
            max_retries: Maximum number of download retry attempts
            timeout: Request timeout in seconds
        """
        self.storage_path = Path(storage_path)
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Create storage directory if it doesn't exist
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"PDFDownloader initialized: storage={storage_path}, max_retries={max_retries}")

    def _get_pdf_path(self, arxiv_id: str, published_date: datetime) -> Path:
        """
        Generate a stable path for storing PDF files.
        Organizes by year/month for better file management.
        
        Args:
            arxiv_id: ArXiv paper ID
            published_date: Publication date of the paper
            
        Returns:
            Path object for the PDF file
        """
        # Extract year and month from published date
        year = published_date.strftime("%Y")
        month = published_date.strftime("%m")
        
        # Create directory structure: storage/YYYY/MM/
        year_dir = self.storage_path / year
        month_dir = year_dir / month
        
        # Create directories if they don't exist
        month_dir.mkdir(parents=True, exist_ok=True)
        
        # Sanitize arxiv_id for filename (replace / with _)
        safe_id = arxiv_id.replace('/', '_').replace('\\', '_')
        
        # Create filename
        filename = f"{safe_id}.pdf"
        
        return month_dir / filename

    def download_pdf(self, 
                    pdf_url: str, 
                    arxiv_id: str,
                    published_date: datetime,
                    force: bool = False) -> Tuple[bool, Optional[Path], Optional[str]]:
        """
        Download PDF with retry logic.
        
        Args:
            pdf_url: URL to download PDF from
            arxiv_id: ArXiv paper ID
            published_date: Publication date for file organization
            force: If True, re-download even if file exists
            
        Returns:
            Tuple of (success, pdf_path, error_message)
        """
        pdf_path = self._get_pdf_path(arxiv_id, published_date)
        
        # Check if file already exists
        if pdf_path.exists() and not force:
            # Validate existing file
            if self._validate_pdf(pdf_path):
                logger.debug(f"PDF already exists and is valid: {arxiv_id}")
                return (True, pdf_path, None)
            else:
                logger.warning(f"Existing PDF is invalid, re-downloading: {arxiv_id}")
        
        # Retry loop
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Downloading PDF (attempt {attempt}/{self.max_retries}): {arxiv_id}")
                
                # Download with timeout
                response = requests.get(
                    pdf_url, 
                    timeout=self.timeout,
                    stream=True,
                    headers={'User-Agent': 'Mozilla/5.0 (ArXiv Paper Search Bot)'}
                )
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get('content-type', '')
                if 'application/pdf' not in content_type.lower():
                    error_msg = f"Invalid content type: {content_type}"
                    logger.warning(error_msg)
                    last_error = error_msg
                    continue
                
                # Write to temporary file first
                temp_path = pdf_path.with_suffix('.tmp')
                
                # Download with progress tracking
                total_size = 0
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            total_size += len(chunk)
                
                logger.debug(f"Downloaded {total_size} bytes")
                
                # Validate downloaded file
                if not self._validate_pdf(temp_path):
                    error_msg = "Downloaded file is not a valid PDF"
                    logger.warning(error_msg)
                    temp_path.unlink()  # Delete invalid file
                    last_error = error_msg
                    continue
                
                # Move to final location
                temp_path.rename(pdf_path)
                
                logger.info(f"Successfully downloaded PDF: {arxiv_id} ({total_size} bytes)")
                return (True, pdf_path, None)
                
            except requests.exceptions.Timeout as e:
                error_msg = f"Timeout after {self.timeout}s"
                logger.warning(f"Attempt {attempt} failed: {error_msg}")
                last_error = error_msg
                
            except requests.exceptions.HTTPError as e:
                error_msg = f"HTTP error: {e.response.status_code}"
                logger.warning(f"Attempt {attempt} failed: {error_msg}")
                last_error = error_msg
                
                # Don't retry on 404
                if e.response.status_code == 404:
                    break
                
            except requests.exceptions.RequestException as e:
                error_msg = f"Request error: {str(e)}"
                logger.warning(f"Attempt {attempt} failed: {error_msg}")
                last_error = error_msg
                
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                logger.error(f"Attempt {attempt} failed: {error_msg}")
                last_error = error_msg
            
            # Wait before retry (exponential backoff)
            if attempt < self.max_retries:
                wait_time = 2 ** attempt  # 2, 4, 8 seconds
                logger.debug(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
        
        # All retries failed
        final_error = f"Failed after {self.max_retries} attempts: {last_error}"
        logger.error(f"Download failed for {arxiv_id}: {final_error}")
        return (False, None, final_error)

    def _validate_pdf(self, pdf_path: Path) -> bool:
        """
        Check if file is a valid PDF.
        Validates PDF magic bytes and basic structure.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            True if valid PDF, False otherwise
        """
        if not pdf_path.exists():
            return False
        
        if pdf_path.stat().st_size == 0:
            logger.warning(f"PDF file is empty: {pdf_path}")
            return False
        
        try:
            # Check PDF magic bytes (%PDF-)
            with open(pdf_path, 'rb') as f:
                header = f.read(5)
                if header != b'%PDF-':
                    logger.warning(f"Invalid PDF header: {pdf_path}")
                    return False
                
                # Check for EOF marker (optional but good practice)
                # Read last 1KB to check for %%EOF
                f.seek(-min(1024, pdf_path.stat().st_size), 2)
                tail = f.read()
                if b'%%EOF' not in tail:
                    logger.debug(f"PDF missing EOF marker (might still be valid): {pdf_path}")
                    # Don't fail on missing EOF, some PDFs don't have it
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating PDF {pdf_path}: {e}")
            return False
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored PDFs.
        
        Returns:
            Dictionary with storage statistics
        """
        stats = {
            'total_pdfs': 0,
            'total_size_bytes': 0,
            'total_size_mb': 0.0,
            'by_year': {},
            'oldest_pdf': None,
            'newest_pdf': None
        }
        
        try:
            # Walk through all PDF files
            pdf_files = list(self.storage_path.rglob('*.pdf'))
            stats['total_pdfs'] = len(pdf_files)
            
            if pdf_files:
                # Calculate total size
                for pdf_file in pdf_files:
                    stats['total_size_bytes'] += pdf_file.stat().st_size
                
                stats['total_size_mb'] = stats['total_size_bytes'] / (1024 * 1024)
                
                # Get modification times
                mod_times = [(f, f.stat().st_mtime) for f in pdf_files]
                mod_times.sort(key=lambda x: x[1])
                
                stats['oldest_pdf'] = datetime.fromtimestamp(mod_times[0][1]).isoformat()
                stats['newest_pdf'] = datetime.fromtimestamp(mod_times[-1][1]).isoformat()
                
                # Count by year
                for pdf_file in pdf_files:
                    # Extract year from path structure (storage/YYYY/MM/file.pdf)
                    try:
                        year = pdf_file.parent.parent.name
                        if year.isdigit():
                            stats['by_year'][year] = stats['by_year'].get(year, 0) + 1
                    except:
                        pass
            
            logger.debug(f"Storage stats: {stats['total_pdfs']} PDFs, {stats['total_size_mb']:.2f} MB")
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
        
        return stats
    
    def cleanup_old_pdfs(self, days_to_keep: int = 90) -> int:
        """
        Remove PDFs older than specified days.
        
        Args:
            days_to_keep: Number of days to keep PDFs
            
        Returns:
            Number of PDFs deleted
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0
        
        try:
            logger.info(f"Cleaning up PDFs older than {days_to_keep} days (before {cutoff_date.date()})")
            
            # Walk through all PDF files
            for pdf_file in self.storage_path.rglob('*.pdf'):
                try:
                    # Get file modification time
                    mod_time = datetime.fromtimestamp(pdf_file.stat().st_mtime)
                    
                    if mod_time < cutoff_date:
                        logger.debug(f"Deleting old PDF: {pdf_file.name}")
                        pdf_file.unlink()
                        deleted_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error deleting {pdf_file}: {e}")
            
            # Clean up empty directories
            for year_dir in self.storage_path.iterdir():
                if year_dir.is_dir():
                    for month_dir in year_dir.iterdir():
                        if month_dir.is_dir() and not any(month_dir.iterdir()):
                            month_dir.rmdir()
                            logger.debug(f"Removed empty directory: {month_dir}")
                    
                    if not any(year_dir.iterdir()):
                        year_dir.rmdir()
                        logger.debug(f"Removed empty directory: {year_dir}")
            
            logger.info(f"Cleanup complete: deleted {deleted_count} PDFs")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        return deleted_count
    
    def pdf_exists(self, arxiv_id: str, published_date: datetime) -> bool:
        """
        Check if PDF already exists for a paper.
        
        Args:
            arxiv_id: ArXiv paper ID
            published_date: Publication date
            
        Returns:
            True if PDF exists and is valid
        """
        pdf_path = self._get_pdf_path(arxiv_id, published_date)
        return pdf_path.exists() and self._validate_pdf(pdf_path)