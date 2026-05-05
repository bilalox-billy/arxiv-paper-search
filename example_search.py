"""
Example usage of the Paper Search Engine

This demonstrates how to use the search engine for various search tasks.
"""

from src.similarity_search import PaperSearchEngine, SearchMode
from src.embedding import EmbeddingGenerator
from config.settings import DB_CONFIG, EMBEDDING_MODEL
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def print_separator(title: str):
    """Print a formatted separator."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(result, index: int):
    """Print a single search result."""
    print(f"\n{index}. {result.title}")
    print(f"   📄 ArXiv ID: {result.arxiv_id}")
    print(f"   ⭐ Score: {result.score:.4f}")
    print(f"   👥 Authors: {', '.join(result.authors[:3])}")
    if len(result.authors) > 3:
        print(f"              (and {len(result.authors) - 3} more)")
    print(f"   🏷️  Categories: {', '.join(result.categories)}")
    print(f"   📅 Published: {result.published_date}")
    
    if result.matched_chunks:
        print(f"   📝 Matched {len(result.matched_chunks)} text chunks")
        # Show first matched chunk
        if result.matched_chunks:
            chunk = result.matched_chunks[0]
            text = chunk.get('text', '')[:150]
            section = chunk.get('section', 'unknown')
            print(f"      From section '{section}': {text}...")

def example_vector_search():
    """Example 1: Pure vector similarity search."""
    print_separator("Example 1: Vector Similarity Search")
    
    print("\nSearching for papers about 'transformer architectures for NLP'...")
    print("Using: Pure vector similarity (semantic search)")
    
    # Initialize
    embedding_gen = EmbeddingGenerator(EMBEDDING_MODEL)
    search_engine = PaperSearchEngine(DB_CONFIG, embedding_gen)
    
    # Search
    results = search_engine.search(
        query="transformer architectures for natural language processing",
        mode=SearchMode.VECTOR,
        limit=5
    )
    
    # Display results
    if results:
        print(f"\nFound {len(results)} papers:")
        for i, result in enumerate(results, 1):
            print_result(result, i)
    else:
        print("\nNo results found.")
    
    search_engine.close()

def example_keyword_search():
    """Example 2: Keyword-based search."""
    print_separator("Example 2: Keyword Search")
    
    print("\nSearching for papers about 'reinforcement learning'...")
    print("Using: Full-text keyword search")
    
    # Initialize
    embedding_gen = EmbeddingGenerator(EMBEDDING_MODEL)
    search_engine = PaperSearchEngine(DB_CONFIG, embedding_gen)
    
    # Search
    results = search_engine.search(
        query="reinforcement learning Q-learning",
        mode=SearchMode.KEYWORD,
        limit=5
    )
    
    # Display results
    if results:
        print(f"\nFound {len(results)} papers:")
        for i, result in enumerate(results, 1):
            print_result(result, i)
    else:
        print("\nNo results found.")
    
    search_engine.close()

def example_hybrid_search():
    """Example 3: Hybrid search (recommended)."""
    print_separator("Example 3: Hybrid Search (Recommended)")
    
    print("\nSearching for papers about 'generative adversarial networks'...")
    print("Using: Hybrid search (70% vector + 30% keyword)")
    
    # Initialize
    embedding_gen = EmbeddingGenerator(EMBEDDING_MODEL)
    search_engine = PaperSearchEngine(DB_CONFIG, embedding_gen)
    
    # Search
    results = search_engine.search(
        query="generative adversarial networks for image generation",
        mode=SearchMode.HYBRID,  # This is the default
        limit=5
    )
    
    # Display results
    if results:
        print(f"\nFound {len(results)} papers:")
        for i, result in enumerate(results, 1):
            print_result(result, i)
    else:
        print("\nNo results found.")
    
    search_engine.close()

def example_filtered_search():
    """Example 4: Search with filters."""
    print_separator("Example 4: Filtered Search")
    
    print("\nSearching for papers about 'deep learning'...")
    print("Filters: Categories [cs.AI, cs.LG], Published after 2023-01-01")
    
    # Initialize
    embedding_gen = EmbeddingGenerator(EMBEDDING_MODEL)
    search_engine = PaperSearchEngine(DB_CONFIG, embedding_gen)
    
    # Search with filters
    results = search_engine.search(
        query="deep learning neural networks",
        mode=SearchMode.HYBRID,
        limit=5,
        filters={
            'categories': ['cs.AI', 'cs.LG'],
            'date_from': '2023-01-01'
        }
    )
    
    # Display results
    if results:
        print(f"\nFound {len(results)} papers:")
        for i, result in enumerate(results, 1):
            print_result(result, i)
    else:
        print("\nNo results found with these filters.")
    
    search_engine.close()

def example_similar_papers():
    """Example 5: Find similar papers."""
    print_separator("Example 5: Find Similar Papers")
    
    # Initialize
    embedding_gen = EmbeddingGenerator(EMBEDDING_MODEL)
    search_engine = PaperSearchEngine(DB_CONFIG, embedding_gen)
    
    # First, find a paper
    print("\nStep 1: Finding a reference paper about 'attention mechanism'...")
    results = search_engine.search(
        query="attention mechanism",
        mode=SearchMode.VECTOR,
        limit=1
    )
    
    if not results:
        print("No papers found.")
        search_engine.close()
        return
    
    reference = results[0]
    print(f"\nReference paper:")
    print_result(reference, 1)
    
    # Find similar papers
    print(f"\nStep 2: Finding papers similar to '{reference.title[:60]}...'")
    similar = search_engine.find_similar_papers(
        paper_id=reference.paper_id,
        limit=5
    )
    
    # Display results
    if similar:
        print(f"\nFound {len(similar)} similar papers:")
        for i, result in enumerate(similar, 1):
            print_result(result, i)
    else:
        print("\nNo similar papers found.")
    
    search_engine.close()

def example_compare_modes():
    """Example 6: Compare different search modes."""
    print_separator("Example 6: Comparing Search Modes")
    
    query = "neural network optimization"
    print(f"\nSearching for: '{query}'")
    print("Comparing results from Vector, Keyword, and Hybrid modes...")
    
    # Initialize
    embedding_gen = EmbeddingGenerator(EMBEDDING_MODEL)
    search_engine = PaperSearchEngine(DB_CONFIG, embedding_gen)
    
    # Search with each mode
    modes = [SearchMode.VECTOR, SearchMode.KEYWORD, SearchMode.HYBRID]
    all_results = {}
    
    for mode in modes:
        results = search_engine.search(
            query=query,
            mode=mode,
            limit=3
        )
        all_results[mode] = results
    
    # Display comparison
    for mode in modes:
        print(f"\n--- {mode.value.upper()} MODE ---")
        results = all_results[mode]
        if results:
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.title[:60]}... (score: {result.score:.4f})")
        else:
            print("No results")
    
    search_engine.close()

def interactive_search():
    """Example 7: Interactive search session."""
    print_separator("Example 7: Interactive Search")
    
    # Initialize
    embedding_gen = EmbeddingGenerator(EMBEDDING_MODEL)
    search_engine = PaperSearchEngine(DB_CONFIG, embedding_gen)
    
    print("\nInteractive Paper Search")
    print("Enter your search queries (or 'quit' to exit)")
    print("Example queries:")
    print("  - 'transformer models'")
    print("  - 'computer vision detection'")
    print("  - 'graph neural networks'")
    
    while True:
        print("\n" + "-" * 70)
        query = input("\nSearch query: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            break
        
        if not query:
            continue
        
        results = search_engine.search(
            query=query,
            mode=SearchMode.HYBRID,
            limit=5
        )
        
        if results:
            print(f"\nFound {len(results)} papers:")
            for i, result in enumerate(results, 1):
                print_result(result, i)
        else:
            print("\nNo results found. Try a different query.")
    
    print("\nThank you for using the search engine!")
    search_engine.close()

def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("  ARXIV PAPER SEARCH ENGINE - EXAMPLES")
    print("=" * 70)
    
    examples = [
        ("Vector Search", example_vector_search),
        ("Keyword Search", example_keyword_search),
        ("Hybrid Search", example_hybrid_search),
        ("Filtered Search", example_filtered_search),
        ("Find Similar Papers", example_similar_papers),
        ("Compare Search Modes", example_compare_modes),
    ]
    
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")
    print(f"{len(examples) + 1}. Interactive Search")
    print("0. Run all examples")
    
    try:
        choice = input("\nSelect example (0-7, or press Enter for all): ").strip()
        
        if choice == '' or choice == '0':
            # Run all examples
            for name, func in examples:
                try:
                    func()
                except Exception as e:
                    print(f"\n❌ Error in {name}: {e}")
        elif choice == str(len(examples) + 1):
            interactive_search()
        elif choice.isdigit() and 1 <= int(choice) <= len(examples):
            name, func = examples[int(choice) - 1]
            func()
        else:
            print("Invalid choice.")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
