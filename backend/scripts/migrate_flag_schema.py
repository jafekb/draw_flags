"""
Migration script to transform flags from old schema to new schema.

Old schema: name, wikipedia_page, wikipedia_url, wikipedia_image_url, local_image_link, verification_method, score
New schema: name, wikipedia_page, wikipedia_url, wikipedia_image_url, category, entity_type, country, adoption_year, tags
"""

import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Known country list for pattern matching (from NationalFlagCollector)
COUNTRIES = [
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda",
    "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain",
    "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia",
    "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso",
    "Burundi", "Cabo Verde", "Cambodia", "Cameroon", "Canada", "Central African Republic",
    "Chad", "Chile", "China", "Colombia", "Comoros", "Congo", "Costa Rica", "Croatia",
    "Cuba", "Cyprus", "Czech Republic", "Czechia", "Denmark", "Djibouti", "Dominica",
    "Dominican Republic", "East Timor", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea",
    "Eritrea", "Estonia", "Eswatini", "Ethiopia", "Fiji", "Finland", "France", "Gabon",
    "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea",
    "Guinea-Bissau", "Guyana", "Haiti", "Honduras", "Hungary", "Iceland", "India", "Indonesia",
    "Iran", "Iraq", "Ireland", "Israel", "Italy", "Ivory Coast", "Jamaica", "Japan", "Jordan",
    "Kazakhstan", "Kenya", "Kiribati", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon",
    "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg", "Madagascar",
    "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania",
    "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro",
    "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand",
    "Nicaragua", "Niger", "Nigeria", "North Korea", "North Macedonia", "Norway", "Oman",
    "Pakistan", "Palau", "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru",
    "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russia", "Rwanda", "Saint Kitts and Nevis",
    "Saint Lucia", "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe",
    "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia",
    "Slovenia", "Solomon Islands", "Somalia", "South Africa", "South Korea", "South Sudan", "Spain",
    "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan",
    "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia",
    "Turkey", "Turkmenistan", "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom",
    "United States", "Uruguay", "Uzbekistan", "Vanuatu", "Vatican City", "Venezuela", "Vietnam",
    "Yemen", "Zambia", "Zimbabwe"
]

# US states for pattern matching
US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"
]


def infer_category_and_entity_type(flag: Dict) -> Tuple[str, str]:
    """
    Infer the category and entity_type based on flag name and wikipedia_page.
    
    Returns:
        Tuple of (category, entity_type)
    """
    name = flag["name"]
    page = flag["wikipedia_page"]
    page_lower = page.lower()
    name_lower = name.lower()
    
    # Check for historical flags (do this early to catch historical variants)
    if any(keyword in name_lower or keyword in page_lower for keyword in [
        "historical", "former", "colonial", "proposal", "ensign", "naval", "governor",
        "1900", "1800", "1700", "19th", "18th", "17th", "–", "c. ", "navy"
    ]):
        return ("historical", "historical")
    
    # Check for organizations
    if any(keyword in name_lower or keyword in page_lower for keyword in [
        "united nations", "european union", "nato", "african union", "asean",
        "organization", "organisation", "commonwealth", "union", "federation",
        "league", "association", "olympics", "olympic"
    ]):
        return ("organization", "organization")
    
    # Check for US states (including disambiguation pages)
    if "u.s._state" in page_lower or "u.s. state" in page_lower:
        return ("subdivision", "state")
    
    # Check for US states by name
    name_clean = name.replace("Flag of ", "").replace("flag of ", "")
    if name_clean in US_STATES:
        return ("subdivision", "state")
    
    # Check for provinces/territories/states in general
    if any(keyword in page_lower for keyword in ["province", "territory", "autonomous"]):
        entity_type = "province" if "province" in page_lower else "territory"
        return ("subdivision", entity_type)
    
    # Check for states (check for page patterns before country check)
    if "state" in page_lower and not any(x in page_lower for x in ["united_states", "sovereign"]):
        return ("subdivision", "state")
    
    # Cities - look for city indicators or capital cities
    city_indicators = ["city", "capital", "municipality", "buenos_aires", "lima", "bogotá",
                       "santiago", "caracas", "quito", "la_paz", "asunción", "georgetown",
                       "guadalajara", "monterrey", "guatemala_city", "san_salvador", "tegucigalpa",
                       "managua", "san_josé", "panama_city", "havana", "são_paulo", "rio_de_janeiro",
                       "paris", "london", "berlin", "rome", "madrid", "tokyo", "beijing", "moscow"]
    
    if any(indicator in page_lower for indicator in city_indicators):
        return ("city", "city")
    
    # Check if name contains comma (often cities)
    if "," in name and not any(keyword in name_lower for keyword in ["proposal", "design", "naval"]):
        return ("city", "city")
    
    # Check if it's a national flag (country name matches) - do this later after subdivision checks
    if name_clean in COUNTRIES or page.replace("_", " ") in COUNTRIES:
        return ("national", "country")
    
    # Special handling for country disambiguation like "Georgia_(country)"
    if "(country)" in page_lower:
        return ("national", "country")
    
    # Default to subdivision for anything else that's not clearly categorized
    return ("subdivision", "state")


def extract_country(flag: Dict, category: str) -> Optional[str]:
    """
    Extract parent country for subdivisions and cities.
    """
    if category == "national":
        return None
    
    name = flag["name"]
    page = flag["wikipedia_page"]
    page_lower = page.lower()
    
    # For US states (check Wikipedia page first)
    if "u.s._state" in page_lower or "u.s. state" in page_lower:
        return "United States"
    
    # For US states by name
    name_clean = name.replace("Flag of ", "").replace("flag of ", "")
    if name_clean in US_STATES or any(state in name for state in US_STATES):
        return "United States"
    
    # For cities with comma notation
    if "," in name:
        parts = name.split(",")
        if len(parts) >= 2:
            country_part = parts[-1].strip()
            # Clean up common prefixes
            country_part = country_part.replace("Flag of ", "")
            return country_part
    
    # For subdivisions, try to extract from wikipedia_page
    # Example: "California" -> United States, "Ontario" -> Canada
    common_subdivisions = {
        "California": "United States", "Texas": "United States", "Florida": "United States",
        "New York": "United States", "Ontario": "Canada", "Quebec": "Canada",
        "British Columbia": "Canada", "Bavaria": "Germany", "Saxony": "Germany",
    }
    
    page_clean = page.replace("_", " ")
    for subdivision, country in common_subdivisions.items():
        if subdivision in page_clean or subdivision in name:
            return country
    
    # Try to extract country from Wikipedia page patterns
    # Many subdivision pages have format like "State_name_(Country)"
    if "(" in page and ")" in page:
        country_match = re.search(r'\(([^)]+)\)', page)
        if country_match:
            potential_country = country_match.group(1).replace("_", " ")
            if potential_country in COUNTRIES:
                return potential_country
    
    return None


def extract_adoption_year(flag: Dict) -> Optional[int]:
    """
    Extract adoption year from flag name if present.
    Best effort - looks for year patterns in the name.
    """
    name = flag["name"]
    
    # Look for year patterns like "1776", "adopted 1960", etc.
    year_patterns = [
        r'\b(1[6-9]\d{2}|20[0-2]\d)\b',  # Years 1600-2029
        r'adopted\s+(\d{4})',
        r'since\s+(\d{4})',
    ]
    
    for pattern in year_patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            year = int(match.group(1) if 'adopted' in pattern or 'since' in pattern else match.group(0))
            if 1600 <= year <= 2030:
                return year
    
    return None


def generate_tags(flag: Dict, category: str, entity_type: str, country: Optional[str]) -> List[str]:
    """
    Generate searchable tags for a flag.
    """
    tags = []
    
    # Add category and entity type
    tags.append(category)
    if entity_type != category:
        tags.append(entity_type)
    
    # Add country if present
    if country:
        tags.append(country.lower())
    
    # Parse name for keywords
    name = flag["name"].lower()
    name_clean = name.replace("flag of ", "").replace("the ", "")
    
    # Split on common delimiters and add significant words
    words = re.split(r'[,\s\-]+', name_clean)
    for word in words:
        word = word.strip()
        # Skip common/short words
        if len(word) > 2 and word not in ['flag', 'the', 'and', 'for']:
            tags.append(word)
    
    # Add special keywords
    if "united states" in name or country == "United States":
        tags.extend(["usa", "us", "america", "american"])
    if "united kingdom" in name or country == "United Kingdom":
        tags.extend(["uk", "britain", "british"])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_tags = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)
    
    return unique_tags


def migrate_flag(flag: Dict) -> Dict:
    """
    Migrate a single flag from old schema to new schema.
    """
    # Infer new fields
    category, entity_type = infer_category_and_entity_type(flag)
    country = extract_country(flag, category)
    adoption_year = extract_adoption_year(flag)
    tags = generate_tags(flag, category, entity_type, country)
    
    # Create new flag dict
    new_flag = {
        "name": flag["name"],
        "wikipedia_page": flag["wikipedia_page"],
        "wikipedia_url": flag["wikipedia_url"],
        "wikipedia_image_url": flag["wikipedia_image_url"],
        "category": category,
        "entity_type": entity_type,
        "country": country,
        "adoption_year": adoption_year,
        "tags": tags,
    }
    
    return new_flag


def migrate_dataset(input_dir: Path, output_dir: Path):
    """
    Migrate entire dataset from old schema to new schema.
    """
    print(f"Migrating dataset from {input_dir} to {output_dir}")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Read input flags.json
    input_file = input_dir / "flags.json"
    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    old_flags = data["flags"]
    print(f"Found {len(old_flags)} flags to migrate")
    
    # Migrate each flag
    new_flags = []
    category_counts = {}
    
    for i, old_flag in enumerate(old_flags):
        if (i + 1) % 500 == 0:
            print(f"  Migrated {i + 1}/{len(old_flags)} flags...")
        
        new_flag = migrate_flag(old_flag)
        new_flags.append(new_flag)
        
        # Track category counts
        category = new_flag["category"]
        category_counts[category] = category_counts.get(category, 0) + 1
    
    print(f"Migration complete!")
    print(f"\nCategory breakdown:")
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count} flags")
    
    # Write output flags.json
    output_file = output_dir / "flags.json"
    print(f"\nWriting {output_file}...")
    output_data = {
        "flags": new_flags,
        "embeddings_filename": data.get("embeddings_filename", "embeddings.npy")
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=1, ensure_ascii=False)
    
    # Copy embeddings.npy
    input_embeddings = input_dir / "embeddings.npy"
    output_embeddings = output_dir / "embeddings.npy"
    if input_embeddings.exists():
        print(f"Copying {input_embeddings} to {output_embeddings}...")
        shutil.copy2(input_embeddings, output_embeddings)
    
    # Copy other metadata files
    for filename in ["collection_metadata.json", "sources.txt"]:
        input_file = input_dir / filename
        output_file = output_dir / filename
        if input_file.exists():
            print(f"Copying {filename}...")
            shutil.copy2(input_file, output_file)
    
    print(f"\nMigration complete! Output written to {output_dir}")
    
    # Print some sample flags
    print(f"\nSample migrated flags:")
    for i in [0, 200, -1]:
        flag = new_flags[i]
        print(f"\n{flag['name']}:")
        print(f"  Category: {flag['category']}")
        print(f"  Entity Type: {flag['entity_type']}")
        print(f"  Country: {flag['country']}")
        print(f"  Tags: {', '.join(flag['tags'][:5])}")


def main():
    """Main entry point."""
    # Define paths
    project_root = Path(__file__).parent.parent.parent
    input_dir = project_root / "backend" / "data" / "comprehensive_flags_2"
    output_dir = project_root / "backend" / "data" / "comprehensive_flags_3"
    
    # Run migration
    migrate_dataset(input_dir, output_dir)


if __name__ == "__main__":
    main()

