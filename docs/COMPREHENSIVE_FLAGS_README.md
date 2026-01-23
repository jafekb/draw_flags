# Comprehensive Flags Dataset

This directory contains a comprehensive database of flags collected from multiple sources, designed to significantly expand the flag recognition capabilities of the DrawFlags application.

## Overview

- **Target Size**: 10,000-50,000 flags
- **Categories**: National flags, subdivisions, cities, organizations, historical flags
- **Sources**: Wikipedia, Flags of the World (FOTW), and other flag databases

## Dataset Structure

```
all_flags/
├── flags.json                    # Main dataset file (FlagList format)
├── embeddings.npy                # CLIP embeddings for all flags
├── collection_metadata.json      # Statistics about data collection
├── sources.txt                   # Attribution and sources
├── images/                       # Downloaded flag images
│   ├── <flag_name>.png
│   ├── <flag_name>.jpg
│   └── ...
├── flags_raw.json               # Raw collected data (before deduplication)
├── flags_deduplicated.json      # After deduplication (before processing)
└── README.md                     # This file
```

## Data Collection Process

### Phase 1: High-Quality Structured Sources
1. **National Flags** (~200 flags)
   - Collected from Wikipedia via the national flag collector

2. **Country Subdivisions** (~2,000-3,000 flags)
   - US states and territories
   - Canadian provinces and territories
   - Australian states
   - German states
   - Russian federal subjects
   - Indian states
   - Mexican states
   - Brazilian states
   - And many more...

3. **International Organizations** (~200-500 flags)
   - United Nations and UN agencies
   - European Union institutions
   - NATO, ASEAN, African Union, Arab League
   - Sports organizations (Olympics, FIFA, etc.)
   - Major NGOs

4. **Historical Flags** (~500-1,000 flags)
   - Former countries (USSR, Yugoslavia, East Germany, etc.)
   - Colonial flags
   - Historical versions of current flags

### Phase 2: City and Municipal Flags
5. **Major City Flags** (~500-1,000 flags)
   - US state capitals and major cities
   - European capitals and major cities
   - Asian major cities
   - Other major world cities

### Phase 3: Extended Collection
6. **FOTW Collection** (sample)
   - Military flags
   - Naval ensigns
   - Political party flags
   - Sports team flags

## Usage Instructions

### Running Data Collection

**Step 1: Collect flags from all sources**

Quick test (1-2 minutes, ~200 flags):
```bash
cd backend
uv run scripts/collect_all_flags.py --test
```

Full collection (4-12 hours, 5000+ flags):
```bash
cd backend
uv run scripts/collect_all_flags.py
```

This will:
- Collect flags from Wikipedia (national, subdivisions, organizations, historical, cities)
- Collect flags from FOTW
- Deduplicate the collected flags
- Save raw and deduplicated data

**Estimated time**: 4-12 hours (depending on network speed and rate limiting)

**Step 2: Download images and generate embeddings**
```bash
cd backend
uv run scripts/download_and_process.py
```

This will:
- Download all flag images with rate limiting
- Convert SVG files to PNG (if cairosvg is available)
- Generate CLIP embeddings for all flags
- Create the final `flags.json` with embeddings reference

**Estimated time**: 6-12 hours (depending on dataset size and hardware)

**Step 3: Validate the dataset**
```bash
cd backend
uv run scripts/validate_dataset.py
```

This will:
- Check dataset structure and integrity
- Validate flags.json format
- Verify embeddings
- Test search functionality
- Display statistics and sample flags

### Using the Dataset in Your Application

Once the dataset is created and validated, update `backend/src/flag_searcher.py`:

```python
FLAGS_FILE = Path("backend/data/all_flags/flags.json")
```

Then restart your backend server:
```bash
cd backend
uv run main.py
```

## Data Quality Assurance

The collection process includes several quality assurance measures:

1. **Rate Limiting**: Respects source websites with appropriate delays (1-3 seconds)
2. **Error Handling**: Retry logic for failed requests with exponential backoff
3. **Deduplication**: Removes duplicate flags based on name and image URL similarity
4. **Validation**: Checks for required fields, valid image URLs, and proper embeddings
5. **Source Attribution**: Maintains proper attribution for all data sources

## Dependencies

The project uses `uv` for dependency management. Required packages are already specified in `pyproject.toml`.

To install development dependencies (includes all packages needed for data collection):
```bash
uv pip install -e ".[dev]"
```

This includes:
- beautifulsoup4 (HTML parsing)
- requests (HTTP requests)
- numpy (numerical operations)
- pillow (image processing)
- sentence-transformers (CLIP embeddings)
- cairosvg (SVG conversion)

## Ethical Considerations

- All scraping respects robots.txt and rate limits
- Proper User-Agent headers are used
- Source attribution is maintained in sources.txt
- Only publicly available data with appropriate licenses is used

## Data Sources

1. **Wikipedia** (https://en.wikipedia.org)
   - Licensed under CC BY-SA 3.0
   - Flag images typically in public domain or CC licenses

2. **Flags of the World (FOTW)** (https://www.crwflags.com/fotw/flags/)
   - Community-maintained vexillology resource
   - Various licenses depending on contributor

See `sources.txt` for detailed attribution.

## Troubleshooting

### Collection Issues
- **Rate limit errors**: Increase `rate_limit_seconds` in collector scripts
- **Connection timeouts**: Check network connection and retry
- **Missing images**: Some flags may not have images available

### Processing Issues
- **SVG conversion fails**: Install cairosvg or skip SVG files
- **Out of memory**: Process in batches or use a machine with more RAM
- **Slow embedding generation**: Normal for large datasets; be patient

### Usage Issues
- **Search returns no results**: Verify embeddings were generated correctly
- **Poor search quality**: May need to regenerate embeddings with better images

## Performance Considerations

- **Disk Space**: Plan for 1-5 GB depending on dataset size
- **Memory**: Embedding generation may require 4-8 GB RAM
- **Time**: Full collection and processing can take 12-24 hours

## Future Enhancements

Potential improvements to the dataset:
- Add more municipal flags from additional countries
- Include more sports team flags
- Add educational institution flags
- Expand FOTW collection (currently limited sample)
- Add regional and minority group flags
- Include more historical variations of current flags

## Support

For issues or questions:
1. Check the validation output for specific errors
2. Review log files from collection/processing scripts
3. Consult the main DrawFlags project documentation

## License

This dataset compilation is part of the DrawFlags project.
Individual flag images retain their original licenses from their respective sources.

