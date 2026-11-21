"""
Standalone script to fix duplicate flag names in existing datasets.

This script can be used to retroactively fix duplicate names in existing
flags.json files. For new data collection, use collect_all_flags.py which
includes name disambiguation as part of the pipeline.

This script:
1. Loads flags from an existing JSON file
2. Identifies all flags with duplicate names
3. Extracts variant information from wikipedia_image_url (date ranges, descriptive text)
4. Updates the name field with disambiguating suffixes
5. Preserves all other flag metadata
"""

import json
from pathlib import Path
from typing import List

from backend.common.flag_data import Flag
from backend.scripts.data_collection.name_disambiguator import disambiguate_flag_names


def load_flags_from_json(input_file: Path) -> tuple[List[Flag], dict, bool]:
    """
    Load flags from JSON file, handling both formats.

    Returns:
        Tuple of (flags_list, extra_data, has_wrapper)
    """
    with input_file.open(encoding="utf-8") as f:
        data = json.load(f)

    # Handle both dict structure (with 'flags' key) and direct list
    if isinstance(data, dict) and "flags" in data:
        flags_data = data["flags"]
        has_wrapper = True
        extra_data = {k: v for k, v in data.items() if k != "flags"}
    else:
        flags_data = data
        has_wrapper = False
        extra_data = {}

    # Convert to Flag objects
    flags = [Flag(**flag_dict) for flag_dict in flags_data]

    return flags, extra_data, has_wrapper


def save_flags_to_json(
    flags: List[Flag], output_file: Path, extra_data: dict, *, has_wrapper: bool
):
    """
    Save flags to JSON file, preserving the original format.

    Args:
        flags: List of Flag objects
        output_file: Output file path
        extra_data: Additional data from the original file (e.g., embeddings_filename)
        has_wrapper: Whether to wrap flags in a dict with 'flags' key
    """
    # Convert flags to dicts
    flags_data = [flag.model_dump() for flag in flags]

    # Preserve the original structure
    output_data = {"flags": flags_data, **extra_data} if has_wrapper else flags_data

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=1, ensure_ascii=False)


def fix_duplicate_names(input_file: Path, output_file: Path, *, dry_run: bool = False):
    """
    Main function to fix duplicate flag names in an existing dataset.

    Args:
        input_file: Path to input flags.json
        output_file: Path to output flags.json
        dry_run: If True, only print what would be changed without saving
    """
    print(f"Reading flags from {input_file}")
    flags, extra_data, has_wrapper = load_flags_from_json(input_file)

    print(f"Total flags: {len(flags)}")

    # Use the shared disambiguation logic
    if dry_run:
        print("\n[DRY RUN MODE - No changes will be saved]")

    updated_flags = disambiguate_flag_names(flags, verbose=True)

    if not dry_run:
        # Save updated flags
        print(f"\nSaving updated flags to {output_file}")
        save_flags_to_json(updated_flags, output_file, extra_data, has_wrapper=has_wrapper)
        print("Done!")
    else:
        print("\n[DRY RUN] No changes saved. Run without --dry-run to apply changes.")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fix duplicate flag names in existing datasets")
    parser.add_argument(
        "--input",
        type=str,
        default="backend/data/all_flags/flags.json",
        help="Input flags.json file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="backend/data/all_flags/flags.json",
        help="Output flags.json file",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be changed without saving"
    )

    args = parser.parse_args()

    input_file = Path(args.input)
    output_file = Path(args.output)

    if not input_file.exists():
        print(f"Error: Input file {input_file} does not exist")
        return

    fix_duplicate_names(input_file, output_file, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
