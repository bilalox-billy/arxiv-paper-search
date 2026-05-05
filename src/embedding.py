from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Optional
import torch
import logging
from tqdm import tqdm
import psycopg2
from psycopg2.extras import execute_batch

logger = logging.getLogger(__name__)



class EmbeddingGenerator:
    """Efficient embedding generation with caching and batch processing."""
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Optional
import torch
import logging
from tqdm import tqdm
import psycopg2
from psycopg2.extras import execute_batch

logger = logging.getLogger(__name__)



class EmbeddingGenerator:
 from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Optional
import torch
import logging
from tqdm import tqdm
import psycopg2
from psycopg2.extras import execute_batch

logger = logging.getLogger(__name__)



class EmbeddingGenerator:
 """Efficient embedding generation with caching and batch processing."""

    _instance = None      # Stores the actual object
    def __new__(cls, *args, **kwargs):
       if cls._instance is None:
           
           # 1. Create the instance
           cls._instance = super(EmbeddingGenerator, cls).__new__(cls)
           
           # 2. Explicitly create the flag on the new instance
           cls._instance._initialized = False 
           
           return cls._instance


    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        
# 3. Check our custom flag        
           if cls._instance._initialized:
                      # We've been here before. Do nothing and exit.
                      return

# 4. Perform the heavy lifting
        self.model = SentenceTransformer(model_name)
        
        # 5. Set the flag so we never do this again
        self._initialized = True
return cls._instance        


    def generate_embeddings(self, 
                          texts: List[str],
                          show_progress: bool = True) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        pass
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text before embedding generation."""
        pass
    
    def generate_query_embedding(self, query: str) -> np.ndarray:
        """Generate embedding for a search query."""
        pass






 