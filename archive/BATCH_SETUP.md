# StoryDredge Batch Processing Setup

## Changes Made for Large-Scale Processing

### 1. Consolidated Directory Structure

- Moved all scripts to `storydredge/scripts/` directory
- Removed nested `storydredge/storydredge/` directory
- Updated path references in all scripts for consistency

### 2. Updated Path References

- Updated path references in all scripts to use consistent directory structure
- Added clear constants for directories in each script (ARCHIVE_DIR, OUTPUT_DIR, etc.)
- Ensured all paths are relative to the BASE_DIR

### 3. Created Setup Script

- Added `setup.py` to validate the environment and create necessary directories
- Tests OpenAI API connection before processing
- Creates all required directories automatically
- Provides helpful summary and next steps

### 4. Added Rate Limiting

- Implemented a RateLimiter class in `classify_articles.py`
- Configurable rate limit (default: 20 requests per minute)
- Respects both per-minute limits and minimum intervals between requests
- Prevents API rate limit errors during large batch processing

### 5. Created Test Script

- Added `test_batch.py` to test the batch processing pipeline
- Creates a small test issues file if one doesn't exist
- Processes just two issues with limited articles
- Verifies results after processing

### 6. Updated Documentation

- Created detailed README for batch processing
- Added documentation for each script and its purpose
- Provided examples for different batch processing scenarios
- Added troubleshooting guidance

### 7. Improved Batch Processing

- Enhanced batch_process.py with better error handling
- Added metrics collection for processing times and article counts
- Added support for skipping existing issues
- Added support for limiting articles per issue (for testing)

## How to Use

1. Run the setup script first:
   ```
   python storydredge/scripts/setup.py
   ```

2. Test the pipeline with a small batch:
   ```
   python storydredge/scripts/test_batch.py
   ```

3. For full batch processing, create or edit your issues file:
   ```
   python storydredge/scripts/batch_process.py --issues=data/sample_issues.json
   ```

## Directory Structure

```
storydredge/
├── archive/              # Archive.org downloads
│   ├── raw/              # Raw OCR files (.txt)
│   └── processed/        # Cleaned OCR files (.txt)
├── output/
│   ├── articles/         # Initial article JSONs (from splitting)
│   ├── ads/              # Pre-filtered advertisement articles
│   ├── classified/       # Articles with OpenAI metadata
│   │   └── YYYY/MM/DD/   # Organized by date
│   ├── hsa-ready/        # Articles ready for HSA consumption
│   │   └── YYYY/MM/DD/   # Organized by date
│   └── rejected/         # Articles that failed quality filters
│       └── YYYY/MM/DD/   # Organized by date
├── data/                 # Configuration and data files
│   ├── index.json        # Tracking processed issues
│   ├── sample_issues.json # Full sample for batch processing 
│   └── test_issues.json  # Small test sample
└── scripts/              # Processing pipeline scripts
    ├── setup.py          # Environment setup and validation
    ├── fetch_issue.py    # Downloads OCR from archive.org
    ├── clean_text.py     # Normalizes OCR text
    ├── split_articles.py # Splits OCR text into articles
    ├── prefilter_ads.py  # Pre-filters obvious advertisements
    ├── classify_articles.py # Uses OpenAI for metadata
    ├── migrate_and_sanitize.py # Organizes directory structure
    ├── filter_and_finalize.py  # Final HSA preparation
    ├── batch_process.py  # Processes multiple issues
    ├── test_batch.py     # Tests batch processing
    └── analyze_batch_results.py # Generates reports
```

## Environment Configuration

Create a `.env` file in the project root with:

```
# OpenAI API settings
OPENAI_API_KEY=your_api_key_here
OPENAI_RATE_LIMIT=20  # Requests per minute

# Default publication name
DEFAULT_PUBLICATION=San Antonio Express-News
``` 