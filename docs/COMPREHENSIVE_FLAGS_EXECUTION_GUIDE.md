# Execution Guide: Building the Comprehensive Flags Database

## Overview

This guide provides the exact commands to build your comprehensive flags database from scratch. The entire process is automated but takes 12-24 hours to complete.

---

## Prerequisites Check

Before starting, ensure you have:

1. **Python 3.10+** (your project uses Python 3.10)
2. **uv installed** (the project uses `uv` for dependency management)
3. **Dependencies installed** - run: `uv pip install -e ".[dev]"`
4. **Stable internet connection** (for downloading thousands of images)
5. **Sufficient disk space** (5-10 GB recommended)
6. **Time** (12-24 hours total, mostly unattended)

---

## Step-by-Step Execution

### Step 0: Verify Environment

```bash
cd /home/bjafek/personal/draw_flags/backend

# Install development dependencies (includes all data collection packages)
uv pip install -e ".[dev]"

# Check if dependencies are available
uv run python -c "import requests, bs4, numpy; print('✓ Core dependencies OK')"
```

### Step 1: Collect Flags from All Sources

**Option A: Quick Test (recommended first)**
- **Time:** 1-2 minutes  
- **Flags:** ~200 (national flags)
- **Output:** `backend/data/all_flags/flags_deduplicated.json`

```bash
cd /home/bjafek/personal/draw_flags/backend

# Run in test mode
uv run scripts/collect_all_flags.py --test
```

**Option B: Full Collection**
- **Time:** 4-12 hours  
- **Flags:** 5,000+
- **Output:** `backend/data/all_flags/flags_deduplicated.json`

```bash
cd /home/bjafek/personal/draw_flags/backend

# Run the full collection script
uv run scripts/collect_all_flags.py
```

**What happens:**
- Scrapes Wikipedia for national flags, subdivisions, organizations, historical flags, and cities
- Collects sample flags from FOTW
- Deduplicates the collected flags
- Saves progress to multiple files

**Expected output:**
```
Starting comprehensive flag data collection...

================================================================================
PHASE 1: Collecting from high-quality structured sources
================================================================================

--- National Flags ---
Collecting national flags from Wikipedia...
  Collected ~200 national flags

--- Subdivision Flags ---
Starting subdivision flag collection...

Collecting flags for United States subdivisions...
  Collected 50 flags from Flags_of_the_U.S._states_and_territories

[... continues for all sources ...]

================================================================================
COLLECTION COMPLETE
================================================================================
Total flags collected (before deduplication): 5234

================================================================================
DEDUPLICATION
================================================================================
Starting deduplication of 5234 flags...
Deduplication complete:
  Original count: 5234
  Duplicates found: 312
  Duplicates removed: 312
  Final count: 4922

Saved deduplicated flags to backend/data/all_flags/flags_deduplicated.json
```

**Monitoring progress:**
- The script prints progress updates as it works
- You can safely interrupt (Ctrl+C) and restart - it will skip already-collected data
- Check `backend/data/all_flags/flags_raw.json` to see raw collected data

---

### Step 2: Download Images and Generate Embeddings

**Time:** 6-12 hours  
**Output:** `backend/data/all_flags/flags.json` + `embeddings.npy`

```bash
cd /home/bjafek/personal/draw_flags/backend

# Run the download and processing script
uv run scripts/download_and_process.py
```

**Alternative (if images already exist):**

```bash
cd /home/bjafek/personal/draw_flags

# Generate embeddings from existing flags.json + images/
uv run python backend/scripts/generate_embeddings_from_images.py \
  --flags-json backend/data/all_flags/flags.json \
  --images-dir backend/data/all_flags/images \
  --output-embeddings backend/data/all_flags/embeddings.npy
```

**What happens:**
- Downloads all flag images (with 1-second rate limiting)
- Converts SVG files to PNG (if cairosvg is available)
- Generates CLIP embeddings for all flags
- Creates the final dataset

**Expected output:**
```
Loading flags from backend/data/all_flags/flags_deduplicated.json...
Loaded 4922 flags

================================================================================
STEP 1: Downloading flag images
================================================================================
Downloading 4922 flag images...
Rate limit: 1.0 seconds between requests
  Progress: 100/4922 (successful: 98, failed: 2, skipped: 0)
  Progress: 200/4922 (successful: 195, failed: 5, skipped: 0)
[... continues ...]

Download complete:
  Successful: 4850
  Failed: 72
  Skipped (already existed): 0
  Total: 4922

================================================================================
STEP 2: Converting SVG files to PNG
================================================================================
Converting 3421 SVG files to PNG...
[... continues ...]

================================================================================
STEP 3: Generating CLIP embeddings
================================================================================
Generating CLIP embeddings for 4922 flags...
Loading CLIP model...
  Progress: 100/4922 (successful: 100, failed: 0)
  Progress: 200/4922 (successful: 200, failed: 0)
[... continues ...]

Embedding generation complete:
  Successful: 4850
  Failed: 72
  Total: 4922
  Saved to: backend/data/all_flags/embeddings.npy

================================================================================
STEP 4: Creating final dataset
================================================================================
Created final dataset: backend/data/all_flags/flags.json
  Total flags: 4922
  Embeddings: backend/data/all_flags/embeddings.npy

================================================================================
PROCESSING COMPLETE
================================================================================

Final dataset location: backend/data/all_flags
To use this dataset, update backend/src/flag_searcher.py:
  FLAGS_FILE = Path('backend/data/all_flags/flags.json')
```

**Monitoring progress:**
- Progress updates every 100 flags
- You can check `backend/data/all_flags/images/` to see downloaded images
- Failed downloads are logged but don't stop the process

---

### Step 3: Validate the Dataset

**Time:** < 1 minute  
**Output:** Validation report

```bash
cd /home/bjafek/personal/draw_flags/backend

# Run the validation script
uv run scripts/validate_dataset.py
```

**Expected output:**
```
================================================================================
COMPREHENSIVE FLAGS DATASET VALIDATION
================================================================================
Dataset directory: backend/data/all_flags

================================================================================
VALIDATION: Dataset Structure
================================================================================
✓ flags.json: Found (Main flags dataset)
✓ embeddings.npy: Found (CLIP embeddings)
✓ collection_metadata.json: Found (Collection metadata)
✓ sources.txt: Found (Source attribution)

✓ All required files present

================================================================================
VALIDATION: flags.json Structure
================================================================================
✓ Successfully loaded 4922 flags
✓ All required fields present (checked first 100 flags)
✓ All image URLs have valid extensions (checked first 100 flags)

================================================================================
VALIDATION: Embeddings
================================================================================
✓ Successfully loaded embeddings
  Shape: (4922, 512)
  Expected: (4922, 512)
✓ Embedding count matches flag count
✓ Embedding dimension correct (512)
✓ No zero embeddings found

================================================================================
VALIDATION: Search Functionality
================================================================================
Initializing FlagSearcher with new dataset...
✓ Successfully initialized with 4922 flags

Testing sample queries...
  Query: 'red white and blue stripes with stars' - Data ready for search
  Query: 'maple leaf' - Data ready for search
  Query: 'rising sun' - Data ready for search
  Query: 'cross on blue background' - Data ready for search
  Query: 'green white and red vertical stripes' - Data ready for search

✓ Dataset is compatible with FlagSearcher
  To use this dataset, update backend/src/flag_searcher.py:
    FLAGS_FILE = Path('backend/data/all_flags/flags.json')

================================================================================
STATISTICS
================================================================================
Collection Statistics:
  Total collected: 5234
  After deduplication: 4922
  Duplicates removed: 312

Final Dataset Size: 4922 flags
Downloaded images: 4850

================================================================================
SAMPLE: Random 10 Flags from Dataset
================================================================================

1. California
   Wikipedia: https://en.wikipedia.org/wiki/California
   Image: https://upload.wikimedia.org/wikipedia/commons/0/01/Flag_of_California.svg

[... 9 more samples ...]

================================================================================
VALIDATION SUMMARY
================================================================================
✓ Dataset validation passed!

The comprehensive flags dataset is ready to use.

To use this dataset in your application:
1. Update backend/src/flag_searcher.py:
   FLAGS_FILE = Path('backend/data/all_flags/flags.json')
2. Restart your backend server
3. Test with various flag descriptions
```

---

### Step 4: Switch to the New Dataset

**Edit:** `backend/src/flag_searcher.py`

Update the path:
```python
FLAGS_FILE = Path("backend/data/all_flags/flags.json")
```

**Restart the backend:**
```bash
cd /home/bjafek/personal/draw_flags/backend
python main.py
```

---

## Troubleshooting

### Problem: "ModuleNotFoundError" when running scripts

**Solution:** Install missing dependencies. The project uses `uv` for dependency management:

```bash
cd /home/bjafek/personal/draw_flags/backend

# Install all development dependencies (includes everything needed)
uv pip install -e ".[dev]"

# This includes:
# - beautifulsoup4, requests, numpy, pillow
# - sentence-transformers (for embeddings)
# - cairosvg (for SVG support)
# - and more
```

### Problem: Rate limit errors or connection timeouts

**Solution:** The scripts already have conservative rate limiting. If you still get errors:
1. Check your internet connection
2. Wait a few minutes and restart the script
3. The scripts will skip already-downloaded content

### Problem: Out of memory during embedding generation

**Solution:**
1. Close other applications
2. If still failing, you may need to process in smaller batches (edit `download_and_process.py`)

### Problem: Some images fail to download

**Solution:** This is normal and expected. Some Wikipedia pages may not have images, or URLs may be broken. The scripts handle this gracefully and continue with the rest of the dataset.

---

## Performance Tips

### Run Overnight
These scripts take many hours. Start them before bed or when you won't need your computer:

```bash
# Run in background (Linux/Mac)
nohup uv run scripts/collect_all_flags.py > collection.log 2>&1 &
nohup uv run scripts/download_and_process.py > processing.log 2>&1 &

# Check progress
tail -f collection.log
tail -f processing.log
```

### Reduce Dataset Size
If you want a smaller dataset (faster to build, less storage), edit `collect_all_flags.py` and comment out some collectors:

```python
# Comment out city flags for a smaller dataset
# city_collector = CityFlagCollector(rate_limit_seconds=2.0)
# city_flags = city_collector.collect()
# all_flags.extend(city_flags)
```

### Resume After Interruption
All scripts handle interruption gracefully:
- **Collection:** Will skip already-collected sources
- **Download:** Will skip already-downloaded images
- **Embeddings:** Will regenerate (but images are cached)

Just re-run the same command to continue where you left off.

---

## Expected Results

After completing all steps, you should have:

```
backend/data/all_flags/
├── flags.json                    # 4,000-6,000 flags
├── embeddings.npy                # ~20-30 MB
├── collection_metadata.json      # Statistics
├── sources.txt                   # Attribution
├── images/                       # 2-5 GB of images
│   └── ... (thousands of files)
└── documentation files
```

**Database expansion:**
- **Before:** ~200 national flags
- **After:** ~4,000-6,000 flags (20-30x increase)

**Categories:**
- National flags: 200
- Subdivisions: 2,000-3,000
- Organizations: 200-500
- Historical: 500-1,000
- Cities: 500-1,000
- FOTW: 100-400

---

## Next Steps

Once your comprehensive dataset is working:

1. **Test search quality** - Try various queries and compare results
2. **Monitor performance** - Ensure the larger dataset doesn't slow down your app
3. **Collect feedback** - See what kinds of flags users are searching for
4. **Expand further** - Add more specialized categories using the collector framework

---

## Support

If you encounter issues:

1. Check the validation output for specific errors
2. Review the log files (`collection.log`, `processing.log`)
3. Consult the troubleshooting sections in README.md and QUICKSTART.md
4. Ensure all dependencies are properly installed

---

## Summary of Commands

```bash
# Complete workflow
cd /home/bjafek/personal/draw_flags/backend

# Step 0: Install dependencies (first time only)
uv pip install -e ".[dev]"

# OPTION A: Quick test run (~5 minutes total)
# Step 1: Collect test dataset (1-2 minutes, ~200 flags)
uv run scripts/collect_all_flags.py --test

# Step 2: Process test dataset (~3-5 minutes)
uv run scripts/download_and_process.py

# Step 3: Validate (< 1 minute)
uv run scripts/validate_dataset.py

# OPTION B: Full collection (12-24 hours total)
# Step 1: Collect full dataset (4-12 hours, 5000+ flags)
uv run scripts/collect_all_flags.py

# Step 2: Process full dataset (6-12 hours)
uv run scripts/download_and_process.py

# Step 3: Validate (< 1 minute)
uv run scripts/validate_dataset.py

# Step 4: Update flag_searcher.py and restart backend
uv run main.py
```

That's it! Your comprehensive flag database is ready to use. 🚩

