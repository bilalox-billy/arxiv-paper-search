"""
Quick test script for the CLI tool

This runs a few basic CLI commands to verify everything works.
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd):
    """Run a command and return the result."""
    print(f"\n{'='*70}")
    print(f"Running: {' '.join(cmd)}")
    print('='*70)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    
    return True

def main():
    """Test basic CLI functionality."""
    python = sys.executable
    cli = Path(__file__).parent / "arxiv_search.py"
    
    print("\n" + "="*70)
    print("CLI TEST SUITE")
    print("="*70)
    
    tests = [
        # Test 1: Help
        ([python, str(cli), "--help"], "Show help"),
        
        # Test 2: Stats
        ([python, str(cli), "stats"], "Show statistics"),
        
        # Test 3: Search (if papers exist)
        ([python, str(cli), "search", "learning", "--limit", "3"], "Basic search"),
    ]
    
    passed = 0
    failed = 0
    
    for cmd, description in tests:
        print(f"\nTest: {description}")
        if run_command(cmd):
            passed += 1
            print("✓ PASSED")
        else:
            failed += 1
            print("✗ FAILED")
    
    print(f"\n{'='*70}")
    print(f"RESULTS: {passed} passed, {failed} failed")
    print('='*70)
    
    if failed == 0:
        print("\n✓ All CLI tests passed!")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
