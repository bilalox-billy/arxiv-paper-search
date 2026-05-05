"""
Example Usage of ArXiv Paper Search System
Demonstrates how to use the complete pipeline
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.pdf_processor import PaperProcessor
from config.settings import DB_CONFIG
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    """Example: Process papers from ArXiv"""
    
    print("="*60)
    print("ArXiv Paper Search System - Example Usage")
    print("="*60)
    
    # Initialize processor
    processor = PaperProcessor(
        db_config=DB_CONFIG,
        max_workers=2  # Process 2 papers in parallel
    )
    
    # Example 1: Process a specific paper by ID
    print("\nExample 1: Process specific paper")
    print("-" * 60)
    result = processor.process_papers(
        query="1706.03762",  # "Attention Is All You Need"
        max_papers=1,
        skip_existing=True
    )
    print(f"Result: {result['papers_embedded']} papers embedded")
    
    # Example 2: Search and process recent AI papers
    print("\nExample 2: Process recent AI papers")
    print("-" * 60)
    result = processor.process_papers(
        query="cat:cs.AI",
        max_papers=5,
        skip_existing=True
    )
    print(f"Result: {result['papers_embedded']} papers embedded")
    
    # Example 3: Get database statistics
    print("\nExample 3: Database statistics")
    print("-" * 60)
    stats = processor.get_processing_stats()
    print(f"Total papers: {stats['total_papers']}")
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Database size: {stats['database_size']}")
    
    # Cleanup
    processor.close()
    
    print("\n" + "="*60)
    print("Processing complete!")
    print("="*60)


if __name__ == "__main__":
    main()
