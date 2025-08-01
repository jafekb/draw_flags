#!/usr/bin/env python3
"""
Test script to verify that the flag searcher produces consistent embeddings.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.src.flag_searcher import FlagSearcher

def test_flag_searcher():
    """Test the flag searcher with a sample query"""
    
    # Create flag searcher
    searcher = FlagSearcher(top_k=5)
    
    # Test with a sample query
    # test_query = "red and white stripes"
    test_query = "american flag"
    print(f"Testing query: '{test_query}'")
    
    # Run the query
    results = searcher.query(test_query, is_image=False)
    
    print(f"Found {len(results.flags)} flags")
    for i, flag in enumerate(results.flags):
        print(f"{i+1}. {flag.name} (score: {flag.score:.4f})")

if __name__ == "__main__":
    test_flag_searcher() 
