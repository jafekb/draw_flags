# Flag Schema Migration (v2 → v3)

## Overview

The flag database schema has been refactored to improve searchability and provide more useful metadata for users. This document describes the changes made in the migration from `comprehensive_flags_2` to `all_flags`.

## Schema Changes

### Fields Removed

The following internal scraper fields have been removed as they were not useful for end users:

- `local_image_link` - Always empty in stored data
- `verification_method` - Internal scraper detail (always "table")
- `score` - Internal scraper detail (always 1.0)

### Fields Added

New metadata fields have been added to enhance searchability and organization:

#### `category` (string, required)
User-friendly category indicating the type of flag.

**Allowed values:**
- `national` - National/country flags
- `subdivision` - State, province, or territory flags
- `city` - City and municipal flags
- `organization` - International organizations, unions, etc.
- `historical` - Historical flags, former countries, naval ensigns
- `fotw` - Flags from the Flags of the World database

**Distribution in current dataset:**
- national: 237 flags
- subdivision: 1,890 flags
- city: 470 flags
- organization: 45 flags
- historical: 111 flags

#### `entity_type` (string, required)
More specific classification of what the flag represents.

**Allowed values:**
- `country` - Sovereign nations
- `state` - US states and similar subdivisions
- `province` - Canadian provinces and similar
- `territory` - Territories and autonomous regions
- `city` - Cities and municipalities
- `organization` - International organizations
- `historical` - Historical entities

**Distribution in current dataset:**
- country: 237 flags
- state: 1,841 flags
- province: 43 flags
- territory: 6 flags
- city: 470 flags
- organization: 45 flags
- historical: 111 flags

#### `country` (string, optional)
Parent country for subdivisions and cities. Null for national flags and organizations.

**Example values:**
- `"United States"` - For US state flags
- `"Canada"` - For Canadian province flags
- `"Chile"` - For "Santiago, Chile"
- `null` - For national flags

**Coverage:** 229/2,753 flags (8.3%) have country information

#### `adoption_year` (integer, optional)
Year the flag was adopted, when available.

**Example values:**
- `1776` - US flag
- `1960` - Various African nations
- `null` - When year is unknown

**Coverage:** 72/2,753 flags (2.6%) have adoption year information

#### `tags` (array of strings, required)
Searchable keywords for enhanced discoverability.

**Tag generation logic:**
- Category name (e.g., "national", "city")
- Entity type (if different from category)
- Country name (if applicable)
- Parsed keywords from flag name
- Special aliases (e.g., "usa", "uk", "america")

**Example:**
```json
{
  "name": "Flag of California",
  "tags": ["subdivision", "state", "united states", "california", "usa", "us", "america", "american"]
}
```

## Migration Process

### Automated Migration

The migration from v2 to v3 was performed using `backend/scripts/migrate_flag_schema.py`, which:

1. Read all flags from `comprehensive_flags_2/flags.json`
2. Inferred category and entity_type based on:
   - Wikipedia page patterns
   - Flag name patterns
   - Known country/state lists
3. Extracted country information from:
   - City names with commas (e.g., "Santiago, Chile")
   - US state detection
   - Wikipedia page disambiguation patterns
4. Generated searchable tags from name, category, and country
5. Copied embeddings.npy (unchanged)
6. Wrote new schema to `all_flags/`

### Category Inference Logic

The migration script uses the following logic to categorize flags:

1. **Historical** - Contains keywords like "historical", "former", "colonial", "proposal", "naval", "governor", or year ranges
2. **Organization** - Contains keywords like "united nations", "european union", "nato", "olympics"
3. **National** - Matches known country names or has "(country)" disambiguation
4. **Subdivision** - Contains "state", "province", "territory" in Wikipedia page
5. **City** - Contains city indicators or has comma in name
6. **Default** - Classified as subdivision if no clear match

### Validation

The migrated dataset was validated using `backend/scripts/validate_dataset.py`:

- ✓ All 2,753 flags successfully migrated
- ✓ All required fields present
- ✓ Category and entity_type distributions reasonable
- ✓ Embeddings compatible (2,721/2,753 valid)
- ✓ FlagSearcher compatibility confirmed

## Updated Collectors

All data collectors have been updated to output the new schema:

- `NationalFlagCollector` - Sets category="national", entity_type="country"
- `SubdivisionFlagCollector` - Sets category="subdivision", entity_type based on subdivision type, includes country
- `CityFlagCollector` - Sets category="city", entity_type="city", extracts country from name
- `OrganizationFlagCollector` - Sets category="organization", entity_type="organization"
- `HistoricalFlagCollector` - Sets category="historical", entity_type="historical"
- `FOTWScraper` - Sets category="fotw", entity_type="historical"

## Backend Updates

### Files Modified

- `backend/common/flag_data.py` - Updated Flag model with new schema
- `backend/src/flag_searcher.py` - Updated to use `all_flags`
- `backend/scripts/validate_dataset.py` - Updated validation logic
- `backend/scripts/collect_all_flags.py` - Updated to output to `all_flags` for future collections
- `backend/scripts/download_and_process.py` - Updated paths for future collections
- All collector files updated with new schema

### Pydantic v2 Migration

As part of this refactor, the codebase was also updated for Pydantic v2:
- Replaced `@validator` with `@field_validator`
- Replaced `.dict()` with `.model_dump()`
- Updated validator syntax to use `@classmethod`

## Usage

### Accessing New Fields

```python
from backend.common.flag_data import flaglist_from_json

flags = flaglist_from_json("backend/data/all_flags/flags.json")

for flag in flags.flags:
    print(f"{flag.name}")
    print(f"  Category: {flag.category}")
    print(f"  Entity Type: {flag.entity_type}")
    print(f"  Country: {flag.country or 'N/A'}")
    print(f"  Adoption Year: {flag.adoption_year or 'Unknown'}")
    print(f"  Tags: {', '.join(flag.tags[:5])}")
```

### Filtering by Category

```python
# Get all city flags
city_flags = [f for f in flags.flags if f.category == "city"]

# Get all US state flags
us_state_flags = [f for f in flags.flags if f.country == "United States" and f.entity_type == "state"]

# Get all national flags
national_flags = [f for f in flags.flags if f.category == "national"]
```

### Searching by Tags

```python
# Find flags with specific tags
american_flags = [f for f in flags.flags if "america" in f.tags or "usa" in f.tags]
european_flags = [f for f in flags.flags if "european" in f.tags]
```

## Future Enhancements

Potential improvements for future versions:

1. **Enhanced Geographic Data**
   - Add continent information
   - Add hemisphere (Northern/Southern, Eastern/Western)
   - Add region (e.g., "Western Europe", "Southeast Asia")

2. **Richer Adoption Data**
   - Parse adoption year from Wikipedia for more flags
   - Add "last_modified" date for flags that have changed
   - Add historical context

3. **Improved Tags**
   - Add color-based tags (e.g., "tricolor", "red-white-blue")
   - Add pattern tags (e.g., "cross", "stars", "stripes")
   - Add symbolism tags (e.g., "religious", "maritime")

4. **Relationships**
   - Link historical flags to their modern equivalents
   - Link subdivision flags to their parent country flag
   - Track flag families (e.g., Nordic cross flags)

## Migration Timeline

- **2026-01-13**: Schema v3 created
- **Dataset**: all_flags (2,753 flags)
- **Previous**: comprehensive_flags_2 (2,753 flags, old schema)
- **Next**: all_flags (future collections will use new schema)

