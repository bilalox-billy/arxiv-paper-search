from typing import List, Dict, Optional, Any
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
import logging

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
except:
    pass

logger = logging.getLogger(__name__)


class TextChunker:
    """Intelligent text chunking for academic papers."""
    
    def __init__(self,
                 target_chunk_size: int = 768,
                 min_chunk_size: int = 256,
                 max_chunk_size: int = 1024,
                 overlap_size: int = 128):
        """
        Initialize text chunker.
        
        Args:
            target_chunk_size: Target number of tokens per chunk
            min_chunk_size: Minimum chunk size in tokens
            max_chunk_size: Maximum chunk size in tokens
            overlap_size: Number of tokens to overlap between chunks
        """
        self.target_chunk_size = target_chunk_size
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        
        logger.info(
            f"TextChunker initialized: target={target_chunk_size}, "
            f"min={min_chunk_size}, max={max_chunk_size}, overlap={overlap_size}"
        )
    
    def chunk_paper(self, 
                   text: str,
                   sections: List[Dict] = None,
                   preserve_sections: bool = True) -> List[Dict]:
        """
        Chunk paper text intelligently.
        
        Args:
            text: Full paper text
            sections: List of section dictionaries with 'title' and text ranges
            preserve_sections: If True, try to keep sections together
            
        Returns:
            List of chunk dictionaries with metadata
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []
        
        all_chunks = []
        
        if preserve_sections and sections:
            # Chunk by sections
            text_lines = text.split('\n')
            
            for section in sections:
                section_title = section.get('title', 'Unknown')
                start_line = section.get('start_line', 0)
                end_line = section.get('end_line', len(text_lines))
                
                # Extract section text
                section_text = '\n'.join(text_lines[start_line:end_line + 1])
                
                if section_text.strip():
                    # Chunk this section
                    section_chunks = self._chunk_text(section_text, section_name=section_title)
                    all_chunks.extend(section_chunks)
        else:
            # Chunk entire text without section boundaries
            all_chunks = self._chunk_text(text)
        
        # Add global chunk indices
        for i, chunk in enumerate(all_chunks):
            chunk['chunk_index'] = i
        
        logger.info(f"Created {len(all_chunks)} chunks from text")
        return all_chunks
    
    def _chunk_text(self, 
                   text: str,
                   section_name: Optional[str] = None) -> List[Dict]:
        """
        Chunk text with sliding window and overlap.
        
        Args:
            text: Text to chunk
            section_name: Optional section name for metadata
            
        Returns:
            List of chunk dictionaries
        """
        if not text or not text.strip():
            return []
        
        # Tokenize into sentences
        try:
            sentences = sent_tokenize(text)
        except Exception as e:
            logger.warning(f"Sentence tokenization failed, using simple split: {e}")
            sentences = [s.strip() + '.' for s in text.split('.') if s.strip()]
        
        if not sentences:
            return []
        
        chunks = []
        current_chunk_sentences = []
        current_chunk_tokens = 0
        char_position = 0
        
        for sentence in sentences:
            # Count tokens in sentence (approximate: split by whitespace)
            sentence_tokens = len(sentence.split())
            
            # Check if adding this sentence exceeds max size
            if current_chunk_tokens + sentence_tokens > self.max_chunk_size and current_chunk_sentences:
                # Save current chunk
                chunk_text = ' '.join(current_chunk_sentences)
                chunks.append({
                    'text': chunk_text,
                    'chunk_tokens': current_chunk_tokens,
                    'section_name': section_name,
                    'char_start': char_position,
                    'char_end': char_position + len(chunk_text),
                    'sentence_count': len(current_chunk_sentences),
                    'has_overlap': len(chunks) > 0  # Has overlap if not first chunk
                })
                
                char_position += len(chunk_text) + 1
                
                # Get overlap sentences from previous chunk
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk_sentences, 
                    self.overlap_size
                )
                
                # Start new chunk with overlap
                current_chunk_sentences = overlap_sentences + [sentence]
                current_chunk_tokens = sum(len(s.split()) for s in current_chunk_sentences)
            else:
                # Add sentence to current chunk
                current_chunk_sentences.append(sentence)
                current_chunk_tokens += sentence_tokens
                
                # Check if we've reached target size
                if current_chunk_tokens >= self.target_chunk_size:
                    chunk_text = ' '.join(current_chunk_sentences)
                    chunks.append({
                        'text': chunk_text,
                        'chunk_tokens': current_chunk_tokens,
                        'section_name': section_name,
                        'char_start': char_position,
                        'char_end': char_position + len(chunk_text),
                        'sentence_count': len(current_chunk_sentences),
                        'has_overlap': len(chunks) > 0
                    })
                    
                    char_position += len(chunk_text) + 1
                    
                    # Get overlap for next chunk
                    overlap_sentences = self._get_overlap_sentences(
                        current_chunk_sentences, 
                        self.overlap_size
                    )
                    current_chunk_sentences = overlap_sentences
                    current_chunk_tokens = sum(len(s.split()) for s in current_chunk_sentences)
        
        # Add remaining sentences as final chunk (if above minimum size)
        if current_chunk_sentences:
            current_chunk_tokens = sum(len(s.split()) for s in current_chunk_sentences)
            if current_chunk_tokens >= self.min_chunk_size or not chunks:
                chunk_text = ' '.join(current_chunk_sentences)
                chunks.append({
                    'text': chunk_text,
                    'chunk_tokens': current_chunk_tokens,
                    'section_name': section_name,
                    'char_start': char_position,
                    'char_end': char_position + len(chunk_text),
                    'sentence_count': len(current_chunk_sentences),
                    'has_overlap': len(chunks) > 0
                })
            elif chunks:
                # Append to last chunk if too small
                chunks[-1]['text'] += ' ' + ' '.join(current_chunk_sentences)
                chunks[-1]['chunk_tokens'] += current_chunk_tokens
                chunks[-1]['sentence_count'] += len(current_chunk_sentences)
        
        return chunks
    
    def _get_overlap_sentences(self, 
                              sentences: List[str],
                              target_tokens: int) -> List[str]:
        """
        Get sentences from end of chunk for overlap.
        
        Args:
            sentences: List of sentences from current chunk
            target_tokens: Target number of tokens for overlap
            
        Returns:
            List of sentences for overlap
        """
        if not sentences or target_tokens <= 0:
            return []
        
        overlap_sentences = []
        token_count = 0
        
        # Work backwards from end of sentences
        for sentence in reversed(sentences):
            sentence_tokens = len(sentence.split())
            if token_count + sentence_tokens <= target_tokens:
                overlap_sentences.insert(0, sentence)
                token_count += sentence_tokens
            else:
                break
        
        return overlap_sentences
    
    def get_chunk_stats(self, chunks: List[Dict]) -> Dict[str, Any]:
        """
        Get statistics about chunks.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Statistics dictionary
        """
        if not chunks:
            return {
                'total_chunks': 0,
                'avg_tokens': 0,
                'min_tokens': 0,
                'max_tokens': 0,
                'total_tokens': 0
            }
        
        token_counts = [c['chunk_tokens'] for c in chunks]
        
        return {
            'total_chunks': len(chunks),
            'avg_tokens': sum(token_counts) / len(token_counts),
            'min_tokens': min(token_counts),
            'max_tokens': max(token_counts),
            'total_tokens': sum(token_counts),
            'chunks_with_overlap': sum(1 for c in chunks if c.get('has_overlap', False))
        }

