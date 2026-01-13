# Quick Start Guide: Comprehensive Flags Dataset

This guide will help you quickly set up and use the comprehensive flags database.

## Prerequisites

Ensure you have the required dependencies installed:

```bash
# Install development dependencies (includes everything needed for data collection)
uv pip install -e ".[dev]"
```

## Three-Step Setup

### Step 1: Collect Flags (4-12 hours)

```bash
cd /home/bjafek/personal/draw_flags/backend
uv run scripts/collect_all_flags.py
```

**What this does:**
- Scrapes Wikipedia for national flags, subdivisions, organizations, historical flags, and cities
- Collects sample flags from FOTW
- Deduplicates the collected flags
- Saves results to `backend/data/comprehensive_flags/flags_deduplicated.json`

**Output files:**
- `flags_raw.json` - All collected flags before deduplication
- `flags_deduplicated.json` - Cleaned dataset ready for processing
- `collection_metadata.json` - Statistics about the collection

**Expected dataset size:** 5,000-20,000 flags

---

### Step 2: Download Images and Generate Embeddings (6-12 hours)

```bash
cd /home/bjafek/personal/draw_flags/backend
uv run scripts/download_and_process.py
```

**What this does:**
- Downloads all flag images (with rate limiting to be respectful)
- Converts SVG files to PNG
- Generates CLIP embeddings for image search
- Creates the final `flags.json` file

**Output files:**
- `images/` - Directory with all downloaded flag images
- `embeddings.npy` - CLIP embeddings (numpy array)
- `flags.json` - Final dataset with embeddings reference
- `sources.txt` - Attribution information

**Note:** This step requires significant disk space (1-5 GB) and memory (4-8 GB RAM recommended).

---

### Step 3: Validate and Test

```bash
cd /home/bjafek/personal/draw_flags/backend
uv run scripts/validate_dataset.py
```

**What this does:**
- Checks dataset structure and integrity
- Validates flags.json format
- Verifies embeddings match the flag count
- Shows statistics and sample flags

**If validation passes**, you'll see:
```
✓ Dataset validation passed!
```

---

## Using the New Dataset

Once setup is complete, update your flag searcher to use the comprehensive dataset:

**Edit:** `backend/src/flag_searcher.py`

```python
# Line 14: Change from
FLAGS_FILE = Path("backend/data/national_flags/flags.json")

# To
FLAGS_FILE = Path("backend/data/comprehensive_flags/flags.json")
```

**Restart your backend:**
```bash
cd /home/bjafek/personal/draw_flags/backend
uv run main.py
```

**Test it out:**
Visit your frontend and try searches like:
- "red dragon on white and green"
- "maple leaf flag"
- "blue with yellow stars in a circle"
- "rising sun with rays"
- "red and white stripes with a star canton"

---

## Troubleshooting

### Problem: Script stops with rate limit errors
**Solution:** The scripts are already configured with polite rate limiting. If you still get errors, you can increase the delays:

Edit the collector scripts and increase `rate_limit_seconds`:
```python
collector = SubdivisionFlagCollector(rate_limit_seconds=3.0)  # Increase from 2.0
```

### Problem: Out of memory during embedding generation
**Solution:** 
1. Close other applications to free up RAM
2. Process in smaller batches (modify `download_and_process.py`)
3. Use a machine with more RAM

### Problem: Some images fail to download
**Solution:** This is normal. Some Wikipedia pages may not have flag images, or URLs may be broken. The scripts handle this gracefully and continue with the rest of the dataset.

### Problem: SVG conversion fails
**Solution:** 
1. Install cairosvg: `uv pip install cairosvg` (or it should already be in dev dependencies)
2. Or skip SVG conversion - PNG embeddings will still work for non-SVG flags

---

## Performance Tips

### Speed up collection:
- Run overnight when you don't need your computer
- Use a fast, stable internet connection
- Consider running on a cloud server if your local connection is slow

### Reduce dataset size:
If you want a smaller, faster dataset, edit `backend/scripts/collect_all_flags.py` and comment out some collectors:

```python
# Comment out city flags for a smaller dataset
# print("\n--- City Flags ---")
# city_collector = CityFlagCollector(rate_limit_seconds=2.0)
# city_flags = city_collector.collect()
# all_flags.extend(city_flags)
```

### Speed up search:
The embeddings enable very fast searches. Once generated, searches are near-instant even with 50,000 flags.

---

## What to Expect

### Dataset Size Estimates:

| Category | Estimated Flags |
|----------|----------------|
| National | 200 |
| Subdivisions | 2,000-3,000 |
| Organizations | 200-500 |
| Historical | 500-1,000 |
| Cities | 500-1,000 |
| FOTW Sample | 100-400 |
| **Total** | **3,500-6,100** |

Note: Actual numbers depend on Wikipedia's current content and collection success rate.

### Time Estimates:

- **Collection**: 4-12 hours
- **Image Download**: 4-8 hours  
- **Embedding Generation**: 2-4 hours
- **Total**: 10-24 hours

Most of this time is automated - you can let it run overnight or in the background.

---

## Need Help?

1. Check the main [README.md](README.md) for detailed information
2. Review the validation output for specific errors
3. Check the collection logs for failed requests
4. Ensure all dependencies are installed correctly

---

## Next Steps After Setup

Once your comprehensive dataset is working:

1. **Compare search quality** - Test the same queries on both the old (200 flags) and new (5,000+ flags) datasets
2. **Collect user feedback** - See what kinds of flags users are searching for
3. **Expand further** - Use the collector framework to add more specialized flag categories
4. **Monitor performance** - Ensure the larger dataset doesn't slow down your application

Enjoy your expanded flag database! 🚩

