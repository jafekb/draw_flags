"""
Quick test script to verify the environment is ready for data collection.
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all required packages can be imported."""
    print("Testing required imports...")
    
    required_packages = {
        'requests': 'Web requests',
        'bs4': 'HTML parsing (BeautifulSoup)',
        'numpy': 'Numerical operations',
        'PIL': 'Image processing (Pillow)',
    }
    
    optional_packages = {
        'cairosvg': 'SVG conversion (optional)',
        'sentence_transformers': 'CLIP embeddings (for processing step)',
    }
    
    all_ok = True
    
    # Test required packages
    for package, description in required_packages.items():
        try:
            __import__(package)
            print(f"  ✓ {package:20s} - {description}")
        except ImportError:
            print(f"  ✗ {package:20s} - {description} - MISSING")
            all_ok = False
    
    # Test optional packages
    print("\nOptional packages:")
    for package, description in optional_packages.items():
        try:
            __import__(package)
            print(f"  ✓ {package:25s} - {description}")
        except ImportError:
            print(f"  ⚠ {package:25s} - {description} - Not installed (optional)")
    
    return all_ok


def test_project_structure():
    """Test that the project structure is correct."""
    print("\nTesting project structure...")
    
    required_dirs = [
        'backend/scripts/data_collection',
        'backend/scripts/data_collection/collectors',
        'backend/data/comprehensive_flags',
    ]
    
    required_files = [
        'backend/scripts/data_collection/base_scraper.py',
        'backend/scripts/data_collection/wikipedia_scraper.py',
        'backend/scripts/data_collection/fotw_scraper.py',
        'backend/scripts/data_collection/deduplicator.py',
        'backend/scripts/data_collection/collectors/national_flags.py',
        'backend/scripts/data_collection/collectors/subdivisions.py',
        'backend/scripts/data_collection/collectors/organizations.py',
        'backend/scripts/data_collection/collectors/historical.py',
        'backend/scripts/data_collection/collectors/cities.py',
        'backend/scripts/collect_all_flags.py',
        'backend/scripts/download_and_process.py',
        'backend/scripts/validate_dataset.py',
    ]
    
    all_ok = True
    
    # Check directories
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists() and path.is_dir():
            print(f"  ✓ {dir_path}")
        else:
            print(f"  ✗ {dir_path} - MISSING")
            all_ok = False
    
    # Check files
    for file_path in required_files:
        path = Path(file_path)
        if path.exists() and path.is_file():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} - MISSING")
            all_ok = False
    
    return all_ok


def test_existing_data():
    """Test that existing national flags data is accessible."""
    print("\nTesting existing data...")
    
    flags_file = Path('backend/data/national_flags/flags.json')
    
    if not flags_file.exists():
        print(f"  ✗ {flags_file} - MISSING")
        return False
    
    try:
        import json
        with flags_file.open() as f:
            data = json.load(f)
        
        num_flags = len(data.get('flags', []))
        print(f"  ✓ {flags_file}")
        print(f"    Found {num_flags} existing national flags")
        return True
    except Exception as e:
        print(f"  ✗ Error reading {flags_file}: {e}")
        return False


def test_module_imports():
    """Test that our custom modules can be imported."""
    print("\nTesting custom module imports...")
    
    modules_to_test = [
        ('backend.common.flag_data', 'Flag data models'),
        ('backend.scripts.data_collection.base_scraper', 'Base scraper'),
        ('backend.scripts.data_collection.wikipedia_scraper', 'Wikipedia scraper'),
        ('backend.scripts.data_collection.deduplicator', 'Deduplicator'),
    ]
    
    all_ok = True
    
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            print(f"  ✓ {module_name:50s} - {description}")
        except ImportError as e:
            print(f"  ✗ {module_name:50s} - {description}")
            print(f"    Error: {e}")
            all_ok = False
    
    return all_ok


def print_summary(results):
    """Print a summary of test results."""
    print("\n" + "="*80)
    print("SETUP TEST SUMMARY")
    print("="*80)
    
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:10s} - {test_name}")
    
    print("="*80)
    
    if all_passed:
        print("\n✓ All tests passed! Your environment is ready for data collection.")
        print("\nNext steps:")
        print("1. Run: python scripts/collect_all_flags.py")
        print("2. Run: python scripts/download_and_process.py")
        print("3. Run: python scripts/validate_dataset.py")
    else:
        print("\n✗ Some tests failed. Please fix the issues above before proceeding.")
        print("\nCommon fixes:")
        print("- Install missing packages: pip install beautifulsoup4 requests numpy pillow")
        print("- Ensure you're running from the project root directory")
        print("- Check that all files were created correctly")
    
    return all_passed


def main():
    """Run all tests."""
    print("="*80)
    print("COMPREHENSIVE FLAGS DATABASE - SETUP TEST")
    print("="*80)
    print("\nThis script verifies that your environment is ready for data collection.\n")
    
    # Change to project root if needed
    if not Path('backend').exists():
        print("Error: Must run from project root directory")
        print(f"Current directory: {Path.cwd()}")
        print("Please cd to /home/bjafek/personal/draw_flags")
        sys.exit(1)
    
    results = {
        'Required Imports': test_imports(),
        'Project Structure': test_project_structure(),
        'Existing Data': test_existing_data(),
        'Custom Modules': test_module_imports(),
    }
    
    success = print_summary(results)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

