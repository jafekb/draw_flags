"""
Migration script to add continent information to existing flag data.
This script reads flags.json, adds continent field based on country mapping,
and writes the updated data back.

Uses country_converter package for accurate country-to-continent mapping.
Install with: pip install country_converter
"""

import json
from pathlib import Path
from typing import Optional

try:
    import country_converter as coco

    cc = coco.CountryConverter()
    COUNTRY_CONVERTER_AVAILABLE = True
except ImportError:
    print("Warning: country_converter not installed. Using fallback mapping.")
    print("Install with: pip install country_converter")
    COUNTRY_CONVERTER_AVAILABLE = False


def get_continent_for_flag(flag: dict) -> Optional[str]:
    """
    Determine the continent for a flag based on its metadata.

    Args:
        flag: Dictionary containing flag data

    Returns:
        Continent name or None if cannot be determined
    """
    # For subdivisions and cities, use the parent country
    if flag.get("country"):
        parent_country = flag["country"]
        if COUNTRY_CONVERTER_AVAILABLE:
            try:
                continent = cc.convert(names=parent_country, to="continent")
                # country_converter returns the country name if not found
                # Only return if it looks like a continent
                if continent in [
                    "Africa",
                    "Asia",
                    "Europe",
                    "North America",
                    "South America",
                    "Oceania",
                    "Antarctica",
                ]:
                    return continent
            except Exception:
                pass
        return None

    # For national flags, try to match the flag name to a country
    if flag.get("category") == "national":
        flag_name = flag["name"]

        # Try direct lookup by name
        if COUNTRY_CONVERTER_AVAILABLE:
            try:
                continent = cc.convert(names=flag_name, to="continent")
                if continent in [
                    "Africa",
                    "Asia",
                    "Europe",
                    "North America",
                    "South America",
                    "Oceania",
                    "Antarctica",
                ]:
                    return continent
            except Exception:
                pass

    # Organizations and historical flags don't have a specific continent
    if flag.get("category") in ["organization", "historical"]:
        return None

    return None


def migrate_flags(input_file: Path, output_file: Path):
    """
    Read flags from input file, add continent information, and write to output file.

    Args:
        input_file: Path to existing flags.json
        output_file: Path to write updated flags.json
    """
    print(f"Reading flags from {input_file}...")
    with input_file.open() as f:
        data = json.load(f)

    flags = data["flags"]
    print(f"Found {len(flags)} flags")

    # Add continent to each flag
    continents_added = 0
    continents_missing = 0

    for flag in flags:
        continent = get_continent_for_flag(flag)
        flag["continent"] = continent

        if continent:
            continents_added += 1
        else:
            continents_missing += 1

    # Write updated data
    print(f"\nWriting updated flags to {output_file}...")
    with output_file.open("w") as f:
        json.dump(data, f, indent=1)

    print(f"\nMigration complete!")
    print(f"  Flags with continent: {continents_added}")
    print(f"  Flags without continent: {continents_missing}")

    # Show continent distribution
    continent_counts = {}
    for flag in flags:
        continent = flag.get("continent")
        if continent:
            continent_counts[continent] = continent_counts.get(continent, 0) + 1

    print(f"\nContinent distribution:")
    for continent in sorted(continent_counts.keys()):
        print(f"  {continent}: {continent_counts[continent]} flags")


if __name__ == "__main__":
    # Define paths
    data_dir = Path("backend/data/comprehensive_flags_3")
    input_file = data_dir / "flags.json"
    output_file = data_dir / "flags.json"  # Overwrite the same file

    # Create backup first
    backup_file = data_dir / "flags_backup.json"
    print(f"Creating backup at {backup_file}...")
    import shutil

    shutil.copy(input_file, backup_file)

    # Run migration
    migrate_flags(input_file, output_file)

    print(f"\nBackup saved at {backup_file}")
    print("If everything looks good, you can delete the backup file.")
