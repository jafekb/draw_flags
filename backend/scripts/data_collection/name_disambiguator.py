"""
Disambiguate duplicate flag names by extracting variant information from URLs.

This module provides functionality to ensure all flags have unique names by:
1. Detecting flags with duplicate names
2. Extracting variant information from Wikipedia image URLs (dates, descriptive text)
3. Updating names with disambiguating suffixes

Used in the data collection pipeline to ensure all flags are uniquely identifiable.
"""

import re
from collections import defaultdict
from typing import List
from urllib.parse import unquote

from backend.common.flag_data import Flag


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
    filename = decoded_url.split("/")[-1]

    # Remove file extension
    name_part = filename.rsplit(".", 1)[0]

    # Pattern 1: Extract content within parentheses
    # Examples: (1517-1793), (eight pointed star), (1844–1922)
    paren_matches = re.findall(r"\(([^)]+)\)", name_part)
    if paren_matches:
        # Take the last parenthetical (usually the most specific)
        variant = paren_matches[-1]

        # Clean up common patterns
        variant = variant.replace("_", " ")
        variant = variant.strip()

        # If it looks like a good variant, return it
        if len(variant) > 0 and len(variant) < 100:
            return variant

    # Pattern 2: For entries without parentheses, try to extract meaningful parts
    if not filename_only:
        # Look for year patterns in the filename itself
        year_pattern = re.search(r"(\d{4}[-–]\d{4})", name_part)
        if year_pattern:
            return year_pattern.group(1)

        # Look for single year
        year_pattern = re.search(r"(\d{4})", name_part)
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
    filename = decoded_url.split("/")[-1]
    name_part = filename.rsplit(".", 1)[0]

    # Remove common prefixes
    name_part = re.sub(r"^Flag[_\s]of[_\s]", "", name_part, flags=re.IGNORECASE)
    name_part = re.sub(r"^Flag[_\s]", "", name_part, flags=re.IGNORECASE)

    # Replace underscores with spaces
    name_part = name_part.replace("_", " ")

    # If we have something meaningful, return it
    if len(name_part) > 0 and name_part.lower() != base_name.lower():
        # Limit length
        if len(name_part) > 80:
            name_part = name_part[:80] + "..."
        return name_part.strip()

    return ""


def disambiguate_flag_group(flags: List[Flag]) -> List[Flag]:
    """
    Generate unique names for a list of flags that share the same name.

    Args:
        flags: List of Flag objects with duplicate names

    Returns:
        List of Flag objects with updated unique names
    """
    if not flags:
        return []

    if len(flags) == 1:
        return flags

    base_name = flags[0].name
    is_generic_name = base_name.lower() in ["flag", "banner", "ensign"]
    updated_flags = []
    variants_used = set()

    # First pass: try to extract variants from URLs
    flags_with_variants = []
    flags_without_variants = []

    for flag in flags:
        # Make a copy to avoid modifying the original
        flag_copy = flag.model_copy()
        url = flag_copy.wikipedia_image_url

        # Try standard extraction
        variant = extract_variant_from_url(url)

        # For generic names like "Flag", try aggressive extraction
        if not variant and is_generic_name:
            variant = extract_variant_from_filename_aggressive(url, base_name)

        if variant and variant not in variants_used:
            # For generic names like "Flag", replace entirely instead of adding parentheses
            if is_generic_name:
                flag_copy.name = variant
            else:
                flag_copy.name = f"{base_name} ({variant})"
            variants_used.add(variant)
            flags_with_variants.append(flag_copy)
        else:
            flags_without_variants.append(flag_copy)

    # Second pass: for flags without unique variants, use numbering
    # Only add variant numbers if there are 2 or more flags that need numbers
    if len(flags_without_variants) > 0:
        if len(flags_with_variants) > 0:
            # We have some variants - number the rest starting from 2
            for i, flag in enumerate(flags_without_variants, start=2):
                counter = i
                while f"variant {counter}" in variants_used:
                    counter += 1
                if is_generic_name:
                    flag.name = f"{base_name} (variant {counter})"
                else:
                    flag.name = f"{base_name} (variant {counter})"
                variants_used.add(f"variant {counter}")
        else:
            # No variants found - keep first one bare, number the rest
            for i, flag in enumerate(flags_without_variants):
                if i == 0:
                    # Keep the first one with the original name (bare)
                    pass
                else:
                    # Number subsequent ones starting from 2
                    if is_generic_name:
                        flag.name = f"{base_name} (variant {i + 1})"
                    else:
                        flag.name = f"{base_name} (variant {i + 1})"

    updated_flags = flags_with_variants + flags_without_variants
    return updated_flags


def disambiguate_flag_names(flags: List[Flag], verbose: bool = True) -> List[Flag]:
    """
    Disambiguate all duplicate flag names in a list of flags.

    This function:
    1. Groups flags by name
    2. For each group with duplicates, extracts variant info from URLs
    3. Updates flag names with disambiguating suffixes
    4. Returns all flags with unique names

    Args:
        flags: List of Flag objects (may contain duplicates)
        verbose: If True, print progress information

    Returns:
        List of Flag objects with unique names
    """
    if verbose:
        print(f"Checking {len(flags)} flags for duplicate names...")

    # Group flags by name
    name_groups = defaultdict(list)
    for flag in flags:
        name_groups[flag.name].append(flag)

    # Find duplicates
    duplicate_names = {
        name: flags_list for name, flags_list in name_groups.items() if len(flags_list) > 1
    }

    if verbose:
        print(f"Found {len(duplicate_names)} flag names with duplicates")
        print(
            f"Total duplicate entries: {sum(len(flags_list) for flags_list in duplicate_names.values())}"
        )

    if not duplicate_names:
        if verbose:
            print("All flag names are already unique!")
        return flags

    # Sort by number of duplicates (descending) for better logging
    sorted_duplicates = sorted(duplicate_names.items(), key=lambda x: len(x[1]), reverse=True)

    if verbose:
        print("\nTop duplicate flag names:")
        for name, flags_list in sorted_duplicates[:10]:
            print(f"  {len(flags_list):3d} - {name}")

    # Process duplicates
    updated_flags = []
    changes_made = 0

    for name, flags_list in sorted_duplicates:
        if verbose:
            print(f"\nProcessing: {name} ({len(flags_list)} duplicates)")

        # Store original names before processing
        original_names = [flag.name for flag in flags_list]

        updated_group = disambiguate_flag_group(flags_list)

        # Show changes
        if verbose:
            for orig_name, updated_flag in zip(original_names, updated_group):
                if orig_name != updated_flag.name:
                    print(f"  '{orig_name}' -> '{updated_flag.name}'")
                    print(f"    URL: {updated_flag.wikipedia_image_url}")
                    changes_made += 1
        else:
            # Count changes even if not verbose
            for orig_name, updated_flag in zip(original_names, updated_group):
                if orig_name != updated_flag.name:
                    changes_made += 1

        updated_flags.extend(updated_group)

    # Add flags that don't have duplicates (unchanged)
    for name, flags_list in name_groups.items():
        if len(flags_list) == 1:
            updated_flags.extend(flags_list)

    if verbose:
        print("\nDisambiguation complete:")
        print(f"  Total changes: {changes_made}")
        print(f"  Final flag count: {len(updated_flags)}")
        print(
            f"  All names unique: {len(set(f.name for f in updated_flags)) == len(updated_flags)}"
        )

    return updated_flags
