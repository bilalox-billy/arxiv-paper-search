import fitz  # PyMuPDF
import re
from typing import List, Dict, Optional, Tuple, Any
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ExtractedPage:
    """Information about the extraction of text from a PDF file."""
    page_num: int
    text: str
    blocks: List[Dict] = field(default_factory=list)
    has_columns: bool = False
    has_math: bool = False
    has_tables: bool = False
    confidence: float = 0.0


class PDFTextExtractor:
    """Advanced PDF text extraction for academic papers."""
    
    def __init__(self):
        """Initialize PDF text extractor with patterns for detection."""
        # Patterns for section detection
        self.section_pattern = re.compile(
            r'^(?:\d+\.?|\d+\.\d+\.?)\s+([A-Z][^\n]+)$|^([A-Z][A-Z\s]{3,}[A-Z])$',
            re.MULTILINE
        )
        
        # Pattern for mathematical content
        self.math_pattern = re.compile(
            r'[\∫∑∏√∂∇≈≠≤≥±×÷∈∉⊂⊃∪∩]|'
            r'\$[^\$]+\$|'
            r'\\[a-zA-Z]+\{|'
            r'\b[a-z]\s*[=<>]\s*[0-9]'
        )
        
        # Pattern for noise (headers/footers/page numbers)
        self.noise_pattern = re.compile(
            r'^\s*\d+\s*$|'  # Just a page number
            r'^\s*Page\s+\d+\s*$|'  # "Page N"
            r'^\s*\d+\s+of\s+\d+\s*$|'  # "N of M"
            r'^\s*©\s*\d{4}|'  # Copyright
            r'^\s*arXiv:\d+\.\d+',  # arXiv ID
            re.IGNORECASE
        )
        
        # Pattern for table detection
        self.table_pattern = re.compile(
            r'Table\s+\d+[:\.]|'
            r'^\s*\|[^\|]+\|[^\|]+\||'  # Markdown-style table
            r'(?:[^\s]+\s+){3,}[^\s]+\s*\n(?:[^\s]+\s+){3,}',  # Multi-column data
            re.MULTILINE
        )
        
        logger.info("PDFTextExtractor initialized")

    def extract_paper_text(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract complete text from PDF with structure preservation.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary containing:
                - full_text: Complete extracted text
                - pages: List of ExtractedPage objects
                - sections: Identified sections
                - metadata: Extraction metadata
                - confidence: Overall confidence score
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF not found: {pdf_path}")
            
            logger.info(f"Extracting text from: {pdf_path.name}")
            
            # Open PDF
            doc = fitz.open(pdf_path)
            
            # Extract pages
            pages = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                extracted_page = self._extract_page(page, page_num)
                pages.append(extracted_page)
            
            doc.close()
            
            # Combine all text
            full_text = "\n\n".join(page.text for page in pages)
            
            # Identify sections
            sections = self._identify_sections(full_text)
            
            # Calculate overall confidence
            confidence = self._calculate_confidence(pages)
            
            # Clean text
            cleaned_text = self._clean_extracted_text(full_text)
            
            result = {
                'full_text': cleaned_text,
                'raw_text': full_text,
                'pages': pages,
                'sections': sections,
                'total_pages': len(pages),
                'has_multi_column': any(p.has_columns for p in pages),
                'has_math': any(p.has_math for p in pages),
                'has_tables': any(p.has_tables for p in pages),
                'confidence': confidence,
                'metadata': {
                    'file_name': pdf_path.name,
                    'total_characters': len(cleaned_text),
                    'avg_page_confidence': confidence
                }
            }
            
            logger.info(
                f"Extraction complete: {len(pages)} pages, "
                f"{len(sections)} sections, confidence={confidence:.2f}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise

    def _extract_page(self, page, page_num: int) -> ExtractedPage:
        """
        Extract text from a single page with layout analysis.
        
        Args:
            page: PyMuPDF page object
            page_num: Page number (0-indexed)
            
        Returns:
            ExtractedPage object
        """
        try:
            # Get text blocks with positions
            blocks_dict = page.get_text("dict")
            blocks = blocks_dict.get("blocks", [])
            
            # Filter text blocks only
            text_blocks = [b for b in blocks if b.get("type") == 0]
            
            # Detect layout features
            has_columns = self._detect_columns(text_blocks)
            
            # Extract text based on layout
            if has_columns:
                ordered_blocks = self._extract_multicolumn(text_blocks)
            else:
                ordered_blocks = self._extract_singlecolumn(text_blocks)
            
            # Combine blocks into text
            text = self._combine_blocks(ordered_blocks)
            
            # Detect content features
            has_math = bool(self.math_pattern.search(text))
            has_tables = self._detect_tables(text_blocks)
            
            # Calculate confidence
            confidence = self._calculate_page_confidence(text, has_columns, page_num)
            
            return ExtractedPage(
                page_num=page_num,
                text=text,
                blocks=text_blocks,
                has_columns=has_columns,
                has_math=has_math,
                has_tables=has_tables,
                confidence=confidence
            )
            
        except Exception as e:
            logger.warning(f"Error extracting page {page_num}: {e}")
            return ExtractedPage(
                page_num=page_num,
                text="",
                blocks=[],
                confidence=0.0
            )
    
    def _detect_columns(self, blocks: List[Dict]) -> bool:
        """
        Detect if page has multi-column layout.
        Uses x-position clustering to identify columns.
        
        Args:
            blocks: List of text blocks with position info
            
        Returns:
            True if multi-column layout detected
        """
        if len(blocks) < 5:  # Too few blocks to determine
            return False
        
        try:
            # Get x-positions of blocks (left edge)
            x_positions = [block["bbox"][0] for block in blocks]
            
            # Simple clustering: check if there are distinct groups
            x_positions_sorted = sorted(set(x_positions))
            
            if len(x_positions_sorted) < 2:
                return False
            
            # Calculate gaps between x-positions
            gaps = []
            for i in range(len(x_positions_sorted) - 1):
                gap = x_positions_sorted[i + 1] - x_positions_sorted[i]
                gaps.append(gap)
            
            if not gaps:
                return False
            
            # If there's a significant gap (>100 points), likely multi-column
            max_gap = max(gaps)
            median_gap = sorted(gaps)[len(gaps) // 2]
            
            # Multi-column if max gap is much larger than median
            is_multicolumn = max_gap > 100 and max_gap > median_gap * 3
            
            return is_multicolumn
            
        except Exception as e:
            logger.debug(f"Error detecting columns: {e}")
            return False
    
    def _extract_multicolumn(self, blocks: List[Dict]) -> List[Dict]:
        """
        Extract text from multi-column layout.
        Orders blocks by column then by position within column.
        
        Args:
            blocks: List of text blocks
            
        Returns:
            Ordered list of blocks
        """
        if not blocks:
            return []
        
        try:
            # Group blocks by columns
            columns = self._group_by_columns(blocks)
            
            # Sort blocks within each column by y-position (top to bottom)
            for column in columns:
                column.sort(key=lambda b: b["bbox"][1])  # Sort by y0
            
            # Flatten columns into single list (left to right, top to bottom)
            ordered_blocks = []
            for column in columns:
                ordered_blocks.extend(column)
            
            return ordered_blocks
            
        except Exception as e:
            logger.warning(f"Error extracting multi-column: {e}")
            return blocks  # Fallback to original order
    
    def _extract_singlecolumn(self, blocks: List[Dict]) -> List[Dict]:
        """
        Extract text from single-column layout.
        Simply sorts blocks by vertical position.
        
        Args:
            blocks: List of text blocks
            
        Returns:
            Sorted list of blocks
        """
        if not blocks:
            return []
        
        # Sort by y-position (top to bottom)
        return sorted(blocks, key=lambda b: b["bbox"][1])
    
    def _extract_block_text(self, block: Dict) -> str:
        """
        Extract text from a single block.
        Handles lines within block.
        
        Args:
            block: Text block dictionary
            
        Returns:
            Extracted text string
        """
        try:
            # Try to get lines from block
            lines = block.get("lines", [])
            if lines:
                text_parts = []
                for line in lines:
                    spans = line.get("spans", [])
                    line_text = " ".join(span.get("text", "") for span in spans)
                    text_parts.append(line_text)
                return " ".join(text_parts)
            else:
                # Fallback to direct text
                return block.get("text", "")
        except Exception as e:
            logger.debug(f"Error extracting block text: {e}")
            return block.get("text", "")
    
    def _group_by_columns(self, blocks: List[Dict]) -> List[List[Dict]]:
        """
        Group blocks into columns based on x-position.
        
        Args:
            blocks: List of text blocks
            
        Returns:
            List of columns, each containing list of blocks
        """
        if not blocks:
            return []
        
        # Get x-positions (left edge of blocks)
        x_positions = [(block["bbox"][0], block) for block in blocks]
        x_positions.sort(key=lambda x: x[0])
        
        # Simple clustering: find natural breaks in x-positions
        columns = []
        current_column = []
        last_x = None
        
        for x, block in x_positions:
            if last_x is None or abs(x - last_x) < 100:
                # Same column
                current_column.append(block)
            else:
                # New column
                if current_column:
                    columns.append(current_column)
                current_column = [block]
            last_x = x
        
        if current_column:
            columns.append(current_column)
        
        return columns
    
    def _combine_blocks(self, blocks: List[Dict]) -> str:
        """
        Combine text blocks into continuous text.
        Filters noise and adds appropriate spacing.
        
        Args:
            blocks: Ordered list of text blocks
            
        Returns:
            Combined text string
        """
        text_parts = []
        
        for block in blocks:
            block_text = self._extract_block_text(block)
            
            # Skip noise
            if self._is_noise(block_text):
                continue
            
            text_parts.append(block_text.strip())
        
        # Join with spaces, preserving paragraph breaks
        return "\n".join(text_parts)
    
    def _is_noise(self, text: str) -> bool:
        """
        Detect if text is likely noise (header/footer/page number).
        
        Args:
            text: Text to check
            
        Returns:
            True if text is noise
        """
        if not text or len(text.strip()) == 0:
            return True
        
        # Check against noise patterns
        if self.noise_pattern.search(text):
            return True
        
        # Very short text (< 3 chars) is likely noise
        if len(text.strip()) < 3:
            return True
        
        return False
    
    def _classify_block(self, text: str) -> str:
        """
        Classify block type (heading, body, caption, etc.).
        
        Args:
            text: Block text
            
        Returns:
            Block type string
        """
        text_clean = text.strip()
        
        # Check for figure/table captions
        if text_clean.lower().startswith(('figure', 'fig.', 'table')):
            return 'caption'
        
        # Check for section headings (all caps or numbered)
        if self.section_pattern.match(text_clean):
            return 'heading'
        
        # Check for mathematical content
        if self.math_pattern.search(text_clean):
            return 'math'
        
        # Default to body text
        return 'body'
    
    def _detect_tables(self, blocks: List[Dict]) -> bool:
        """
        Detect presence of tables in the page.
        
        Args:
            blocks: List of text blocks
            
        Returns:
            True if tables detected
        """
        for block in blocks:
            text = self._extract_block_text(block)
            if self.table_pattern.search(text):
                return True
        return False
    
    def _identify_sections(self, text: str) -> List[Dict]:
        """
        Identify document sections and their positions.
        
        Args:
            text: Full document text
            
        Returns:
            List of section dictionaries
        """
        sections = []
        lines = text.split('\n')
        
        current_section = None
        start_pos = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check if this line is a section heading
            if self.section_pattern.match(line_stripped):
                # Save previous section
                if current_section:
                    sections.append({
                        'title': current_section,
                        'start_line': start_pos,
                        'end_line': i - 1
                    })
                
                # Start new section
                current_section = line_stripped
                start_pos = i
        
        # Add last section
        if current_section:
            sections.append({
                'title': current_section,
                'start_line': start_pos,
                'end_line': len(lines) - 1
            })
        
        logger.debug(f"Identified {len(sections)} sections")
        return sections
    
    def _clean_extracted_text(self, text: str) -> str:
        """
        Clean extracted text for better processing.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Fix hyphenation at line breaks
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        
        # Normalize spaces
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Remove trailing/leading whitespace from lines
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text
    
    def _calculate_page_confidence(self, 
                                  text: str, 
                                  has_columns: bool,
                                  page_num: int) -> float:
        """
        Calculate confidence score for page extraction.
        
        Args:
            text: Extracted text
            text_stripped = text.strip()has_columns: Whether page has multi-column layout
            page_num: Page number
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence = 1.0
        
        # Penalize empty or very short text
        if len(text.strip()) < 50:
            confidence *= 0.3
        elif len(text.strip()) < 200:
            confidence *= 0.6
        
        # Penalize first/last pages (often have less standard layout)
        if page_num == 0:
            confidence *= 0.9
        
        # Slight penalty for multi-column (harder to extract correctly)
        if has_columns:
            confidence *= 0.95
        
        return max(0.0, min(1.0, confidence))
    
    def _calculate_confidence(self, pages: List[ExtractedPage]) -> float:
        """
        Calculate overall extraction confidence.
        
        Args:
            pages: List of extracted pages
            
        Returns:
            Overall confidence score (0.0 to 1.0)
        """
        if not pages:
            return 0.0
        
        # Average page confidences
        avg_confidence = sum(p.confidence for p in pages) / len(pages)
        
        # Penalize if many pages have low confidence
        low_confidence_pages = sum(1 for p in pages if p.confidence < 0.5)
        if low_confidence_pages > len(pages) * 0.3:  # More than 30% low confidence
            avg_confidence *= 0.8
        
        return round(avg_confidence, 2)


