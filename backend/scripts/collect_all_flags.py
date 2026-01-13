"""
Main script to orchestrate collection of all flags from different sources.
"""

import argparse
import json
from pathlib import Path
from typing import List

from backend.common.flag_data import Flag, FlagList
from backend.scripts.data_collection.collectors.national_flags import NationalFlagCollector
from backend.scripts.data_collection.collectors.subdivisions import SubdivisionFlagCollector
from backend.scripts.data_collection.collectors.organizations import OrganizationFlagCollector
from backend.scripts.data_collection.collectors.historical import HistoricalFlagCollector
from backend.scripts.data_collection.collectors.cities import CityFlagCollector
from backend.scripts.data_collection.fotw_scraper import FOTWScraper
from backend.scripts.data_collection.deduplicator import FlagDeduplicator


def collect_all_flags(test_mode: bool = False) -> List[Flag]:
    """
    Collect flags from all sources.
    
    Args:
        test_mode: If True, only collect a small subset for testing (~50 flags, <2 min)
    
    Returns:
        List of all collected flags
    """
    all_flags = []
    
    if test_mode:
        print("\n" + "="*80)
        print("TEST MODE: Collecting small subset (~20 flags)")
        print("="*80)
        print("This will take ~1-2 minutes (includes network requests)")
        print("For full collection, run without --test flag")
        print("="*80 + "\n")
    
    # Phase 1: High-quality structured data sources
    print("\n" + "="*80)
    print("PHASE 1: Collecting from high-quality structured sources")
    print("="*80)
    
    # National flags
    print("\n--- National Flags ---")
    national_collector = NationalFlagCollector(rate_limit_seconds=0.5 if test_mode else 1.0)
    
    if test_mode:
        # In test mode, limit to just a few countries for speed
        print("  Test mode: Collecting subset of national flags (first 20 countries)")
        national_collector.COUNTRY_PAGES = national_collector.COUNTRY_PAGES[:20]
        # Skip the gallery pages in test mode to save time
        national_collector.NATIONAL_FLAG_SOURCES = []
    
    national_flags = national_collector.collect()
    all_flags.extend(national_flags)
    if test_mode:
        print(f"  Test mode: Collected {len(national_flags)} national flags")
    
    if test_mode:
        # In test mode, skip the time-consuming collectors
        print("\n--- Skipping Other Collectors (test mode) ---")
        print("  Skipped: Subdivisions (would collect 2000-3000 flags)")
        print("  Skipped: Organizations (would collect 200-500 flags)")
        print("  Skipped: Historical (would collect 500-1000 flags)")
        print("  Skipped: Cities (would collect 500-1000 flags)")
        print("  Skipped: FOTW (would collect 100-400 flags)")
    else:
        # Subdivisions (states, provinces, etc.)
        print("\n--- Subdivision Flags ---")
        subdivision_collector = SubdivisionFlagCollector(rate_limit_seconds=2.0)
        subdivision_flags = subdivision_collector.collect()
        all_flags.extend(subdivision_flags)
        
        # International organizations
        print("\n--- Organization Flags ---")
        org_collector = OrganizationFlagCollector(rate_limit_seconds=2.0)
        org_flags = org_collector.collect()
        all_flags.extend(org_flags)
        
        # Historical flags
        print("\n--- Historical Flags ---")
        historical_collector = HistoricalFlagCollector(rate_limit_seconds=2.0)
        historical_flags = historical_collector.collect()
        all_flags.extend(historical_flags)
        
        # Phase 2: City flags
        print("\n" + "="*80)
        print("PHASE 2: Collecting city and municipal flags")
        print("="*80)
        
        print("\n--- City Flags ---")
        city_collector = CityFlagCollector(rate_limit_seconds=2.0)
        city_flags = city_collector.collect()
        all_flags.extend(city_flags)
        
        # Phase 3: FOTW extended collection (optional, can be slow)
        print("\n" + "="*80)
        print("PHASE 3: Collecting from FOTW (limited sample)")
        print("="*80)
        
        print("\n--- FOTW Flags ---")
        fotw_collector = FOTWScraper(rate_limit_seconds=3.0)
        fotw_flags = fotw_collector.collect()
        all_flags.extend(fotw_flags)
    
    print("\n" + "="*80)
    print("COLLECTION COMPLETE")
    print("="*80)
    print(f"Total flags collected (before deduplication): {len(all_flags)}")
    
    return all_flags


def save_raw_flags(flags: List[Flag], output_dir: Path):
    """
    Save raw collected flags before deduplication.
    
    Args:
        flags: List of flags
        output_dir: Output directory
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "flags_raw.json"
    
    data = [flag.dict() for flag in flags]
    with output_file.open('w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nSaved raw flags to {output_file}")


def main():
    """Main execution function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Collect flags from multiple sources to build comprehensive database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick test run (~50 flags, ~1-2 minutes)
  uv run scripts/collect_all_flags.py --test
  
  # Full collection (~5000+ flags, 4-12 hours)
  uv run scripts/collect_all_flags.py
        """
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: collect only ~50 flags (existing national flags) in ~1-2 minutes'
    )
    
    args = parser.parse_args()
    
    if args.test:
        print("Starting QUICK TEST collection...")
        print("This will take ~1-2 minutes and collect ~20 flags.\n")
    else:
        print("Starting comprehensive flag data collection...")
        print("This will take several hours to complete.\n")
    
    # Collect all flags
    all_flags = collect_all_flags(test_mode=args.test)
    
    # Save raw collection
    output_dir = Path("backend/data/comprehensive_flags")
    save_raw_flags(all_flags, output_dir)
    
    # Deduplicate
    print("\n" + "="*80)
    print("DEDUPLICATION")
    print("="*80)
    
    deduplicator = FlagDeduplicator(name_similarity_threshold=0.85)
    unique_flags = deduplicator.deduplicate(all_flags)
    
    # Save deduplicated flags
    output_file = output_dir / "flags_deduplicated.json"
    data = [flag.model_dump() for flag in unique_flags]
    with output_file.open('w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nSaved deduplicated flags to {output_file}")
    
    # Save metadata
    metadata = {
        'total_collected': len(all_flags),
        'after_deduplication': len(unique_flags),
        'duplicates_removed': len(all_flags) - len(unique_flags),
        'sources': [
            'Wikipedia (national flags, subdivisions, organizations, historical, cities)',
            'FOTW (Flags of the World)',
        ]
    }
    
    metadata_file = output_dir / "collection_metadata.json"
    with metadata_file.open('w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nSaved metadata to {metadata_file}")
    print("\n" + "="*80)
    print("COLLECTION AND DEDUPLICATION COMPLETE")
    print("="*80)
    print(f"Final flag count: {len(unique_flags)}")
    
    if len(all_flags) < 500:  # Likely test mode
        print("\n" + "="*80)
        print("TEST MODE COMPLETE")
        print("="*80)
        print("You successfully collected a test dataset!")
        print("\nNext steps to test the full pipeline:")
        print("1. Run: uv run scripts/download_and_process.py")
        print("   (This will download ~200 images and generate embeddings, ~5-10 minutes)")
        print("2. Run: uv run scripts/validate_dataset.py")
        print("   (This will validate the dataset)")
        print("\nTo collect the FULL dataset (5000+ flags):")
        print("  uv run scripts/collect_all_flags.py")
        print("  (without the --test flag)")
    else:
        print("\nNext steps:")
        print("1. Run download_and_process.py to download images and generate embeddings")
        print("2. Test with the flag searcher")


if __name__ == "__main__":
    main()

