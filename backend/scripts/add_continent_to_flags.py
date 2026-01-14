"""
Migration script to add continent information to existing flag data.
This script reads flags.json, adds continent field based on country mapping,
and writes the updated data back.
"""

import json
from pathlib import Path
from typing import Optional

# Comprehensive country to continent mapping
COUNTRY_TO_CONTINENT = {
    # Africa
    "Algeria": "Africa",
    "Angola": "Africa",
    "Benin": "Africa",
    "Botswana": "Africa",
    "Burkina Faso": "Africa",
    "Burundi": "Africa",
    "Cameroon": "Africa",
    "Cape Verde": "Africa",
    "Central African Republic": "Africa",
    "Chad": "Africa",
    "Comoros": "Africa",
    "Congo": "Africa",
    "Democratic Republic of the Congo": "Africa",
    "Djibouti": "Africa",
    "Egypt": "Africa",
    "Equatorial Guinea": "Africa",
    "Eritrea": "Africa",
    "Eswatini": "Africa",
    "Ethiopia": "Africa",
    "Gabon": "Africa",
    "Gambia": "Africa",
    "Ghana": "Africa",
    "Guinea": "Africa",
    "Guinea-Bissau": "Africa",
    "Ivory Coast": "Africa",
    "Kenya": "Africa",
    "Lesotho": "Africa",
    "Liberia": "Africa",
    "Libya": "Africa",
    "Madagascar": "Africa",
    "Malawi": "Africa",
    "Mali": "Africa",
    "Mauritania": "Africa",
    "Mauritius": "Africa",
    "Morocco": "Africa",
    "Mozambique": "Africa",
    "Namibia": "Africa",
    "Niger": "Africa",
    "Nigeria": "Africa",
    "Rwanda": "Africa",
    "Sao Tome and Principe": "Africa",
    "Senegal": "Africa",
    "Seychelles": "Africa",
    "Sierra Leone": "Africa",
    "Somalia": "Africa",
    "South Africa": "Africa",
    "South Sudan": "Africa",
    "Sudan": "Africa",
    "Tanzania": "Africa",
    "Togo": "Africa",
    "Tunisia": "Africa",
    "Uganda": "Africa",
    "Zambia": "Africa",
    "Zimbabwe": "Africa",
    # Asia
    "Afghanistan": "Asia",
    "Armenia": "Asia",
    "Azerbaijan": "Asia",
    "Bahrain": "Asia",
    "Bangladesh": "Asia",
    "Bhutan": "Asia",
    "Brunei": "Asia",
    "Cambodia": "Asia",
    "China": "Asia",
    "Cyprus": "Asia",
    "Georgia": "Asia",
    "India": "Asia",
    "Indonesia": "Asia",
    "Iran": "Asia",
    "Iraq": "Asia",
    "Israel": "Asia",
    "Japan": "Asia",
    "Jordan": "Asia",
    "Kazakhstan": "Asia",
    "Kuwait": "Asia",
    "Kyrgyzstan": "Asia",
    "Laos": "Asia",
    "Lebanon": "Asia",
    "Malaysia": "Asia",
    "Maldives": "Asia",
    "Mongolia": "Asia",
    "Myanmar": "Asia",
    "Nepal": "Asia",
    "North Korea": "Asia",
    "Oman": "Asia",
    "Pakistan": "Asia",
    "Palestine": "Asia",
    "Philippines": "Asia",
    "Qatar": "Asia",
    "Saudi Arabia": "Asia",
    "Singapore": "Asia",
    "South Korea": "Asia",
    "Sri Lanka": "Asia",
    "Syria": "Asia",
    "Taiwan": "Asia",
    "Tajikistan": "Asia",
    "Thailand": "Asia",
    "Timor-Leste": "Asia",
    "Turkey": "Asia",
    "Turkmenistan": "Asia",
    "United Arab Emirates": "Asia",
    "Uzbekistan": "Asia",
    "Vietnam": "Asia",
    "Yemen": "Asia",
    # Europe
    "Albania": "Europe",
    "Andorra": "Europe",
    "Austria": "Europe",
    "Belarus": "Europe",
    "Belgium": "Europe",
    "Bosnia and Herzegovina": "Europe",
    "Bulgaria": "Europe",
    "Croatia": "Europe",
    "Czech Republic": "Europe",
    "Denmark": "Europe",
    "Estonia": "Europe",
    "Finland": "Europe",
    "France": "Europe",
    "Germany": "Europe",
    "Greece": "Europe",
    "Hungary": "Europe",
    "Iceland": "Europe",
    "Ireland": "Europe",
    "Italy": "Europe",
    "Kosovo": "Europe",
    "Latvia": "Europe",
    "Liechtenstein": "Europe",
    "Lithuania": "Europe",
    "Luxembourg": "Europe",
    "Malta": "Europe",
    "Moldova": "Europe",
    "Monaco": "Europe",
    "Montenegro": "Europe",
    "Netherlands": "Europe",
    "North Macedonia": "Europe",
    "Norway": "Europe",
    "Poland": "Europe",
    "Portugal": "Europe",
    "Romania": "Europe",
    "Russia": "Europe",
    "San Marino": "Europe",
    "Serbia": "Europe",
    "Slovakia": "Europe",
    "Slovenia": "Europe",
    "Spain": "Europe",
    "Sweden": "Europe",
    "Switzerland": "Europe",
    "Ukraine": "Europe",
    "United Kingdom": "Europe",
    "Vatican City": "Europe",
    # North America
    "Antigua and Barbuda": "North America",
    "Bahamas": "North America",
    "Barbados": "North America",
    "Belize": "North America",
    "Canada": "North America",
    "Costa Rica": "North America",
    "Cuba": "North America",
    "Dominica": "North America",
    "Dominican Republic": "North America",
    "El Salvador": "North America",
    "Grenada": "North America",
    "Guatemala": "North America",
    "Haiti": "North America",
    "Honduras": "North America",
    "Jamaica": "North America",
    "Mexico": "North America",
    "Nicaragua": "North America",
    "Panama": "North America",
    "Saint Kitts and Nevis": "North America",
    "Saint Lucia": "North America",
    "Saint Vincent and the Grenadines": "North America",
    "Trinidad and Tobago": "North America",
    "United States": "North America",
    # South America
    "Argentina": "South America",
    "Bolivia": "South America",
    "Brazil": "South America",
    "Chile": "South America",
    "Colombia": "South America",
    "Ecuador": "South America",
    "Guyana": "South America",
    "Paraguay": "South America",
    "Peru": "South America",
    "Suriname": "South America",
    "Uruguay": "South America",
    "Venezuela": "South America",
    # Oceania
    "Australia": "Oceania",
    "Fiji": "Oceania",
    "Kiribati": "Oceania",
    "Marshall Islands": "Oceania",
    "Micronesia": "Oceania",
    "Nauru": "Oceania",
    "New Zealand": "Oceania",
    "Palau": "Oceania",
    "Papua New Guinea": "Oceania",
    "Samoa": "Oceania",
    "Solomon Islands": "Oceania",
    "Tonga": "Oceania",
    "Tuvalu": "Oceania",
    "Vanuatu": "Oceania",
}


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
        return COUNTRY_TO_CONTINENT.get(parent_country)

    # For national flags, try to match the flag name to a country
    if flag.get("category") == "national":
        # Try direct lookup by name
        flag_name = flag["name"]

        # Check if the name directly matches a country
        if flag_name in COUNTRY_TO_CONTINENT:
            return COUNTRY_TO_CONTINENT[flag_name]

        # Try to extract country name from patterns like "Flag of X"
        if flag_name.startswith("Flag of "):
            country_name = flag_name.replace("Flag of ", "").strip()
            if country_name in COUNTRY_TO_CONTINENT:
                return COUNTRY_TO_CONTINENT[country_name]

        # Direct name match
        for country, continent in COUNTRY_TO_CONTINENT.items():
            if country.lower() in flag_name.lower():
                return continent

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

    print("\nMigration complete!")
    print(f"  Flags with continent: {continents_added}")
    print(f"  Flags without continent: {continents_missing}")

    # Show continent distribution
    continent_counts = {}
    for flag in flags:
        continent = flag.get("continent")
        if continent:
            continent_counts[continent] = continent_counts.get(continent, 0) + 1

    print("\nContinent distribution:")
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
