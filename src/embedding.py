"""
Embedding Generation Module
Generates vector embeddings using SentenceTransformer models
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Optional
import torch
import logging
from tqdm import tqdm

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Efficient embedding generation with caching and batch processing (Singleton)."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        """
        Singleton pattern to ensure only one model instance is loaded.
        """
        if cls._instance is None:
            cls._instance = super(EmbeddingGenerator, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', device: Optional[str] = None):
        """
        Initialize embedding generator (only once due to singleton).
        
        Args:
            model_name: Name of the sentence transformer model
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
        """
        # Skip initialization if already done
        if self._initialized:
            return
        
        self.model_name = model_name
        
        # Determine device
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        
        logger.info(f"Loading embedding model: {model_name} on {self.device}")
        
        # Load model
        self.model = SentenceTransformer(model_name, device=self.device)
        
        # Get embedding dimension
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        logger.info(f"Model loaded: {model_name}, dimension={self.embedding_dim}, device={self.device}")
        
        # Mark as initialized
        self._initialized = True
    
    def generate_embeddings(self, 
                          texts: List[str],
                          batch_size: int = 32,
                          show_progress: bool = True,
                          normalize: bool = True) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings
            batch_size: Batch size for processing
            show_progress: Show progress bar
            normalize: Normalize embeddings to unit length
            
        Returns:
            Numpy array of embeddings (shape: [n_texts, embedding_dim])
        """
        if not texts:
            logger.warning("Empty text list provided")
            return np.array([])
        
        # Preprocess texts
        processed_texts = [self._preprocess_text(text) for text in texts]
        
        # Generate embeddings
        logger.debug(f"Generating embeddings for {len(texts)} texts")
        
        embeddings = self.model.encode(
            processed_texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=normalize,
            convert_to_numpy=True
        )
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        return embeddings
    
    def generate_query_embedding(self, query: str, normalize: bool = True) -> np.ndarray:
        """
        Generate embedding for a search query.
        
        Args:
            query: Query string
            normalize: Normalize embedding to unit length
            
        Returns:
            Numpy array embedding (shape: [embedding_dim])
        """
        if not query or not query.strip():
            logger.warning("Empty query provided")
            return np.zeros(self.embedding_dim)
        
        # Preprocess query
        processed_query = self._preprocess_text(query)
        
        # Generate embedding
        embedding = self.model.encode(
            processed_query,
            normalize_embeddings=normalize,
            convert_to_numpy=True
        )
        
        return embedding
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text before embedding generation.
        
        Args:
            text: Raw text
            
        Returns:
            Preprocessed text
        """
        if not text:
            return ""
        
        # Basic cleaning
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Truncate if too long (most models have max sequence length)
        max_length = 512  # Most models have 512 token limit
        words = text.split()
        if len(words) > max_length:
            text = ' '.join(words[:max_length])
            logger.debug(f"Truncated text from {len(words)} to {max_length} words")
        
        return text.strip()
    
    def get_model_info(self) -> dict:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model information
        """
        return {
            'model_name': self.model_name,
            'embedding_dim': self.embedding_dim,
            'device': self.device,
            'max_seq_length': getattr(self.model, 'max_seq_length', 'unknown')
        }
