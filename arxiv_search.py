#!/usr/bin/env python
"""
ArXiv Paper Search - Command Line Interface

A powerful CLI tool for searching and managing academic papers.

Usage:
    python arxiv_search.py search "deep learning"
    python arxiv_search.py similar 123
    python arxiv_search.py fetch "cat:cs.AI" --max 10
    python arxiv_search.py stats
"""

import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.similarity_search import PaperSearchEngine, SearchMode, SearchResult
from src.embedding import EmbeddingGenerator
from src.database import DatabaseManager
from src.pdf_processor import PaperProcessor
from config.settings import DB_CONFIG, EMBEDDING_MODEL

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")

def print_paper(result: SearchResult, index: int = None, show_abstract: bool = False):
    """Print a single paper result."""
    prefix = f"{Colors.BOLD}{index}. {Colors.END}" if index else ""
    
    print(f"{prefix}{Colors.BOLD}{result.title}{Colors.END}")
    print(f"   {Colors.CYAN}ArXiv ID:{Colors.END} {result.arxiv_id}")
    print(f"   {Colors.CYAN}Score:{Colors.END} {result.score:.4f}")
    
    if result.authors:
        authors = ', '.join(result.authors[:3])
        if len(result.authors) > 3:
            authors += f" (+{len(result.authors) - 3} more)"
        print(f"   {Colors.CYAN}Authors:{Colors.END} {authors}")
    
    if result.categories:
        print(f"   {Colors.CYAN}Categories:{Colors.END} {', '.join(result.categories[:5])}")
    
    if result.published_date:
        print(f"   {Colors.CYAN}Published:{Colors.END} {result.published_date}")
    
    if show_abstract and result.abstract:
        abstract = result.abstract[:200] + "..." if len(result.abstract) > 200 else result.abstract
        print(f"   {Colors.CYAN}Abstract:{Colors.END} {abstract}")
    
    if result.matched_chunks:
        print(f"   {Colors.CYAN}Matched chunks:{Colors.END} {len(result.matched_chunks)}")
    
    print()

def cmd_search(args):
    """Search for papers."""
    print_header(f"Searching: {args.query}")
    
    # Parse search mode
    mode_map = {
        'vector': SearchMode.VECTOR,
        'keyword': SearchMode.KEYWORD,
        'hybrid': SearchMode.HYBRID
    }
    mode = mode_map.get(args.mode, SearchMode.HYBRID)
    
    # Build filters
    filters = {}
    if args.categories:
        filters['categories'] = args.categories.split(',')
    if args.authors:
        filters['authors'] = args.authors.split(',')
    if args.date_from:
        filters['date_from'] = args.date_from
    if args.date_to:
        filters['date_to'] = args.date_to
    
    # Initialize search engine
    print(f"{Colors.YELLOW}Initializing search engine...{Colors.END}")
    embedding_gen = EmbeddingGenerator(EMBEDDING_MODEL)
    search_engine = PaperSearchEngine(DB_CONFIG, embedding_gen)
    
    # Search
    print(f"{Colors.YELLOW}Searching (mode: {mode.value})...{Colors.END}\n")
    results = search_engine.search(
        query=args.query,
        mode=mode,
        limit=args.limit,
        filters=filters if filters else None
    )
    
    # Display results
    if results:
        print(f"{Colors.GREEN}Found {len(results)} papers:{Colors.END}\n")
        for i, result in enumerate(results, 1):
            print_paper(result, i, show_abstract=args.show_abstract)
        
        # Export if requested
        if args.export:
            export_results(results, args.export, args.format)
    else:
        print(f"{Colors.YELLOW}No results found.{Colors.END}")
    
    search_engine.close()

def cmd_similar(args):
    """Find papers similar to a given paper."""
    print_header(f"Finding Similar Papers")
    
    # Initialize search engine
    embedding_gen = EmbeddingGenerator(EMBEDDING_MODEL)
    search_engine = PaperSearchEngine(DB_CONFIG, embedding_gen)
    
    # Get reference paper info
    db = DatabaseManager(DB_CONFIG)
    conn = db.get_connection()
    
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, arxiv_id, title FROM papers WHERE id = %s OR arxiv_id = %s",
            (args.paper_id, args.paper_id)
        )
        row = cursor.fetchone()
    
    db.close_connection()
    
    if not row:
        print(f"{Colors.RED}Paper not found: {args.paper_id}{Colors.END}")
        return
    
    paper_id, arxiv_id, title = row
    print(f"{Colors.CYAN}Reference paper:{Colors.END}")
    print(f"  ID: {paper_id}")
    print(f"  ArXiv ID: {arxiv_id}")
    print(f"  Title: {title}\n")
    
    # Find similar papers
    print(f"{Colors.YELLOW}Finding similar papers...{Colors.END}\n")
    results = search_engine.find_similar_papers(
        paper_id=paper_id,
        limit=args.limit
    )
    
    # Display results
    if results:
        print(f"{Colors.GREEN}Found {len(results)} similar papers:{Colors.END}\n")
        for i, result in enumerate(results, 1):
            print_paper(result, i, show_abstract=args.show_abstract)
        
        # Export if requested
        if args.export:
            export_results(results, args.export, args.format)
    else:
        print(f"{Colors.YELLOW}No similar papers found.{Colors.END}")
    
    search_engine.close()

def cmd_fetch(args):
    """Fetch and process papers from ArXiv."""
    print_header(f"Fetching Papers from ArXiv")
    
    print(f"{Colors.CYAN}Query:{Colors.END} {args.query}")
    print(f"{Colors.CYAN}Max papers:{Colors.END} {args.max_papers}")
    print(f"{Colors.CYAN}Skip existing:{Colors.END} {args.skip_existing}\n")
    
    # Initialize processor
    processor = PaperProcessor(DB_CONFIG, max_workers=args.workers)
    
    # Process papers
    print(f"{Colors.YELLOW}Processing papers...{Colors.END}\n")
    stats = processor.process_papers(
        query=args.query,
        max_papers=args.max_papers,
        skip_existing=args.skip_existing
    )
    
    # Display stats
    print(f"\n{Colors.GREEN}Processing Complete!{Colors.END}\n")
    print(f"  Papers fetched: {stats['papers_fetched']}")
    print(f"  Papers skipped: {stats['papers_skipped']}")
    print(f"  Papers downloaded: {stats['papers_downloaded']}")
    print(f"  Papers extracted: {stats['papers_extracted']}")
    print(f"  Papers chunked: {stats['papers_chunked']}")
    print(f"  Papers embedded: {stats['papers_embedded']}")
    print(f"  Papers failed: {stats['papers_failed']}")
    
    # Calculate duration
    if 'end_time' in stats and 'start_time' in stats:
        duration = (stats['end_time'] - stats['start_time']).total_seconds()
        print(f"  Duration: {duration:.1f}s")
    
    processor.close()

def cmd_stats(args):
    """Show database statistics."""
    print_header("Database Statistics")
    
    db = DatabaseManager(DB_CONFIG)
    stats = db.get_database_stats()
    
    print(f"{Colors.CYAN}Papers:{Colors.END}")
    print(f"  Total: {stats['total_papers']}")
    print(f"  With PDFs: {stats['papers_with_pdfs']}")
    print(f"  Processed: {stats['papers_processed']}")
    print(f"  With embeddings: {stats['papers_with_embeddings']}")
    print(f"  With errors: {stats['papers_with_errors']}")
    
    print(f"\n{Colors.CYAN}Chunks:{Colors.END}")
    print(f"  Total: {stats['total_chunks']}")
    
    print(f"\n{Colors.CYAN}Storage:{Colors.END}")
    print(f"  Database size: {stats['database_size']}")
    
    # Get recent papers
    conn = db.get_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT arxiv_id, title, embedding_generated, created_at
            FROM papers
            ORDER BY created_at DESC
            LIMIT 5
        """)
        recent = cursor.fetchall()
    
    if recent:
        print(f"\n{Colors.CYAN}Recent Papers:{Colors.END}")
        for arxiv_id, title, embedded, created in recent:
            status = f"{Colors.GREEN}✓{Colors.END}" if embedded else f"{Colors.RED}✗{Colors.END}"
            date = created.strftime('%Y-%m-%d %H:%M')
            print(f"  {status} {arxiv_id}: {title[:50]}... ({date})")
    
    db.close_connection()

def cmd_detail(args):
    """Show detailed information about a paper."""
    print_header("Paper Details")
    
    db = DatabaseManager(DB_CONFIG)
    conn = db.get_connection()
    
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT 
                id, arxiv_id, title, abstract, authors, categories,
                primary_category, published_date, pdf_url,
                pdf_downloaded, pdf_processed, embedding_generated,
                processing_error
            FROM papers
            WHERE id = %s OR arxiv_id = %s
        """, (args.paper_id, args.paper_id))
        row = cursor.fetchone()
    
    if not row:
        print(f"{Colors.RED}Paper not found: {args.paper_id}{Colors.END}")
        db.close_connection()
        return
    
    (pid, arxiv_id, title, abstract, authors, categories, primary_cat,
     pub_date, pdf_url, pdf_dl, pdf_proc, embedded, error) = row
    
    print(f"{Colors.BOLD}{title}{Colors.END}\n")
    print(f"{Colors.CYAN}ArXiv ID:{Colors.END} {arxiv_id}")
    print(f"{Colors.CYAN}Database ID:{Colors.END} {pid}")
    print(f"{Colors.CYAN}Primary Category:{Colors.END} {primary_cat}")
    print(f"{Colors.CYAN}Categories:{Colors.END} {', '.join(categories) if categories else 'N/A'}")
    print(f"{Colors.CYAN}Published:{Colors.END} {pub_date}")
    print(f"{Colors.CYAN}PDF URL:{Colors.END} {pdf_url}")
    
    print(f"\n{Colors.CYAN}Status:{Colors.END}")
    print(f"  PDF Downloaded: {Colors.GREEN + '✓' + Colors.END if pdf_dl else Colors.RED + '✗' + Colors.END}")
    print(f"  PDF Processed: {Colors.GREEN + '✓' + Colors.END if pdf_proc else Colors.RED + '✗' + Colors.END}")
    print(f"  Embeddings Generated: {Colors.GREEN + '✓' + Colors.END if embedded else Colors.RED + '✗' + Colors.END}")
    
    if error:
        print(f"\n{Colors.RED}Error:{Colors.END} {error}")
    
    print(f"\n{Colors.CYAN}Authors ({len(authors) if authors else 0}):{Colors.END}")
    if authors:
        for i, author in enumerate(authors[:10], 1):
            print(f"  {i}. {author}")
        if len(authors) > 10:
            print(f"  ... and {len(authors) - 10} more")
    
    if abstract:
        print(f"\n{Colors.CYAN}Abstract:{Colors.END}")
        print(f"{abstract}\n")
    
    # Get chunk info
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*), 
                   COUNT(CASE WHEN has_math THEN 1 END) as math_chunks,
                   COUNT(CASE WHEN has_code THEN 1 END) as code_chunks
            FROM paper_chunks
            WHERE paper_id = %s
        """, (pid,))
        chunk_stats = cursor.fetchone()
    
    if chunk_stats and chunk_stats[0] > 0:
        print(f"{Colors.CYAN}Chunks:{Colors.END}")
        print(f"  Total: {chunk_stats[0]}")
        print(f"  With math: {chunk_stats[1]}")
        print(f"  With code: {chunk_stats[2]}")
    
    db.close_connection()

def export_results(results: List[SearchResult], filename: str, format: str):
    """Export search results to file."""
    if format == 'json':
        export_json(results, filename)
    elif format == 'csv':
        export_csv(results, filename)
    elif format == 'bibtex':
        export_bibtex(results, filename)
    else:
        print(f"{Colors.RED}Unknown format: {format}{Colors.END}")

def export_json(results: List[SearchResult], filename: str):
    """Export results as JSON."""
    data = []
    for r in results:
        data.append({
            'paper_id': r.paper_id,
            'arxiv_id': r.arxiv_id,
            'title': r.title,
            'abstract': r.abstract,
            'authors': r.authors,
            'categories': r.categories,
            'published_date': r.published_date,
            'score': r.score,
            'matched_chunks': r.matched_chunks
        })
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{Colors.GREEN}Exported {len(results)} results to {filename}{Colors.END}")

def export_csv(results: List[SearchResult], filename: str):
    """Export results as CSV."""
    import csv
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ArXiv ID', 'Title', 'Authors', 'Categories', 'Published', 'Score'])
        
        for r in results:
            writer.writerow([
                r.arxiv_id,
                r.title,
                '; '.join(r.authors),
                '; '.join(r.categories),
                r.published_date,
                f"{r.score:.4f}"
            ])
    
    print(f"\n{Colors.GREEN}Exported {len(results)} results to {filename}{Colors.END}")

def export_bibtex(results: List[SearchResult], filename: str):
    """Export results as BibTeX."""
    with open(filename, 'w', encoding='utf-8') as f:
        for r in results:
            # Generate BibTeX key
            first_author = r.authors[0].split()[-1] if r.authors else 'Unknown'
            year = r.published_date[:4] if r.published_date else 'YYYY'
            key = f"{first_author}{year}{r.arxiv_id.replace('.', '_')}"
            
            f.write(f"@article{{{key},\n")
            f.write(f"  title = {{{r.title}}},\n")
            if r.authors:
                f.write(f"  author = {{{' and '.join(r.authors)}}},\n")
            f.write(f"  year = {{{year}}},\n")
            f.write(f"  journal = {{arXiv preprint arXiv:{r.arxiv_id}}},\n")
            if r.abstract:
                f.write(f"  abstract = {{{r.abstract}}},\n")
            f.write(f"  url = {{https://arxiv.org/abs/{r.arxiv_id}}}\n")
            f.write("}\n\n")
    
    print(f"\n{Colors.GREEN}Exported {len(results)} results to {filename}{Colors.END}")

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='ArXiv Paper Search - Command Line Interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for papers
  %(prog)s search "deep learning for NLP" --mode hybrid --limit 10
  
  # Search with filters
  %(prog)s search "neural networks" --categories cs.AI,cs.LG --date-from 2024-01-01
  
  # Find similar papers
  %(prog)s similar 123
  %(prog)s similar 2301.12345
  
  # Fetch new papers from ArXiv
  %(prog)s fetch "cat:cs.AI" --max 20
  
  # Show database statistics
  %(prog)s stats
  
  # Show paper details
  %(prog)s detail 123
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for papers')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--mode', choices=['vector', 'keyword', 'hybrid'],
                               default='hybrid', help='Search mode (default: hybrid)')
    search_parser.add_argument('--limit', type=int, default=10,
                               help='Maximum number of results (default: 10)')
    search_parser.add_argument('--categories', help='Filter by categories (comma-separated)')
    search_parser.add_argument('--authors', help='Filter by authors (comma-separated)')
    search_parser.add_argument('--date-from', help='Filter by date from (YYYY-MM-DD)')
    search_parser.add_argument('--date-to', help='Filter by date to (YYYY-MM-DD)')
    search_parser.add_argument('--show-abstract', action='store_true',
                               help='Show paper abstracts')
    search_parser.add_argument('--export', help='Export results to file')
    search_parser.add_argument('--format', choices=['json', 'csv', 'bibtex'],
                               default='json', help='Export format (default: json)')
    
    # Similar command
    similar_parser = subparsers.add_parser('similar', help='Find similar papers')
    similar_parser.add_argument('paper_id', help='Paper ID or ArXiv ID')
    similar_parser.add_argument('--limit', type=int, default=10,
                                help='Maximum number of results (default: 10)')
    similar_parser.add_argument('--show-abstract', action='store_true',
                                help='Show paper abstracts')
    similar_parser.add_argument('--export', help='Export results to file')
    similar_parser.add_argument('--format', choices=['json', 'csv', 'bibtex'],
                                default='json', help='Export format (default: json)')
    
    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='Fetch papers from ArXiv')
    fetch_parser.add_argument('query', help='ArXiv query (e.g., "cat:cs.AI")')
    fetch_parser.add_argument('--max-papers', type=int, default=10,
                              help='Maximum papers to fetch (default: 10)')
    fetch_parser.add_argument('--workers', type=int, default=4,
                              help='Number of workers (default: 4)')
    fetch_parser.add_argument('--skip-existing', action='store_true',
                              help='Skip papers already in database')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show database statistics')
    
    # Detail command
    detail_parser = subparsers.add_parser('detail', help='Show paper details')
    detail_parser.add_argument('paper_id', help='Paper ID or ArXiv ID')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    try:
        if args.command == 'search':
            cmd_search(args)
        elif args.command == 'similar':
            cmd_similar(args)
        elif args.command == 'fetch':
            cmd_fetch(args)
        elif args.command == 'stats':
            cmd_stats(args)
        elif args.command == 'detail':
            cmd_detail(args)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
