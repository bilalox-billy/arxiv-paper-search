"""
ArXiv Paper Search System - Interactive CLI
"""

import click
import sys
from typing import Optional, List
from tabulate import tabulate
from datetime import datetime, timedelta
import json

# Import our modules
from arxiv_client import ArxivClient
from pdf_processor import PDFDownloader, PDFExtractor
from text_chunking import TextChunker
from embedding import EmbeddingGenerator, EmbeddingPipeline
from search import PaperSearchEngine, SearchMode
from database import DatabaseManager

@click.group()
@click.pass_context
def cli(ctx):
    """ArXiv Paper Search System - Personal Research Tool"""
    pass

@cli.command()
@click.option('--query', '-q', required=True, help='Search query')
@click.option('--mode', '-m', 
              type=click.Choice(['vector', 'hybrid', 'keyword']),
              default='hybrid',
              help='Search mode')
@click.option('--limit', '-l', default=10, help='Number of results')
@click.option('--authors', '-a', multiple=True, help='Filter by authors')
@click.option('--categories', '-c', multiple=True, help='Filter by categories')
@click.option('--days', '-d', type=int, help='Papers from last N days')
@click.option('--export', '-e', help='Export results to file')
@click.pass_context
def search(ctx, query, mode, limit, authors, categories, days, export):
    """Search for papers"""
    pass

def display_results(results: List):
    """Display search results in a formatted table."""
    pass

def explore_results(ctx, results: List):
    """Interactive result exploration."""
    pass

def show_paper_details(result):
    """Show detailed information about a paper."""
    pass

def find_similar(ctx, result):
    """Find papers similar to the selected one."""
    pass

def download_papers(ctx, results):
    """Download PDFs for selected papers."""
    pass

def export_results(results: List, filename: str):
    """Export search results to JSON file."""
    pass

@cli.command()
@click.option('--categories', '-c', multiple=True, required=True,
              help='ArXiv categories to fetch (e.g., cs.LG, cs.AI)')
@click.option('--days', '-d', default=7, help='Fetch papers from last N days')
@click.option('--max-papers', '-m', default=100, help='Maximum papers to fetch')
@click.pass_context
def fetch(ctx, categories, days, max_papers):
    """Fetch recent papers from ArXiv"""
    pass

@cli.command()
@click.pass_context
def stats(ctx):
    """Show database statistics"""
    pass

@cli.command()
@click.option('--init', is_flag=True, help='Initialize database schema')
@click.option('--rebuild-index', is_flag=True, help='Rebuild vector indexes')
@click.option('--cleanup', is_flag=True, help='Clean up old data')
@click.pass_context
def manage(ctx, init, rebuild_index, cleanup):
    """Database management operations"""
    pass

if __name__ == '__main__':
    cli()