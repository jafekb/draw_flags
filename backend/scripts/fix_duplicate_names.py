"""
Script to fix duplicate flag names by extracting variant information from Wikipedia image URLs.

This script:
1. Identifies all flags with duplicate names
2. Extracts variant information from wikipedia_image_url (date ranges, descriptive text)
3. Updates the name field with disambiguating suffixes
4. Preserves all other flag metadata
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List
from urllib.parse import unquote


def extract_variant_from_url(url: str, filename_only: bool = False) -> str:
    """
    Extract variant information from Wikipedia image URL.
    
    Args:
        url: Wikipedia image URL
        filename_only: If True, only parse the filename, not path components
        
    Returns:
        Variant string (empty if none found)
    """
    # URL decode first
    decoded_url = unquote(url)
    
    # Extract filename from URL
    filename = decoded_url.split('/')[-1]
    
    # Remove file extension
    name_part = filename.rsplit('.', 1)[0]
    
    # Pattern 1: Extract content within parentheses
    # Examples: (1517-1793), (eight pointed star), (1844–1922)
    paren_matches = re.findall(r'\(([^)]+)\)', name_part)
    if paren_matches:
        # Take the last parenthetical (usually the most specific)
        variant = paren_matches[-1]
        
        # Clean up common patterns
        variant = variant.replace('_', ' ')
        variant = variant.strip()
        
        # If it looks like a good variant, return it
        if len(variant) > 0 and len(variant) < 100:
            return variant
    
    # Pattern 2: For entries without parentheses, try to extract meaningful parts
    if not filename_only:
        # Look for year patterns in the filename itself
        year_pattern = re.search(r'(\d{4}[-–]\d{4})', name_part)
        if year_pattern:
            return year_pattern.group(1)
        
        # Look for single year
        year_pattern = re.search(r'(\d{4})', name_part)
        if year_pattern:
            return year_pattern.group(1)
    
    return ""


def extract_variant_from_filename_aggressive(url: str, base_name: str) -> str:
    """
    More aggressive extraction for cases like "Flag" where we need any identifying info.
    
    Args:
        url: Wikipedia image URL
        base_name: The base flag name (e.g., "Flag")
        
    Returns:
        Variant string extracted from filename
    """
    decoded_url = unquote(url)
    filename = decoded_url.split('/')[-1]
    name_part = filename.rsplit('.', 1)[0]
    
    # Remove common prefixes
    name_part = re.sub(r'^Flag[_\s]of[_\s]', '', name_part, flags=re.IGNORECASE)
    name_part = re.sub(r'^Flag[_\s]', '', name_part, flags=re.IGNORECASE)
    
    # Replace underscores with spaces
    name_part = name_part.replace('_', ' ')
    
    # If we have something meaningful, return it
    if len(name_part) > 0 and name_part.lower() != base_name.lower():
        # Limit length
        if len(name_part) > 80:
            name_part = name_part[:80] + '...'
        return name_part.strip()
    
    return ""


def generate_unique_names(flags_with_same_name: List[Dict]) -> List[Dict]:
    """
    Generate unique names for a list of flags that share the same name.
    
    Args:
        flags_with_same_name: List of flag dicts with duplicate names
        
    Returns:
        List of flag dicts with updated names
    """
    base_name = flags_with_same_name[0]['name']
    updated_flags = []
    variants_used = set()
    
    # First pass: try to extract variants from URLs
    flags_with_variants = []
    flags_without_variants = []
    
    for flag in flags_with_same_name:
        # Make a copy to avoid modifying the original
        flag = flag.copy()
        url = flag['wikipedia_image_url']
        
        # Try standard extraction
        variant = extract_variant_from_url(url)
        
        # For generic names like "Flag", try aggressive extraction
        if not variant and base_name.lower() in ['flag', 'banner', 'ensign']:
            variant = extract_variant_from_filename_aggressive(url, base_name)
        
        if variant and variant not in variants_used:
            flag['name'] = f"{base_name} ({variant})"
            variants_used.add(variant)
            flags_with_variants.append(flag)
        else:
            flags_without_variants.append(flag)
    
    # Second pass: for flags without unique variants, use numbering
    if len(flags_without_variants) > 0:
        # If we found some variants, number the rest continuing from where variants left off
        if len(flags_with_variants) > 0:
            for i, flag in enumerate(flags_without_variants, start=1):
                # Try to find a unique number
                counter = i
                while f"variant {counter}" in variants_used:
                    counter += 1
                flag['name'] = f"{base_name} (variant {counter})"
                variants_used.add(f"variant {counter}")
        else:
            # No variants found for any, just number them all
            for i, flag in enumerate(flags_without_variants, start=1):
                flag['name'] = f"{base_name} (variant {i})"
    
    updated_flags = flags_with_variants + flags_without_variants
    return updated_flags


def fix_duplicate_names(input_file: Path, output_file: Path, dry_run: bool = False):
    """
    Main function to fix duplicate flag names.
    
    Args:
        input_file: Path to input flags.json
        output_file: Path to output flags.json
        dry_run: If True, only print what would be changed without saving
    """
    print(f"Reading flags from {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle both dict structure (with 'flags' key) and direct list
    if isinstance(data, dict) and 'flags' in data:
        flags = data['flags']
        has_wrapper = True
        embeddings_filename = data.get('embeddings_filename')
    else:
        flags = data
        has_wrapper = False
        embeddings_filename = None
    
    print(f"Total flags: {len(flags)}")
    
    # Group flags by name
    name_groups = defaultdict(list)
    for flag in flags:
        name_groups[flag['name']].append(flag)
    
    # Find duplicates
    duplicate_names = {name: flags_list for name, flags_list in name_groups.items() if len(flags_list) > 1}
    
    print(f"\nFound {len(duplicate_names)} flag names with duplicates")
    print(f"Total duplicate entries: {sum(len(flags_list) for flags_list in duplicate_names.values())}")
    
    # Sort by number of duplicates (descending)
    sorted_duplicates = sorted(duplicate_names.items(), key=lambda x: len(x[1]), reverse=True)
    
    print("\nTop duplicate flag names:")
    for name, flags_list in sorted_duplicates[:10]:
        print(f"  {len(flags_list):3d} - {name}")
    
    # Process duplicates
    updated_flags = []
    changes_made = 0
    
    for name, flags_list in sorted_duplicates:
        print(f"\nProcessing: {name} ({len(flags_list)} duplicates)")
        
        # Store original names before processing
        original_names = [flag['name'] for flag in flags_list]
        
        updated_group = generate_unique_names(flags_list)
        
        # Show changes
        for orig_name, updated_flag in zip(original_names, updated_group):
            if orig_name != updated_flag['name']:
                print(f"  '{orig_name}' -> '{updated_flag['name']}'")
                print(f"    URL: {updated_flag['wikipedia_image_url']}")
                changes_made += 1
        
        updated_flags.extend(updated_group)
    
    # Add flags that don't have duplicates (unchanged)
    for name, flags_list in name_groups.items():
        if len(flags_list) == 1:
            updated_flags.extend(flags_list)
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Total changes: {changes_made}")
    print(f"Final flag count: {len(updated_flags)}")
    
    if not dry_run:
        # Save updated flags
        print(f"\nSaving updated flags to {output_file}")
        
        # Preserve the original structure
        if has_wrapper:
            output_data = {
                'flags': updated_flags,
                'embeddings_filename': embeddings_filename
            }
        else:
            output_data = updated_flags
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=1, ensure_ascii=False)
        print("Done!")
    else:
        print("\n[DRY RUN] No changes saved. Run without --dry-run to apply changes.")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix duplicate flag names')
    parser.add_argument('--input', type=str, 
                       default='backend/data/comprehensive_flags_3/flags.json',
                       help='Input flags.json file')
    parser.add_argument('--output', type=str,
                       default='backend/data/comprehensive_flags_3/flags.json',
                       help='Output flags.json file')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be changed without saving')
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    output_file = Path(args.output)
    
    if not input_file.exists():
        print(f"Error: Input file {input_file} does not exist")
        return
    
    fix_duplicate_names(input_file, output_file, dry_run=args.dry_run)


if __name__ == '__main__':
    main()

