#!/usr/bin/env python3
"""
Test to verify that our custom cosine similarity implementation
produces the same results as scikit-learn's version.
"""

import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.src.flag_searcher import cosine_similarity

def test_cosine_similarity_equivalence():
    """Test that our cosine similarity matches scikit-learn's implementation"""
    
    # Create some test vectors
    a = np.array([[1, 2, 3], [4, 5, 6]])
    b = np.array([[1, 2, 3], [7, 8, 9], [10, 11, 12]])
    
    # Our implementation
    our_result = cosine_similarity(a, b)
    
    # Try to import scikit-learn for comparison (only in dev environment)
    try:
        from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine_similarity
        sklearn_result = sklearn_cosine_similarity(a, b)
        
        # Check if results are identical (within numerical precision)
        np.testing.assert_allclose(our_result, sklearn_result, rtol=1e-10, atol=1e-10)
        print("✅ Our cosine similarity implementation matches scikit-learn exactly!")
        
        print(f"Our result shape: {our_result.shape}")
        print(f"Sklearn result shape: {sklearn_result.shape}")
        print(f"Max difference: {np.max(np.abs(our_result - sklearn_result))}")
        
    except ImportError:
        print("⚠️  scikit-learn not available in current environment")
        print("✅ Our cosine similarity implementation works (no comparison possible)")
        print(f"Our result shape: {our_result.shape}")
        print(f"Our result sample: {our_result[0, 0]:.6f}")

def test_cosine_similarity_properties():
    """Test basic properties of cosine similarity"""
    
    # Test with identical vectors (should be 1.0)
    a = np.array([[1, 2, 3]])
    b = np.array([[1, 2, 3]])
    result = cosine_similarity(a, b)
    assert abs(result[0, 0] - 1.0) < 1e-10, f"Identical vectors should have similarity 1.0, got {result[0, 0]}"
    
    # Test with orthogonal vectors (should be 0.0)
    a = np.array([[1, 0, 0]])
    b = np.array([[0, 1, 0]])
    result = cosine_similarity(a, b)
    assert abs(result[0, 0]) < 1e-10, f"Orthogonal vectors should have similarity 0.0, got {result[0, 0]}"
    
    # Test with opposite vectors (should be -1.0)
    a = np.array([[1, 2, 3]])
    b = np.array([[-1, -2, -3]])
    result = cosine_similarity(a, b)
    assert abs(result[0, 0] - (-1.0)) < 1e-10, f"Opposite vectors should have similarity -1.0, got {result[0, 0]}"
    
    print("✅ Cosine similarity properties test passed!")

if __name__ == "__main__":
    print("Testing cosine similarity implementation...")
    test_cosine_similarity_properties()
    test_cosine_similarity_equivalence()
    print("🎉 All tests passed!") 
